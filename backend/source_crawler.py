"""
Source Discovery Crawler
========================
지역별 기관 웹사이트에서 드론/AI 관련 RSS 피드를 탐색하고
data/discovered_sources.json 에 기록합니다.

사용법:
    python3 backend/source_crawler.py              # 전체 탐색
    python3 backend/source_crawler.py --region asia # 특정 지역만
    python3 backend/source_crawler.py --dry-run     # 저장 없이 결과만 출력
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DISCOVERED_PATH = DATA_DIR / "discovered_sources.json"
SOURCES_PATH = DATA_DIR / "sources.json"

TIMEOUT = 15
USER_AGENT = "DronePulseWire-Crawler/0.1 (+https://localhost)"

DRONE_KEYWORDS = [
    "drone", "uav", "uas", "unmanned", "rpas", "bvlos", "urban air",
    "evtol", "uam", "autonomous flight",
    "드론", "무인기", "도심항공",
    "ドローン", "無人機",
    "无人机", "無人機",
    "дрон", "бпла", "беспилотник",
    "dron", "vehículo aéreo no tripulado",
]

# ---------------------------------------------------------------------------
# 지역별 탐색 시드: (기관명, 시작URL, 지역, content_class)
# 크롤러는 각 URL에서 RSS 링크를 발견하려 시도합니다.
# ---------------------------------------------------------------------------

REGION_SEEDS: dict[str, list[dict]] = {
    "north_america": [
        {"name": "FAA UAS", "url": "https://www.faa.gov/uas", "region": "North America", "content_class": "report"},
        {"name": "NASA Aeronautics", "url": "https://www.nasa.gov/aeronautics/", "region": "North America", "content_class": "report"},
        {"name": "DARPA", "url": "https://www.darpa.mil/", "region": "North America", "content_class": "report"},
        {"name": "Transport Canada Drones", "url": "https://tc.canada.ca/en/aviation/drone-safety", "region": "North America", "content_class": "report"},
        {"name": "AUVSI", "url": "https://www.auvsi.org/news", "region": "North America"},
    ],
    "europe": [
        {"name": "EASA Drones", "url": "https://www.easa.europa.eu/en/domains/civil-drones", "region": "Europe", "content_class": "report"},
        {"name": "UK CAA Drones", "url": "https://www.caa.co.uk/drones/", "region": "Europe", "content_class": "report"},
        {"name": "DLR", "url": "https://www.dlr.de/en/latest/news", "region": "Europe", "content_class": "report"},
        {"name": "SESAR JU", "url": "https://www.sesarju.eu/news", "region": "Europe", "content_class": "report"},
        {"name": "ENAC France", "url": "https://www.ecologie.gouv.fr/drones-aeronefs-sans-equipage-bord", "region": "Europe", "content_class": "report"},
        {"name": "ENAIRE Spain", "url": "https://www.enaire.es/en/news", "region": "Europe", "content_class": "report"},
    ],
    "china": [
        {"name": "CAAC China", "url": "http://www.caac.gov.cn/", "region": "China", "content_class": "report"},
        {"name": "Xinhua Tech", "url": "http://www.news.cn/tech/", "region": "China"},
        {"name": "36Kr Tech", "url": "https://36kr.com/", "region": "China"},
        {"name": "COMAC", "url": "http://english.comac.cc/news/", "region": "China", "content_class": "report"},
    ],
    "japan": [
        {"name": "MLIT Japan", "url": "https://www.mlit.go.jp/", "region": "Japan", "content_class": "report"},
        {"name": "JAXA", "url": "https://www.jaxa.jp/", "region": "Japan", "content_class": "report"},
        {"name": "NEDO", "url": "https://www.nedo.go.jp/", "region": "Japan", "content_class": "report"},
        {"name": "Japan Drone Association", "url": "https://www.juida.org/", "region": "Japan", "content_class": "report"},
    ],
    "southeast_asia": [
        {"name": "CAAS Singapore", "url": "https://www.caas.gov.sg/", "region": "Southeast Asia", "content_class": "report"},
        {"name": "CAAT Thailand", "url": "https://www.caat.or.th/en/", "region": "Southeast Asia", "content_class": "report"},
        {"name": "DGCA Indonesia", "url": "https://hubud.dephub.go.id/", "region": "Southeast Asia", "content_class": "report"},
        {"name": "CAAV Vietnam", "url": "https://caa.gov.vn/en/", "region": "Southeast Asia", "content_class": "report"},
        {"name": "CAAP Philippines", "url": "https://caap.gov.ph/", "region": "Southeast Asia", "content_class": "report"},
        {"name": "CAAM Malaysia", "url": "https://www.caam.gov.my/", "region": "Southeast Asia", "content_class": "report"},
    ],
    "middle_east": [
        {"name": "UAE GCAA", "url": "https://www.gcaa.gov.ae/en/", "region": "Middle East", "content_class": "report"},
        {"name": "Saudi GACA", "url": "https://gaca.gov.sa/web/en-gb/page/home", "region": "Middle East", "content_class": "report"},
        {"name": "Israel IAA", "url": "https://www.gov.il/en/departments/iaa/", "region": "Middle East", "content_class": "report"},
        {"name": "Gulf News Tech", "url": "https://gulfnews.com/technology", "region": "Middle East"},
        {"name": "Khaleej Times Tech", "url": "https://www.khaleejtimes.com/technology", "region": "Middle East"},
    ],
    "russia": [
        {"name": "TASS Tech", "url": "https://tass.com/science", "region": "Russia / CIS"},
        {"name": "Rosaviatsia", "url": "https://favt.gov.ru/", "region": "Russia / CIS", "content_class": "report"},
        {"name": "RIA Novosti Tech", "url": "https://ria.ru/technology/", "region": "Russia / CIS"},
    ],
    "africa": [
        {"name": "SACAA South Africa", "url": "https://www.caa.co.za/", "region": "Africa", "content_class": "report"},
        {"name": "KCAA Kenya", "url": "https://www.kcaa.or.ke/", "region": "Africa", "content_class": "report"},
        {"name": "RCAA Rwanda", "url": "https://www.rcaa.gov.rw/", "region": "Africa", "content_class": "report"},
        {"name": "NCAA Nigeria", "url": "https://ncaa.gov.ng/", "region": "Africa", "content_class": "report"},
        {"name": "TechCabal", "url": "https://techcabal.com/", "region": "Africa"},
        {"name": "Disrupt Africa", "url": "https://disrupt-africa.com/", "region": "Africa"},
    ],
    "india": [
        {"name": "DGCA India", "url": "https://www.dgca.gov.in/", "region": "India", "content_class": "report"},
        {"name": "DRDO India", "url": "https://www.drdo.gov.in/", "region": "India", "content_class": "report"},
        {"name": "ISRO", "url": "https://www.isro.gov.in/", "region": "India", "content_class": "report"},
        {"name": "Economic Times Tech", "url": "https://economictimes.indiatimes.com/tech", "region": "India"},
    ],
    "oceania": [
        {"name": "CASA Australia", "url": "https://www.casa.gov.au/", "region": "Oceania", "content_class": "report"},
        {"name": "CAA New Zealand", "url": "https://www.aviation.govt.nz/", "region": "Oceania", "content_class": "report"},
    ],
    "latin_america": [
        {"name": "ANAC Brazil", "url": "https://www.gov.br/anac/en", "region": "Latin America", "content_class": "report"},
        {"name": "DGAC Mexico", "url": "https://www.gob.mx/sct", "region": "Latin America", "content_class": "report"},
        {"name": "DGAC Chile", "url": "https://www.dgac.gob.cl/", "region": "Latin America", "content_class": "report"},
    ],
    "korea": [
        {"name": "국토교통부 드론", "url": "https://www.molit.go.kr/", "region": "Korea", "content_class": "report"},
        {"name": "산업통상자원부", "url": "https://www.motie.go.kr/", "region": "Korea", "content_class": "report"},
        {"name": "국방과학연구소 ADD", "url": "https://www.add.re.kr/", "region": "Korea", "content_class": "report"},
        {"name": "한국드론산업진흥협회", "url": "https://www.kodipa.or.kr/", "region": "Korea", "content_class": "report"},
    ],
}


def fetch_page(url: str) -> str | None:
    """Fetch a URL and return its content as string."""
    try:
        req = Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html, application/xhtml+xml, application/xml;q=0.9, */*;q=0.8",
        })
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
            # try utf-8 first, fallback to latin-1
            for enc in ("utf-8", "euc-kr", "latin-1"):
                try:
                    return data.decode(enc)
                except UnicodeDecodeError:
                    continue
            return data.decode("utf-8", errors="replace")
    except Exception:
        return None


def discover_rss_links(html: str, base_url: str) -> list[str]:
    """Extract RSS/Atom feed URLs from HTML page."""
    feeds: list[str] = []

    # <link rel="alternate" type="application/rss+xml" href="...">
    link_pattern = re.compile(
        r'<link[^>]+type=["\']application/(rss|atom)\+xml["\'][^>]+href=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    for match in link_pattern.finditer(html):
        feeds.append(urljoin(base_url, match.group(2)))

    # Also look for href="..." ending in /rss, /feed, .xml, .rdf
    href_pattern = re.compile(
        r'href=["\']([^"\']*(?:/rss|/feed|\.rss|\.xml|\.rdf|/atom)[^"\']*)["\']',
        re.IGNORECASE,
    )
    for match in href_pattern.finditer(html):
        href = match.group(1)
        if any(skip in href.lower() for skip in ["sitemap", "schema", "xmlrpc", ".js", ".css"]):
            continue
        feeds.append(urljoin(base_url, href))

    # Deduplicate preserving order
    seen = set()
    unique: list[str] = []
    for url in feeds:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def validate_rss_feed(url: str) -> dict | None:
    """Try to parse a URL as RSS/Atom. Returns feed info or None."""
    try:
        req = Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml",
        })
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read(50_000)  # only read first 50KB
        root = ET.fromstring(data)
    except Exception:
        return None

    # Count items
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    if not items:
        return None

    title = (
        root.findtext("channel/title")
        or root.findtext("{http://www.w3.org/2005/Atom}title")
        or ""
    ).strip()

    return {
        "title": title,
        "url": url,
        "item_count": len(items),
    }


def has_drone_content(feed_info: dict, url: str) -> bool:
    """Check if a feed URL or title suggests drone/UAV relevance."""
    text = f"{feed_info.get('title', '')} {url}".lower()
    return any(kw in text for kw in DRONE_KEYWORDS)


def load_existing_sources() -> set[str]:
    """Load existing source URLs from sources.json and discovered_sources.json."""
    urls: set[str] = set()
    for path in [SOURCES_PATH, DISCOVERED_PATH]:
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                if isinstance(item, dict) and item.get("url"):
                    urls.add(item["url"])
        except Exception:
            pass
    return urls


def crawl_seed(seed: dict, existing_urls: set[str]) -> list[dict]:
    """Crawl a single seed and return discovered source entries."""
    name = seed["name"]
    base_url = seed["url"]
    region = seed.get("region", "Global")
    content_class = seed.get("content_class")

    print(f"  [{region}] {name} — {base_url}")

    html = fetch_page(base_url)
    if not html:
        print(f"    ✗ 접근 불가")
        return []

    rss_links = discover_rss_links(html, base_url)

    # Always try common RSS paths as fallback
    parsed = urlparse(base_url)
    fallback_paths = [
        "/feed/", "/rss/", "/rss.xml", "/feed.xml", "/atom.xml",
        "/news/rss", "/news/feed", "/en/rss", "/rss/news.xml",
        "/newsroom/rss", "/media/rss", "/press/feed",
        "/rss/press.xml", "/rss/news", "/feeds/posts/default",
    ]
    for path in fallback_paths:
        candidate = f"{parsed.scheme}://{parsed.netloc}{path}"
        if candidate not in rss_links:
            rss_links.append(candidate)

    results: list[dict] = []
    for feed_url in rss_links[:15]:  # limit per seed
        if feed_url in existing_urls:
            continue

        feed_info = validate_rss_feed(feed_url)
        if not feed_info:
            continue

        # 기관 리포트 소스는 RSS만 유효하면 바로 채택
        # 일반 뉴스 소스만 드론 관련성 체크
        if content_class != "report" and not has_drone_content(feed_info, feed_url):
            continue

        source_id = f"src-discovered-{uuid.uuid4().hex[:8]}"
        entry = {
            "id": source_id,
            "name": feed_info["title"] or name,
            "type": "rss",
            "url": feed_url,
            "content_class": content_class,
            "discovered_from": base_url,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "region": region,
            "item_count": feed_info["item_count"],
        }

        # For general feeds, add drone relevance filter
        if not content_class:
            entry["must_contain_any"] = [
                "drone", "uav", "uas", "unmanned", "autonomous",
                "robot", "드론", "무인기", "ドローン", "无人机",
            ]

        results.append(entry)
        existing_urls.add(feed_url)
        print(f"    ✓ 발견: {feed_info['title'] or feed_url} ({feed_info['item_count']}건)")

    if not results:
        print(f"    — 새 피드 없음")

    return results


def run_crawl(regions: list[str] | None = None, dry_run: bool = False) -> list[dict]:
    """Run the source discovery crawl."""
    print("=" * 60)
    print("  Source Discovery Crawler")
    print(f"  시작: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    existing_urls = load_existing_sources()
    print(f"\n기존 소스: {len(existing_urls)}개 URL 등록됨\n")

    all_discovered: list[dict] = []

    # Load previously discovered sources to append
    if DISCOVERED_PATH.exists() and not dry_run:
        try:
            with DISCOVERED_PATH.open("r", encoding="utf-8") as f:
                all_discovered = json.load(f)
            existing_urls |= {s.get("url") for s in all_discovered if isinstance(s, dict)}
        except Exception:
            pass

    target_regions = regions or list(REGION_SEEDS.keys())

    for region_key in target_regions:
        seeds = REGION_SEEDS.get(region_key, [])
        if not seeds:
            print(f"\n⚠ 알 수 없는 지역: {region_key}")
            continue

        print(f"\n{'─' * 40}")
        print(f"  지역: {region_key.upper()} ({len(seeds)}개 시드)")
        print(f"{'─' * 40}")

        for seed in seeds:
            discovered = crawl_seed(seed, existing_urls)
            all_discovered.extend(discovered)

    # Count new
    new_count = sum(
        1 for s in all_discovered
        if isinstance(s, dict) and s.get("discovered_at", "").startswith(
            datetime.now(timezone.utc).date().isoformat()
        )
    )

    print(f"\n{'=' * 60}")
    print(f"  완료: 신규 {new_count}개 발견 / 총 {len(all_discovered)}개 누적")
    print(f"{'=' * 60}")

    if dry_run:
        print("\n[DRY RUN] 저장하지 않습니다.")
        if all_discovered:
            print(json.dumps(all_discovered[-5:], ensure_ascii=False, indent=2))
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with DISCOVERED_PATH.open("w", encoding="utf-8") as f:
            json.dump(all_discovered, f, ensure_ascii=False, indent=2)
        print(f"\n저장 완료: {DISCOVERED_PATH}")

    return all_discovered


def main():
    parser = argparse.ArgumentParser(
        description="지역별 기관 RSS 피드 자동 발견 크롤러"
    )
    parser.add_argument(
        "--region", "-r",
        nargs="*",
        help="탐색할 지역 (예: asia europe). 미지정 시 전체 탐색. "
             f"가능한 값: {', '.join(REGION_SEEDS.keys())}",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="결과를 파일에 저장하지 않고 출력만",
    )
    parser.add_argument(
        "--list-regions",
        action="store_true",
        help="사용 가능한 지역 목록 출력",
    )

    args = parser.parse_args()

    if args.list_regions:
        print("사용 가능한 지역:")
        for key, seeds in REGION_SEEDS.items():
            print(f"  {key:20s} — {len(seeds)}개 시드")
        return

    run_crawl(regions=args.region, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
