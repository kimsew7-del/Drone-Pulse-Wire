from __future__ import annotations

import json
import logging
import os
import re
import time as _time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.domain import (
    NewsItem,
    classify_doc_type,
    normalize_article,
    parse_crossref_date,
    parse_date,
    parse_iso_datetime,
    strip_html,
)
from app.services.fetchers import collect_from_sources, fetch_json
from app.services.translators import looks_korean, translate_to_korean_gtx, translate_topic
from app.services.source_crawler import REGION_SEEDS, crawl_seed
from app.services.analytics import merge_news

logger = logging.getLogger(__name__)


def _build_topic_keywords(topic: str, topic_en: str | None = None) -> list[str]:
    raw = topic
    if topic_en and topic_en != topic:
        raw = f"{topic} {topic_en}"
    keywords = [w.strip().lower() for w in re.split(r"[\s,+/]+", raw) if len(w.strip()) >= 2]
    noise = {"or", "and", "not", "the", "for", "report", "보고서", "백서", "통계", "정책", "filetype:pdf"}
    return [kw for kw in keywords if kw not in noise]


def _topic_relevant(keywords: list[str], headline: str, summary: str) -> bool:
    if not keywords:
        return True
    text = f"{headline} {summary}".lower()
    return any(kw in text for kw in keywords)


