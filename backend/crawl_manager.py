from __future__ import annotations

import json
import os
import re
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from backend.models import (
    NewsItem,
    classify_doc_type,
    normalize_article,
    parse_crossref_date,
    parse_date,
    parse_iso_datetime,
    strip_html,
)
from backend.fetchers import collect_from_sources, fetch_json
from backend.translators import looks_korean, translate_to_korean_gtx, translate_topic


def _build_topic_keywords(topic: str, topic_en: str | None = None) -> list[str]:
    """주제에서 관련성 체크용 키워드 목록 생성."""
    raw = topic
    if topic_en and topic_en != topic:
        raw = f"{topic} {topic_en}"
    # 단어 분리 (2자 이상)
    keywords = [w.strip().lower() for w in re.split(r"[\s,+/]+", raw) if len(w.strip()) >= 2]
    # OR, AND 같은 검색 연산자 제거
    noise = {"or", "and", "not", "the", "for", "report", "보고서", "백서", "통계", "정책", "filetype:pdf"}
    return [kw for kw in keywords if kw not in noise]


def _topic_relevant(keywords: list[str], headline: str, summary: str) -> bool:
    """제목+요약에 주제 키워드가 하나라도 포함되어 있는지 확인."""
    if not keywords:
        return True
    text = f"{headline} {summary}".lower()
    return any(kw in text for kw in keywords)


class CrawlManager:
    def __init__(self, service: Any) -> None:
        self._svc = service
        self.crawl_job: dict[str, Any] = {
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
        self.crawl_job = {
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
        return dict(self.crawl_job)

    def clear_reports(self) -> dict[str, Any]:
        svc = self._svc
        with svc.lock:
            before = len(svc.news)
            svc.news = [item for item in svc.news if item.content_type != "report"]
            removed = before - len(svc.news)
            svc._do_persist()
            return {"removed": removed, "remaining": len(svc.news)}

    # ── Region crawl ──────────────────────────────────────────

    def start_crawl(self, regions: list[str] | None = None) -> dict[str, Any]:
        if self.crawl_job["status"] == "running":
            return {"error": "이미 크롤링이 진행 중입니다.", **self.crawl_job}

        from backend.source_crawler import REGION_SEEDS

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

        thread = threading.Thread(
            target=self._run_crawl_background,
            args=(target,),
            daemon=True,
        )
        thread.start()
        return dict(self.crawl_job)

    def _run_crawl_background(self, regions: list[str]) -> None:
        from backend.source_crawler import REGION_SEEDS, load_existing_sources, crawl_seed
        from backend.persistence import merge_discovered_sources as merge_disc

        svc = self._svc
        try:
            existing_urls = load_existing_sources()
            all_discovered: list[dict[str, Any]] = []

            discovered_path = svc.data_dir / "discovered_sources.json"
            if discovered_path.exists():
                try:
                    with discovered_path.open("r", encoding="utf-8") as f:
                        all_discovered = json.load(f)
                    existing_urls |= {
                        s.get("url") for s in all_discovered if isinstance(s, dict)
                    }
                except Exception:
                    pass

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
                                f"[{region_key}] {item.get('name', '?')} — {item.get('url', '?')}"
                            )
                    except Exception as exc:
                        self.crawl_job["log"].append(
                            f"[{region_key}] {seed['name']} — 오류: {exc}"
                        )

            svc.data_dir.mkdir(parents=True, exist_ok=True)
            with discovered_path.open("w", encoding="utf-8") as f:
                json.dump(all_discovered, f, ensure_ascii=False, indent=2)

            with svc.lock:
                before = len(svc.sources)
                merge_disc(svc.sources, svc.data_dir)
                new_sources = len(svc.sources) - before
                self.crawl_job["log"].append(
                    f"소스 {new_sources}개 등록 완료, 뉴스 수집 시작..."
                )

                fetched = collect_from_sources(svc.sources, svc.source_stats)
                from backend.analytics import merge_news
                added = merge_news(fetched, svc.news, svc.trend_history, svc.sources, svc._do_persist) if fetched else 0
                self.crawl_job["log"].append(
                    f"뉴스 수집 완료: {added}건 추가"
                )
                self.crawl_job["discovered"] += added

            self.crawl_job["status"] = "completed"
            self.crawl_job["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.crawl_job["log"].append(
                f"완료: 소스 {new_sources}개 발견, 뉴스 {added}건 수집"
            )

        except Exception as exc:
            self.crawl_job["status"] = "error"
            self.crawl_job["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.crawl_job["log"].append(f"크롤링 오류: {exc}")

    # ── Topic crawl ───────────────────────────────────────────

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

        thread = threading.Thread(
            target=self._run_topic_crawl_background,
            args=(topic,),
            daemon=True,
        )
        thread.start()
        return dict(self.crawl_job)

    def _run_topic_crawl_background(self, topic: str) -> None:
        svc = self._svc
        try:
            collected_items: list[NewsItem] = []
            known_urls: set[str] = {
                item.url for item in svc.news if item.content_type != "report"
            }

            topic_en = translate_topic(topic, "en")
            relevance_keywords = _build_topic_keywords(topic, topic_en)

            steps: list[dict[str, Any]] = []

            # Phase 1: Crossref + Europe PMC
            steps.append({"phase": "학술 검색", "label": f"Crossref — {topic_en}", "action": "crossref", "query": topic_en})
            steps.append({"phase": "학술 검색", "label": f"Europe PMC — {topic_en}", "action": "europepmc", "query": topic_en})

            # Phase 2: DuckDuckGo
            ddg_queries = [
                {"label": "영어 리포트", "query": f"{topic_en} report OR whitepaper OR regulation"},
                {"label": "영어 PDF", "query": f"{topic_en} filetype:pdf report"},
                {"label": "미국 정부", "query": f"{topic_en} FAA OR GAO OR NASA OR DARPA OR DOD OR DHS report"},
                {"label": "미국 의회", "query": f"{topic_en} CRS OR Congressional Research Service OR Senate report"},
                {"label": "캐나다", "query": f"{topic_en} Transport Canada OR DRDC Canada report"},
                {"label": "유럽 기관", "query": f"{topic_en} EASA OR EU Commission OR Eurocontrol report"},
                {"label": "영국", "query": f"{topic_en} UK CAA OR UK MOD OR DSTL report"},
                {"label": "독일·프랑스", "query": f"{topic_en} DLR OR Bundeswehr OR ONERA OR DGA report"},
                {"label": "일본 기관", "query": f"{translate_topic(topic, 'ja')} 防衛省 OR JAXA OR 国土交通省"},
                {"label": "중국 기관", "query": f"{translate_topic(topic, 'zh')} 中国民航局 OR 国防部 OR 工信部 报告"},
                {"label": "인도", "query": f"{topic_en} DGCA India OR DRDO OR ISRO report"},
                {"label": "싱가포르·ASEAN", "query": f"{topic_en} CAAS Singapore OR ASEAN report"},
                {"label": "중동", "query": f"{topic_en} UAE GCAA OR Saudi GACA OR Israel IAA report"},
                {"label": "아프리카", "query": f"{topic_en} African Union OR SACAA OR Kenya KCAA report"},
                {"label": "호주·뉴질랜드", "query": f"{topic_en} CASA Australia OR CAA New Zealand report"},
                {"label": "중남미", "query": f"{topic_en} ANAC Brazil OR DGAC Mexico report"},
                {"label": "국제기구", "query": f"{topic_en} ICAO OR OECD OR NATO OR UN OR ITU report"},
                {"label": "싱크탱크", "query": f"{topic_en} RAND OR Brookings OR Carnegie OR CSIS OR IISS analysis"},
                {"label": "한국어 리포트", "query": f"{topic} 보고서 OR 백서 OR 통계 OR 정책"},
                {"label": "한국 정부", "query": f"{topic} 국방부 OR 국토부 OR 과기부 OR 방사청 OR 산업부 보고서"},
                {"label": "한국 연구기관", "query": f"{topic} KARI OR KIST OR ADD OR 항공우주연구원 보고서"},
            ]
            for lang_code, label in [("ja","일본어"),("zh-CN","중국어"),("de","독일어"),("fr","프랑스어"),("ru","러시아어"),("ar","아랍어")]:
                translated = translate_topic(topic, lang_code.split("-")[0])
                if translated != topic:
                    ddg_queries.append({"label": f"{label} ({translated[:20]})", "query": f"{translated} report"})

            for qinfo in ddg_queries:
                steps.append({"phase": "웹 검색", "label": qinfo["label"], "action": "ddg", "query": qinfo["query"]})

            # Phase 3: Google News
            gnews_langs = [
                {"hl": "en", "gl": "US", "ceid": "US:en", "label": "영어 뉴스"},
                {"hl": "ko", "gl": "KR", "ceid": "KR:ko", "label": "한국어 뉴스"},
            ]
            for lang in gnews_langs:
                steps.append({"phase": "뉴스 보조", "label": lang["label"], "action": "gnews", "lang": lang})

            self.crawl_job["total"] = len(steps)

            for idx, step in enumerate(steps):
                self.crawl_job["progress"] = idx + 1
                self.crawl_job["current_region"] = step["phase"]
                self.crawl_job["current_seed"] = step["label"]

                try:
                    items: list[NewsItem] = []

                    if step["action"] == "crossref":
                        items = self._topic_search_crossref(step["query"], known_urls)

                    elif step["action"] == "europepmc":
                        items = self._topic_search_europepmc(step["query"], known_urls)

                    elif step["action"] == "ddg":
                        import time as _time
                        _time.sleep(0.5)
                        items = self._search_duckduckgo(step["query"], topic, known_urls)

                    elif step["action"] == "gnews":
                        lang = step["lang"]
                        lang_code = lang["hl"]
                        translated = translate_topic(topic, lang_code.split("-")[0])
                        query = quote_plus(f"{translated} report OR 보고서 OR 발표")
                        rss_url = (
                            f"https://news.google.com/rss/search?q={query}"
                            f"&hl={lang['hl']}&gl={lang['gl']}&ceid={lang['ceid']}"
                        )
                        items = self._fetch_google_rss_items(rss_url, topic, known_urls)

                    # 주제 관련성 필터
                    before = len(items)
                    items = [it for it in items if _topic_relevant(relevance_keywords, it.headline, it.summary)]
                    filtered_out = before - len(items)

                    collected_items.extend(items)
                    for it in items:
                        known_urls.add(it.url)

                    log_msg = f"[{step['phase']}] {step['label']} — {len(items)}건"
                    if filtered_out:
                        log_msg += f" (관련성 미달 {filtered_out}건 제외)"
                    self.crawl_job["log"].append(log_msg)
                except Exception as exc:
                    self.crawl_job["log"].append(
                        f"[{step['phase']}] {step['label']} — 오류: {exc}"
                    )

            # Translation
            from concurrent.futures import ThreadPoolExecutor, as_completed

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
                    return False

            translated_count = 0
            with ThreadPoolExecutor(max_workers=10) as pool:
                futures = {pool.submit(_translate_item, item): item for item in need_translate}
                for future in as_completed(futures):
                    if future.result():
                        translated_count += 1

            self.crawl_job["log"].append(f"[번역] {translated_count}/{len(need_translate)}건 한글 번역 완료")

            # Merge
            with svc.lock:
                from backend.analytics import merge_news
                added = merge_news(collected_items, svc.news, svc.trend_history, svc.sources, svc._do_persist) if collected_items else 0
                self.crawl_job["discovered"] = added

            self.crawl_job["status"] = "completed"
            self.crawl_job["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.crawl_job["log"].append(
                f"완료: \"{topic}\" — {added}건 추가 (수집 {len(collected_items)}건 중)"
            )

        except Exception as exc:
            self.crawl_job["status"] = "error"
            self.crawl_job["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.crawl_job["log"].append(f"크롤링 오류: {exc}")

    # ── Stats crawl ─────────────────────────────────────────

    def start_stats_crawl(self, topic: str) -> dict[str, Any]:
        """통계/차트/데이터 전용 크롤."""
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

        thread = threading.Thread(
            target=self._run_stats_crawl_background,
            args=(topic,),
            daemon=True,
        )
        thread.start()
        return dict(self.crawl_job)

    def _run_stats_crawl_background(self, topic: str) -> None:
        svc = self._svc
        try:
            collected_items: list[NewsItem] = []
            known_urls: set[str] = {
                item.url for item in svc.news if item.content_type != "report"
            }

            topic_en = translate_topic(topic, "en")
            relevance_keywords = _build_topic_keywords(topic, topic_en)

            steps: list[dict[str, Any]] = []

            # ── DuckDuckGo: 통계·데이터 특화 쿼리
            ddg_queries = [
                # 영어 통계/데이터
                {"label": "영어 통계", "query": f"{topic_en} statistics 2024 2025 data"},
                {"label": "시장 규모", "query": f"{topic_en} market size market share forecast"},
                {"label": "인포그래픽", "query": f"{topic_en} infographic chart data visualization"},
                {"label": "PDF 통계", "query": f"{topic_en} statistics filetype:pdf"},
                {"label": "엑셀/CSV", "query": f"{topic_en} dataset filetype:xlsx OR filetype:csv"},
                # 주요 통계 포털
                {"label": "Statista", "query": f"site:statista.com {topic_en}"},
                {"label": "OECD Data", "query": f"site:data.oecd.org {topic_en}"},
                {"label": "World Bank", "query": f"site:data.worldbank.org {topic_en}"},
                # 정부 통계
                {"label": "미국 통계", "query": f"{topic_en} FAA statistics OR BTS data OR census"},
                {"label": "유럽 통계", "query": f"{topic_en} Eurostat OR EASA statistics data"},
                {"label": "일본 통계", "query": f"{translate_topic(topic, 'ja')} 統計 データ 推移"},
                {"label": "중국 통계", "query": f"{translate_topic(topic, 'zh')} 统计 数据 市场规模"},
                # 한국 통계
                {"label": "한국 통계", "query": f"{topic} 통계 현황 추이 데이터"},
                {"label": "KOSIS", "query": f"site:kosis.kr {topic}"},
                {"label": "공공데이터", "query": f"site:data.go.kr {topic}"},
                {"label": "한국 시장", "query": f"{topic} 시장규모 성장률 전망"},
                {"label": "한국 정부 통계", "query": f"{topic} 국토부 OR 과기부 OR 산업부 통계 현황"},
                # 리서치 기관
                {"label": "리서치", "query": f"{topic_en} Grand View Research OR MarketsAndMarkets OR Frost Sullivan"},
                {"label": "컨설팅", "query": f"{topic_en} McKinsey OR Deloitte OR PwC statistics report"},
            ]

            for qinfo in ddg_queries:
                steps.append({"phase": "통계 검색", "label": qinfo["label"], "action": "ddg", "query": qinfo["query"]})

            # ── Crossref: 통계 논문
            steps.append({
                "phase": "학술 통계",
                "label": f"Crossref — {topic_en} statistics",
                "action": "crossref",
                "query": f"{topic_en} statistics data survey",
            })

            # ── Google News: 통계 관련 뉴스
            gnews_langs = [
                {"hl": "en", "gl": "US", "ceid": "US:en", "label": "영어 통계 뉴스"},
                {"hl": "ko", "gl": "KR", "ceid": "KR:ko", "label": "한국 통계 뉴스"},
            ]
            for lang in gnews_langs:
                steps.append({"phase": "통계 뉴스", "label": lang["label"], "action": "gnews", "lang": lang})

            self.crawl_job["total"] = len(steps)

            for idx, step in enumerate(steps):
                self.crawl_job["progress"] = idx + 1
                self.crawl_job["current_region"] = step["phase"]
                self.crawl_job["current_seed"] = step["label"]

                try:
                    items: list[NewsItem] = []

                    if step["action"] == "crossref":
                        items = self._topic_search_crossref(step["query"], known_urls)
                        for it in items:
                            it.doc_type = "통계"

                    elif step["action"] == "ddg":
                        import time as _time
                        _time.sleep(0.5)
                        items = self._search_duckduckgo(step["query"], topic, known_urls)
                        for it in items:
                            if it.doc_type == "뉴스":
                                it.doc_type = "통계"

                    elif step["action"] == "gnews":
                        lang = step["lang"]
                        lang_code = lang["hl"]
                        translated = translate_topic(topic, lang_code.split("-")[0])
                        query = quote_plus(f"{translated} statistics OR 통계 OR 현황 OR forecast")
                        rss_url = (
                            f"https://news.google.com/rss/search?q={query}"
                            f"&hl={lang['hl']}&gl={lang['gl']}&ceid={lang['ceid']}"
                        )
                        items = self._fetch_google_rss_items(rss_url, topic, known_urls)
                        for it in items:
                            if it.doc_type == "뉴스":
                                it.doc_type = "통계"

                    # 주제 관련성 필터
                    before = len(items)
                    items = [it for it in items if _topic_relevant(relevance_keywords, it.headline, it.summary)]
                    filtered_out = before - len(items)

                    collected_items.extend(items)
                    for it in items:
                        known_urls.add(it.url)

                    log_msg = f"[{step['phase']}] {step['label']} — {len(items)}건"
                    if filtered_out:
                        log_msg += f" (관련성 미달 {filtered_out}건 제외)"
                    self.crawl_job["log"].append(log_msg)
                except Exception as exc:
                    self.crawl_job["log"].append(
                        f"[{step['phase']}] {step['label']} — 오류: {exc}"
                    )

            # Translation
            from concurrent.futures import ThreadPoolExecutor, as_completed

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
                    return False

            translated_count = 0
            with ThreadPoolExecutor(max_workers=10) as pool:
                futures = {pool.submit(_translate_item, item): item for item in need_translate}
                for future in as_completed(futures):
                    if future.result():
                        translated_count += 1

            self.crawl_job["log"].append(f"[번역] {translated_count}/{len(need_translate)}건 한글 번역 완료")

            # Merge
            with svc.lock:
                from backend.analytics import merge_news
                added = merge_news(collected_items, svc.news, svc.trend_history, svc.sources, svc._do_persist) if collected_items else 0
                self.crawl_job["discovered"] = added

            self.crawl_job["status"] = "completed"
            self.crawl_job["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.crawl_job["log"].append(
                f"완료: \"{topic}\" 통계 — {added}건 추가 (수집 {len(collected_items)}건 중)"
            )

        except Exception as exc:
            self.crawl_job["status"] = "error"
            self.crawl_job["finished_at"] = datetime.now(timezone.utc).isoformat()
            self.crawl_job["log"].append(f"통계 수집 오류: {exc}")

    # ── Search helpers ────────────────────────────────────────

    def _topic_search_crossref(self, query: str, known_urls: set[str]) -> list[NewsItem]:
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
                sources=self._svc.sources,
                published_at=parse_crossref_date(article.get("published")),
            )
            item.content_type = "report"
            item.doc_type = "논문"
            items.append(item)
        return items

    def _topic_search_europepmc(self, query: str, known_urls: set[str]) -> list[NewsItem]:
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
                sources=self._svc.sources,
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
        """DuckDuckGo 스니펫에서 날짜 추출 시도."""
        # "Jan 15, 2025", "March 3, 2024"
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
        # "15 Jan 2025", "3 March 2024"
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
        # "2024-06-01", "2024/06/01", "2024.06.01"
        m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            except ValueError:
                pass
        # "2025년 3월 5일"
        m = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", text)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            except ValueError:
                pass
        return None

    def _search_duckduckgo(
        self, query: str, topic: str, known_urls: set[str]
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

        # 결과 블록 단위로 파싱: 링크 + 스니펫
        results = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            raw_html, re.DOTALL,
        )
        # 스니펫: <a class="result__snippet" ...>text</a>
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

            # 스니펫에서 요약 + 날짜 추출
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
                sources=self._svc.sources,
                published_at=snippet_date,
            )
            item.content_type = "report"
            item.doc_type = classify_doc_type(real_url, source_name, title)
            items.append(item)

        return items

    def _fetch_google_rss_items(
        self, rss_url: str, topic: str, known_urls: set[str]
    ) -> list[NewsItem]:
        request = Request(
            rss_url,
            headers={
                "User-Agent": "DronePulseWire/0.1 (+https://localhost)",
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
                sources=self._svc.sources,
                published_at=parse_date(node.findtext("pubDate")),
            )
            item.content_type = "report"
            item.doc_type = classify_doc_type(link, source_name, title)
            items.append(item)

        return items