class CrawlManager:
    """Manages background crawl jobs. Ephemeral state kept in memory.

    Instead of holding a reference to the old NewsService, it receives
    an async_sessionmaker and helper callables that know how to read/write
    the DB.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.crawl_job: dict[str, Any] = self._make_idle_job()

    @staticmethod
    def _make_idle_job() -> dict[str, Any]:
        return {
            "status": "idle",
            "regions": [],
            "progress": 0,
            "total": 0,
            "current_region": "",
            "current_seed": "",
            "discovered": 0,
            "log": [],
            "started_at": None,
            "finished_at": None,
        }

    def get_status(self) -> dict[str, Any]:
        return dict(self.crawl_job)

    def reset(self) -> dict[str, Any]:
        self.crawl_job = self._make_idle_job()
        return dict(self.crawl_job)

    async def clear_reports(self) -> dict[str, Any]:
        from app.models import NewsItem as ORMNewsItem

        async with self._session_factory() as db:
            result = await db.execute(
                select(ORMNewsItem).where(ORMNewsItem.content_type == "report")
            )
            report_rows = result.scalars().all()
            removed = len(report_rows)
            for row in report_rows:
                await db.delete(row)
            await db.commit()

            result2 = await db.execute(select(ORMNewsItem))
            remaining = len(result2.scalars().all())
            return {"removed": removed, "remaining": remaining}

    # -- Helpers to load sources/news from DB synchronously (from thread) --

    def _load_sources_sync(self) -> list[dict[str, Any]]:
        """Synchronous helper to load sources from DB (called from background thread)."""
        import asyncio
        from app.models import Source as ORMSource

        async def _load():
            async with self._session_factory() as db:
                result = await db.execute(select(ORMSource))
                rows = result.scalars().all()
                sources = []
                for r in rows:
                    sources.append({
                        "id": r.id,
                        "name": r.name,
                        "type": r.type,
                        "url": r.url,
                        "query": r.query,
                        "language": r.language,
                        "page_size": r.page_size,
                        "env_key": r.env_key,
                        "must_contain_any": r.must_contain_any_list,
                        "content_class": r.content_class,
                    })
                return sources

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_load())
        finally:
            loop.close()

    def _load_news_as_domain_items_sync(self) -> list[NewsItem]:
        """Load all news items from DB as domain NewsItem dataclasses (sync)."""
        import asyncio
        from app.models import NewsItem as ORMNewsItem

        async def _load():
            async with self._session_factory() as db:
                result = await db.execute(select(ORMNewsItem))
                rows = result.scalars().all()
                return [_orm_to_domain(r) for r in rows]

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_load())
        finally:
            loop.close()

    def _persist_news_sync(self, news: list[NewsItem], source_stats: dict[str, dict[str, Any]]) -> None:
        """Persist domain NewsItem list and source stats to DB (sync wrapper)."""
        import asyncio

        async def _persist():
            from app.services.news_service import persist_domain_items_to_db, persist_source_stats_to_db
            async with self._session_factory() as db:
                await persist_domain_items_to_db(db, news)
                await persist_source_stats_to_db(db, source_stats)
                await db.commit()

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_persist())
        finally:
            loop.close()

    # -- Region crawl ------------------------------------------------------

    def start_crawl(self, regions: list[str] | None = None) -> dict[str, Any]:
        if self.crawl_job["status"] == "running":
            return {"error": "이미 크롤링이 진행 중입니다.", **self.crawl_job}

        target = regions or list(REGION_SEEDS.keys())
        total_seeds = sum(len(REGION_SEEDS.get(r, [])) for r in target)

        self.crawl_job = {
            "status": "running",
            "regions": target,
            "progress": 0,
            "total": total_seeds,
            "current_region": "",
            "current_seed": "",
            "discovered": 0,
            "log": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
        }

        import threading
        thread = threading.Thread(
            target=self._run_crawl_background,
            args=(target,),
            daemon=True,
        )
        thread.start()
        return dict(self.crawl_job)

    def _run_crawl_background(self, regions: list[str]) -> None:
        try:
            sources = self._load_sources_sync()
            existing_urls = {s["url"] for s in sources}

            all_discovered: list[dict[str, Any]] = []
            progress = 0

            for region_key in regions:
                seeds = REGION_SEEDS.get(region_key, [])
                self.crawl_job["current_region"] = region_key

                for seed in seeds:
                    self.crawl_job["current_seed"] = seed["name"]
                    progress += 1
                    self.crawl_job["progress"] = progress

                    try:
                        found = crawl_seed(seed, existing_urls)
                        all_discovered.extend(found)
                        self.crawl_job["discovered"] += len(found)
                        for item in found:
                            self.crawl_job["log"].append(
                                f"[{region_key}] {item.get('name', '?')} -- {item.get('url', '?')}"
                            )
                    except Exception as exc:
                        logger.warning("[%s] %s 크롤 실패: %s", region_key, seed["name"], exc, exc_info=True)
                        self.crawl_job["log"].append(
                            f"[{region_key}] {seed['name']} -- 오류: {exc}"
                        )

            # Register discovered sources in DB
            new_sources = self._register_discovered_sources_sync(all_discovered)
            self.crawl_job["log"].append(
                f"소스 {new_sources}개 등록 완료, 뉴스 수집 시작..."
            )

            # Now collect news from all sources
            sources = self._load_sources_sync()
            source_stats: dict[str, dict[str, Any]] = {}
            fetched = collect_from_sources(sources, source_stats)
            news = self._load_news_as_domain_items_sync()
            trend_history: list[dict[str, Any]] = []

            added = merge_news(fetched, news, trend_history, sources, lambda: None) if fetched else 0
            self._persist_news_sync(news, source_stats)

            self.crawl_job["log"].append(f"뉴스 수집 완료: {added}건 추가")
            self.crawl_job["discovered"] += added
            self.crawl_job["status"] = "completed"
            self.crawl_job["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.crawl_job["log"].append(
                f"완료: 소스 {new_sources}개 발견, 뉴스 {added}건 수집"
            )

        except Exception as exc:
            logger.error("지역 크롤링 오류: %s", exc, exc_info=True)
            self.crawl_job["status"] = "error"
            self.crawl_job["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.crawl_job["log"].append(f"크롤링 오류: {exc}")

    def _register_discovered_sources_sync(self, discovered: list[dict[str, Any]]) -> int:
        """Register discovered sources into the DB. Returns count of newly added."""
        import asyncio
        from app.models import Source as ORMSource

        async def _register():
            async with self._session_factory() as db:
                result = await db.execute(select(ORMSource))
                existing = result.scalars().all()
                known_ids = {s.id for s in existing}
                known_urls = {s.url for s in existing}
                count = 0
                for item in discovered:
                    if not isinstance(item, dict):
                        continue
                    if item.get("id") in known_ids or item.get("url") in known_urls:
                        continue
                    must_contain = item.get("must_contain_any", [])
                    orm_source = ORMSource(
                        id=item.get("id", f"src-discovered-{__import__('uuid').uuid4().hex[:8]}"),
                        name=item.get("name", "Discovered Source"),
                        type=item.get("type", "rss"),
                        url=item.get("url", ""),
                        query=item.get("query"),
                        language=item.get("language"),
                        page_size=item.get("page_size"),
                        env_key=item.get("env_key"),
                        content_class=item.get("content_class"),
                    )
                    orm_source.must_contain_any_list = must_contain if isinstance(must_contain, list) else []
                    db.add(orm_source)
                    known_ids.add(orm_source.id)
                    known_urls.add(orm_source.url)
                    count += 1
                await db.commit()
                return count

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_register())
        finally:
            loop.close()

    # -- Topic crawl -------------------------------------------------------

    def start_topic_crawl(self, topic: str) -> dict[str, Any]:
        if self.crawl_job["status"] == "running":
            return {"error": "이미 크롤링이 진행 중입니다.", **self.crawl_job}

        self.crawl_job = {
            "status": "running",
            "regions": ["topic"],
            "progress": 0,
            "total": 1,
            "current_region": "topic",
            "current_seed": topic,
            "discovered": 0,
            "log": [f"주제 크롤링 시작: \"{topic}\""],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
        }

        import threading
        thread = threading.Thread(
            target=self._run_topic_crawl_background,
            args=(topic,),
            daemon=True,
        )
        thread.start()
        return dict(self.crawl_job)

    def _run_topic_crawl_background(self, topic: str) -> None:
        topic_en = translate_topic(topic, "en")
        steps = self._build_topic_steps(topic, topic_en)
        self._run_step_crawl_pipeline(topic, topic_en, steps, crawl_label="주제")

    @staticmethod
    def _build_topic_steps(topic: str, topic_en: str) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []

        steps.append({"phase": "학술 검색", "label": f"Crossref -- {topic_en}", "action": "crossref", "query": topic_en})
        steps.append({"phase": "학술 검색", "label": f"Europe PMC -- {topic_en}", "action": "europepmc", "query": topic_en})

        ddg_queries = [
            {"label": "영어 리포트", "query": f"{topic_en} report OR whitepaper OR regulation"},
            {"label": "영어 PDF", "query": f"{topic_en} filetype:pdf report"},
            {"label": "미국 정부", "query": f"{topic_en} FAA OR GAO OR NASA OR DARPA OR DOD OR DHS report"},
            {"label": "미국 의회", "query": f"{topic_en} CRS OR Congressional Research Service OR Senate report"},
            {"label": "캐나다", "query": f"{topic_en} Transport Canada OR DRDC Canada report"},
            {"label": "유럽 기관", "query": f"{topic_en} EASA OR EU Commission OR Eurocontrol report"},
            {"label": "영국", "query": f"{topic_en} UK CAA OR UK MOD OR DSTL report"},
            {"label": "독일/프랑스", "query": f"{topic_en} DLR OR Bundeswehr OR ONERA OR DGA report"},
            {"label": "일본 기관", "query": f"{translate_topic(topic, 'ja')} 防衛省 OR JAXA OR 国土交通省"},
            {"label": "중국 기관", "query": f"{translate_topic(topic, 'zh')} 中国民航局 OR 国防部 OR 工信部 报告"},
            {"label": "인도", "query": f"{topic_en} DGCA India OR DRDO OR ISRO report"},
            {"label": "싱가포르/ASEAN", "query": f"{topic_en} CAAS Singapore OR ASEAN report"},
            {"label": "중동", "query": f"{topic_en} UAE GCAA OR Saudi GACA OR Israel IAA report"},
            {"label": "아프리카", "query": f"{topic_en} African Union OR SACAA OR Kenya KCAA report"},
            {"label": "호주/뉴질랜드", "query": f"{topic_en} CASA Australia OR CAA New Zealand report"},
            {"label": "중남미", "query": f"{topic_en} ANAC Brazil OR DGAC Mexico report"},
            {"label": "국제기구", "query": f"{topic_en} ICAO OR OECD OR NATO OR UN OR ITU report"},
            {"label": "싱크탱크", "query": f"{topic_en} RAND OR Brookings OR Carnegie OR CSIS OR IISS analysis"},
            {"label": "한국어 리포트", "query": f"{topic} 보고서 OR 백서 OR 통계 OR 정책"},
            {"label": "한국 정부", "query": f"{topic} 국방부 OR 국토부 OR 과기부 OR 방사청 OR 산업부 보고서"},
            {"label": "한국 연구기관", "query": f"{topic} KARI OR KIST OR ADD OR 항공우주연구원 보고서"},
        ]
        for lang_code, label in [("ja", "일본어"), ("zh-CN", "중국어"), ("de", "독일어"), ("fr", "프랑스어"), ("ru", "러시아어"), ("ar", "아랍어")]:
            translated = translate_topic(topic, lang_code.split("-")[0])
            if translated != topic:
                ddg_queries.append({"label": f"{label} ({translated[:20]})", "query": f"{translated} report"})

        for qinfo in ddg_queries:
            steps.append({"phase": "웹 검색", "label": qinfo["label"], "action": "ddg", "query": qinfo["query"]})

        gnews_langs = [
            {"hl": "en", "gl": "US", "ceid": "US:en", "label": "영어 뉴스"},
            {"hl": "ko", "gl": "KR", "ceid": "KR:ko", "label": "한국어 뉴스"},
        ]
        for lang in gnews_langs:
            steps.append({
                "phase": "뉴스 보조", "label": lang["label"], "action": "gnews", "lang": lang,
                "gnews_suffix": "report OR 보고서 OR 발표",
            })

        return steps

    # -- Stats crawl -------------------------------------------------------

    def start_stats_crawl(self, topic: str) -> dict[str, Any]:
        if self.crawl_job["status"] == "running":
            return {"error": "이미 크롤링이 진행 중입니다.", **self.crawl_job}

        self.crawl_job = {
            "status": "running",
            "regions": ["stats"],
            "progress": 0,
            "total": 1,
            "current_region": "통계 수집",
            "current_seed": topic,
            "discovered": 0,
            "log": [f"통계 수집 시작: \"{topic}\""],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
        }

        import threading
        thread = threading.Thread(
            target=self._run_stats_crawl_background,
            args=(topic,),
            daemon=True,
        )
        thread.start()
        return dict(self.crawl_job)

    def _run_stats_crawl_background(self, topic: str) -> None:
        topic_en = translate_topic(topic, "en")
        steps = self._build_stats_steps(topic, topic_en)
        self._run_step_crawl_pipeline(
            topic, topic_en, steps,
            doc_type_override="통계",
            crawl_label="통계",
        )

    @staticmethod
    def _build_stats_steps(topic: str, topic_en: str) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []

        ddg_queries = [
            {"label": "영어 통계", "query": f"{topic_en} statistics 2024 2025 data"},
            {"label": "시장 규모", "query": f"{topic_en} market size market share forecast"},
            {"label": "인포그래픽", "query": f"{topic_en} infographic chart data visualization"},
            {"label": "PDF 통계", "query": f"{topic_en} statistics filetype:pdf"},
            {"label": "엑셀/CSV", "query": f"{topic_en} dataset filetype:xlsx OR filetype:csv"},
            {"label": "Statista", "query": f"site:statista.com {topic_en}"},
            {"label": "OECD Data", "query": f"site:data.oecd.org {topic_en}"},
            {"label": "World Bank", "query": f"site:data.worldbank.org {topic_en}"},
            {"label": "미국 통계", "query": f"{topic_en} FAA statistics OR BTS data OR census"},
            {"label": "유럽 통계", "query": f"{topic_en} Eurostat OR EASA statistics data"},
            {"label": "일본 통계", "query": f"{translate_topic(topic, 'ja')} 統計 データ 推移"},
            {"label": "중국 통계", "query": f"{translate_topic(topic, 'zh')} 统计 数据 市场规模"},
            {"label": "한국 통계", "query": f"{topic} 통계 현황 추이 데이터"},
            {"label": "KOSIS", "query": f"site:kosis.kr {topic}"},
            {"label": "공공데이터", "query": f"site:data.go.kr {topic}"},
            {"label": "한국 시장", "query": f"{topic} 시장규모 성장률 전망"},
            {"label": "한국 정부 통계", "query": f"{topic} 국토부 OR 과기부 OR 산업부 통계 현황"},
            {"label": "리서치", "query": f"{topic_en} Grand View Research OR MarketsAndMarkets OR Frost Sullivan"},
            {"label": "컨설팅", "query": f"{topic_en} McKinsey OR Deloitte OR PwC statistics report"},
        ]

        for qinfo in ddg_queries:
            steps.append({"phase": "통계 검색", "label": qinfo["label"], "action": "ddg", "query": qinfo["query"]})

        steps.append({
            "phase": "학술 통계",
            "label": f"Crossref -- {topic_en} statistics",
            "action": "crossref",
            "query": f"{topic_en} statistics data survey",
        })

        gnews_langs = [
            {"hl": "en", "gl": "US", "ceid": "US:en", "label": "영어 통계 뉴스"},
            {"hl": "ko", "gl": "KR", "ceid": "KR:ko", "label": "한국 통계 뉴스"},
        ]
        for lang in gnews_langs:
            steps.append({
                "phase": "통계 뉴스", "label": lang["label"], "action": "gnews", "lang": lang,
                "gnews_suffix": "statistics OR 통계 OR 현황 OR forecast",
            })

        return steps

    # -- Shared step-based crawl pipeline ----------------------------------

    def _run_step_crawl_pipeline(
        self,
        topic: str,
        topic_en: str,
        steps: list[dict[str, Any]],
        *,
        doc_type_override: str | None = None,
        crawl_label: str = "주제",
    ) -> None:
        try:
            sources = self._load_sources_sync()
            news = self._load_news_as_domain_items_sync()

            collected_items: list[NewsItem] = []
            known_urls: set[str] = {
                item.url for item in news if item.content_type != "report"
            }

            relevance_keywords = _build_topic_keywords(topic, topic_en)

            self.crawl_job["total"] = len(steps)

            for idx, step in enumerate(steps):
                self.crawl_job["progress"] = idx + 1
                self.crawl_job["current_region"] = step["phase"]
                self.crawl_job["current_seed"] = step["label"]

                try:
                    items = self._execute_step(step, topic, known_urls, doc_type_override, sources)

                    before = len(items)
                    items = [it for it in items if _topic_relevant(relevance_keywords, it.headline, it.summary)]
                    filtered_out = before - len(items)

                    collected_items.extend(items)
                    for it in items:
                        known_urls.add(it.url)

                    log_msg = f"[{step['phase']}] {step['label']} -- {len(items)}건"
                    if filtered_out:
                        log_msg += f" (관련성 미달 {filtered_out}건 제외)"
                    self.crawl_job["log"].append(log_msg)
                except Exception as exc:
                    logger.warning("[%s] %s 실패: %s", step["phase"], step["label"], exc, exc_info=True)
                    self.crawl_job["log"].append(
                        f"[{step['phase']}] {step['label']} -- 오류: {exc}"
                    )

            # Translation
            self._translate_collected_items(collected_items)

            # Merge
            trend_history: list[dict[str, Any]] = []
            added = merge_news(collected_items, news, trend_history, sources, lambda: None) if collected_items else 0

            source_stats: dict[str, dict[str, Any]] = {}
            self._persist_news_sync(news, source_stats)

            self.crawl_job["discovered"] = added
            self.crawl_job["status"] = "completed"
            self.crawl_job["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.crawl_job["log"].append(
                f"완료: \"{topic}\" {crawl_label} -- {added}건 추가 (수집 {len(collected_items)}건 중)"
            )

        except Exception as exc:
            logger.error("%s 크롤 오류: %s", crawl_label, exc, exc_info=True)
            self.crawl_job["status"] = "error"
            self.crawl_job["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.crawl_job["log"].append(f"{crawl_label} 수집 오류: {exc}")

    def _execute_step(
        self,
        step: dict[str, Any],
        topic: str,
        known_urls: set[str],
        doc_type_override: str | None,
        sources: list[dict[str, Any]],
    ) -> list[NewsItem]:
        items: list[NewsItem] = []

        if step["action"] == "crossref":
            items = self._topic_search_crossref(step["query"], known_urls, sources)
            if doc_type_override:
                for it in items:
                    it.doc_type = doc_type_override

        elif step["action"] == "europepmc":
            items = self._topic_search_europepmc(step["query"], known_urls, sources)

        elif step["action"] == "ddg":
            _time.sleep(0.5)
            items = self._search_duckduckgo(step["query"], topic, known_urls, sources)
            if doc_type_override:
                for it in items:
                    if it.doc_type == "뉴스":
                        it.doc_type = doc_type_override

        elif step["action"] == "gnews":
            lang = step["lang"]
            lang_code = lang["hl"]
            translated = translate_topic(topic, lang_code.split("-")[0])
            suffix = step.get("gnews_suffix", "report OR 보고서 OR 발표")
            query = quote_plus(f"{translated} {suffix}")
            rss_url = (
                f"https://news.google.com/rss/search?q={query}"
                f"&hl={lang['hl']}&gl={lang['gl']}&ceid={lang['ceid']}"
            )
            items = self._fetch_google_rss_items(rss_url, topic, known_urls, sources)
            if doc_type_override:
                for it in items:
                    if it.doc_type == "뉴스":
                        it.doc_type = doc_type_override

        return items

    def _translate_collected_items(self, collected_items: list[NewsItem]) -> None:
        need_translate = [
            item for item in collected_items
            if not looks_korean(item.headline)
        ]
        self.crawl_job["current_region"] = "번역"
        self.crawl_job["current_seed"] = f"제목 {len(need_translate)}건 병렬 번역 중..."

        def _translate_item(item: NewsItem) -> bool:
            try:
                ko = translate_to_korean_gtx(item.headline)
                if ko and ko != item.headline:
                    item.translated_headline = ko
                    item.translated_to_ko = True
                if item.summary and not looks_korean(item.summary):
                    ko_s = translate_to_korean_gtx(item.summary)
                    if ko_s and ko_s != item.summary:
                        item.translated_summary = ko_s
                return bool(item.translated_headline)
            except Exception:
                logger.debug("번역 실패: %s", item.headline[:50], exc_info=True)
                return False

        translated_count = 0
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_translate_item, item): item for item in need_translate}
            for future in as_completed(futures):
                if future.result():
                    translated_count += 1

        self.crawl_job["log"].append(f"[번역] {translated_count}/{len(need_translate)}건 한글 번역 완료")

    # -- Search helpers ----------------------------------------------------

    def _topic_search_crossref(self, query: str, known_urls: set[str], sources: list[dict[str, Any]]) -> list[NewsItem]:
        params = {
            "rows": "15",
            "query.title": query,
            "select": "DOI,title,published,container-title,URL,abstract",
        }
        mailto = os.environ.get("CROSSREF_MAILTO", "")
        if mailto:
            params["mailto"] = mailto

        payload = fetch_json("https://api.crossref.org/works", params)
        items: list[NewsItem] = []
        for article in payload.get("message", {}).get("items", []):
            title = " ".join(article.get("title", [])[:1])
            if not title:
                continue
            url = article.get("URL", "")
            if not url or url in known_urls:
                continue
            summary = strip_html(article.get("abstract", "") or "")
            journal = " / ".join(article.get("container-title", [])[:1]) or "Crossref"
            item = normalize_article(
                headline=title,
                summary=summary,
                source_name=journal,
                source_id="topic-crossref",
                url=url,
                sources=sources,
                published_at=parse_crossref_date(article.get("published")),
            )
            item.content_type = "report"
            item.doc_type = "논문"
            items.append(item)
        return items

    def _topic_search_europepmc(self, query: str, known_urls: set[str], sources: list[dict[str, Any]]) -> list[NewsItem]:
        params = {
            "query": f"{query} sort_date:y",
            "pageSize": "15",
            "format": "json",
            "resultType": "core",
        }
        payload = fetch_json("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params)
        items: list[NewsItem] = []
        for article in payload.get("resultList", {}).get("result", []):
            title = article.get("title", "")
            if not title:
                continue
            doi = article.get("doi", "")
            url = f"https://doi.org/{doi}" if doi else ""
            if not url or url in known_urls:
                continue
            summary = article.get("abstractText", "")
            journal = article.get("journalTitle", "") or "Europe PMC"
            item = normalize_article(
                headline=title,
                summary=summary,
                source_name=journal,
                source_id="topic-europepmc",
                url=url,
                sources=sources,
                published_at=parse_iso_datetime(article.get("firstPublicationDate")),
            )
            item.content_type = "report"
            item.doc_type = "논문"
            items.append(item)
        return items

    _MONTH_MAP = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    @classmethod
    def _parse_snippet_date(cls, text: str) -> datetime | None:
        m = re.search(
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})",
            text, re.IGNORECASE,
        )
        if m:
            month = cls._MONTH_MAP.get(m.group(1)[:3].lower())
            if month:
                try:
                    return datetime(int(m.group(3)), month, int(m.group(2)), tzinfo=timezone.utc)
                except ValueError:
                    pass
        m = re.search(
            r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})",
            text, re.IGNORECASE,
        )
        if m:
            month = cls._MONTH_MAP.get(m.group(2)[:3].lower())
            if month:
                try:
                    return datetime(int(m.group(3)), month, int(m.group(1)), tzinfo=timezone.utc)
                except ValueError:
                    pass
        m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            except ValueError:
                pass
        m = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", text)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            except ValueError:
                pass
        return None

    def _search_duckduckgo(
        self, query: str, topic: str, known_urls: set[str], sources: list[dict[str, Any]]
    ) -> list[NewsItem]:
        encoded_q = quote_plus(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_q}"
        request = Request(
            search_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html",
            },
        )
        with urlopen(request, timeout=15) as resp:
            raw_html = resp.read().decode("utf-8", errors="replace")

        results = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            raw_html, re.DOTALL,
        )
        snippets = re.findall(
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            raw_html, re.DOTALL,
        )

        items: list[NewsItem] = []
        for idx, (href, raw_title) in enumerate(results[:15]):
            uddg = re.search(r'uddg=([^&]+)', href)
            real_url = unquote(uddg.group(1)) if uddg else href
            if not real_url.startswith("http") or real_url in known_urls:
                continue

            title = strip_html(raw_title).strip()
            if not title or len(title) < 5:
                continue

            snippet_text = strip_html(snippets[idx]) if idx < len(snippets) else ""
            snippet_date = self._parse_snippet_date(f"{title} {snippet_text}")

            domain = urlparse(real_url).netloc.replace("www.", "")
            source_name = domain

            item = normalize_article(
                headline=title,
                summary=snippet_text,
                source_name=source_name,
                source_id=f"topic-{topic[:20]}",
                url=real_url,
                sources=sources,
                published_at=snippet_date,
            )
            item.content_type = "report"
            item.doc_type = classify_doc_type(real_url, source_name, title)
            items.append(item)

        return items

    def _fetch_google_rss_items(
        self, rss_url: str, topic: str, known_urls: set[str], sources: list[dict[str, Any]]
    ) -> list[NewsItem]:
        request = Request(
            rss_url,
            headers={
                "User-Agent": "Briefwave/0.1 (+https://localhost)",
                "Accept": "application/rss+xml, application/xml, text/xml",
            },
        )
        with urlopen(request, timeout=15) as resp:
            data = resp.read()
        root = ET.fromstring(data)

        items: list[NewsItem] = []
        for node in root.findall(".//item")[:10]:
            raw_title = (node.findtext("title") or "").strip()
            link = (node.findtext("link") or "").strip()
            if not raw_title or not link or link in known_urls:
                continue

            source_name = f"Topic: {topic}"
            title = raw_title
            if " - " in raw_title:
                parts = raw_title.rsplit(" - ", 1)
                candidate_source = parts[1].strip()
                if len(candidate_source) <= 40 and parts[0].strip():
                    title = parts[0].strip()
                    source_name = candidate_source

            raw_desc = node.findtext("description") or ""
            summary = strip_html(raw_desc).strip()
            if summary and summary.lower().startswith(title.lower()[:30]):
                summary = ""

            item = normalize_article(
                headline=title,
                summary=summary,
                source_name=source_name,
                source_id=f"topic-{topic[:20]}",
                url=link,
                sources=sources,
                published_at=parse_date(node.findtext("pubDate")),
            )
            item.content_type = "report"
            item.doc_type = classify_doc_type(link, source_name, title)
            items.append(item)

        return items


# -- Conversion helpers ------------------------------------------------


def _orm_to_domain(row: Any) -> NewsItem:
    """Convert an ORM NewsItem row to a domain NewsItem dataclass."""
    import json as _json
    return NewsItem(
        id=row.id,
        topic=row.topic,
        region=row.region,
        headline=row.headline,
        summary=row.summary,
        highlights=_safe_json_list(row.highlights),
        source=row.source,
        impact=row.impact,
        timestamp=row.timestamp,
        url=row.url,
        status=row.status or "queued",
        duplicate_group=row.duplicate_group,
        related_sources=_safe_json_list(row.related_sources),
        duplicate_count=row.duplicate_count or 0,
        canonical_key=row.canonical_key or "",
        merged_summary=row.merged_summary,
        related_articles=_safe_json_list(row.related_articles),
        editor_note=row.editor_note or "",
        source_id=row.source_id or "",
        translated_headline=row.translated_headline or "",
        translated_summary=row.translated_summary or "",
        translated_to_ko=bool(row.translated_to_ko),
        auto_categories=_safe_json_list(row.auto_categories),
        content_type=row.content_type or "news",
        doc_type=row.doc_type or "",
    )


def _safe_json_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if not val:
        return []
    try:
        import json as _json
        parsed = _json.loads(val)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []
