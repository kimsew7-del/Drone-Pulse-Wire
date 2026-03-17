from __future__ import annotations

import html as html_mod
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


# -- Constants ---------------------------------------------------------

TOPIC_RULES = {
    "Drone + AI": [
        "autonomy",
        "autonomous",
        "computer vision",
        "edge ai",
        "drone ai",
        "swarm",
        "자율비행",
        "자율 비행",
        "드론 ai",
        "비전 ai",
        "군집",
    ],
    "Drone": [
        "drone",
        "uav",
        "bvlos",
        "quadcopter",
        "air mobility",
        "드론",
        "무인기",
        "u a m",
        "uam",
        "도심항공교통",
        "비행체",
    ],
    "AI": [
        "ai",
        "artificial intelligence",
        "llm",
        "vision model",
        "machine learning",
        "인공지능",
        "생성형 ai",
        "머신러닝",
        "딥러닝",
        "언어모델",
    ],
}

REGION_RULES = {
    "North America": ["united states", "canada", "north america", "us ", "u.s.", "faa", "nasa", "pentagon", "darpa"],
    "Europe": [
        "europe", "eu", "germany", "france", "uk", "britain", "ireland", "hungary", "easa",
        "italy", "spain", "netherlands", "sweden", "norway", "denmark", "finland", "poland",
        "dlr", "onera", "eu commission",
    ],
    "Korea": [
        "korea", "한국", "대한민국", "국내", "서울", "부산", "대구", "인천", "대전",
        "광주", "울산", "세종", "경기", "경북", "경남", "충북", "충남",
        "전북", "전남", "강원", "제주", "수원", "성남", "고양", "용인",
        "포항", "구미", "창원", "김해",
        "삼성", "현대", "lg전자", "sk", "카카오", "네이버", "두산",
        "한화", "기아", "산림청", "국방부", "과기부", "국토부", "중진공",
        "kaist", "연합뉴스", "조선일보", "중앙일보", "한겨레", "한국경제",
        "매일경제", "전자신문", "ytn",
    ],
    "China": [
        "china", "chinese", "beijing", "shanghai", "shenzhen", "dji",
        "中国", "中國", "北京", "上海", "深圳", "无人机", "caac",
    ],
    "Japan": [
        "japan", "japanese", "tokyo", "osaka",
        "日本", "東京", "ドローン", "jaxa", "mlit",
    ],
    "Southeast Asia": [
        "singapore", "thailand", "indonesia", "vietnam", "philippines", "malaysia",
        "southeast asia", "asean", "caas", "bangkok", "jakarta", "manila",
    ],
    "India": ["india", "indian", "delhi", "mumbai", "bangalore", "dgca india", "isro"],
    "Middle East": [
        "middle east", "saudi", "uae", "qatar", "israel", "dubai", "abu dhabi",
        "이란", "이스라엘", "두바이", "gcaa", "gaca",
    ],
    "Russia / CIS": [
        "russia", "russian", "moscow", "ukraine",
        "россия", "москва", "дрон", "бпла", "беспилотник",
    ],
    "Africa": [
        "africa", "african", "kenya", "nigeria", "south africa", "rwanda",
        "ghana", "ethiopia", "egypt", "morocco", "tanzania",
    ],
    "Latin America": [
        "brazil", "mexico", "colombia", "argentina", "chile", "peru",
        "latin america", "south america", "brasil", "méxico",
    ],
    "Oceania": ["australia", "australian", "new zealand", "casa australia"],
}

SOURCE_REGION_MAP = {
    # 한국
    "src-etnews-ai": "Korea",
    "src-etnews-drone-uam": "Korea",
    "src-google-news-kr-drone": "Korea",
    "src-google-news-kr-robot": "Korea",
    "src-newsapi-korea": "Korea",
    "src-gnews-korea": "Korea",
    "src-kci-korea-drone-ai": "Korea",
    "src-molit-kr": "Korea",
    "src-msit-kr": "Korea",
    "src-kari-kr": "Korea",
    "src-kiast-kr": "Korea",
    # 북미
    "src-suas-news": "North America",
    "src-faa-newsroom": "North America",
    "src-rand-uav": "North America",
    "src-gao-reports": "North America",
    "src-crs-reports": "North America",
    "src-brookings-ai": "North America",
    "src-nasa-uam": "North America",
    "src-darpa-news": "North America",
    # 유럽
    "src-unmanned-airspace": "Europe",
    "src-easa-reports": "Europe",
    "src-uk-caa": "Europe",
    "src-dlr-de": "Europe",
    "src-ec-transport": "Europe",
    "src-google-news-eu-drone": "Europe",
    # 중국
    "src-scmp-tech": "China",
    "src-xinhua-tech": "China",
    "src-google-news-cn-drone": "China",
    "src-caac-cn": "China",
    # 일본
    "src-google-news-jp-drone": "Japan",
    "src-mlit-jp": "Japan",
    "src-jaxa-jp": "Japan",
    "src-nedo-jp": "Japan",
    # 동남아
    "src-google-news-sea-drone": "Southeast Asia",
    "src-caas-sg": "Southeast Asia",
    "src-straits-times-tech": "Southeast Asia",
    "src-channelnewsasia-tech": "Southeast Asia",
    # 중동
    "src-aljazeera": "Middle East",
    "src-google-news-mideast-drone": "Middle East",
    "src-gulf-news-tech": "Middle East",
    "src-arabnews-tech": "Middle East",
    "src-uae-gcaa": "Middle East",
    # 러시아
    "src-google-news-ru-drone": "Russia / CIS",
    "src-tass-tech": "Russia / CIS",
    # 아프리카
    "src-google-news-africa-drone": "Africa",
    "src-techcabal-africa": "Africa",
    "src-africanews-tech": "Africa",
    "src-au-sti": "Africa",
    # 인도
    "src-google-news-india-drone": "India",
    "src-dgca-india": "India",
    # 오세아니아
    "src-google-news-au-drone": "Oceania",
    "src-casa-au": "Oceania",
    # 중남미
    "src-google-news-latam-drone": "Latin America",
    # 국제기구
    "src-wef-drones": "Global",
    "src-icao-news": "Global",
    "src-oecd-sti": "Global",
    "src-itu-news": "Global",
}

STOP_WORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "into",
    "new",
    "of",
    "on",
    "the",
    "to",
    "with",
    "this",
    "that",
    "its",
    "their",
    "how",
    "why",
}

GENERIC_TOKENS = {"ai", "drone", "drones", "uav", "news", "global", "드론", "인공지능", "뉴스"}

RESEARCH_RELEVANCE_TERMS = {
    "drone",
    "drones",
    "uav",
    "uas",
    "unmanned aerial",
    "quadcopter",
    "multirotor",
    "flight",
    "aerial",
    "swarm",
    "bvlos",
    "navigation",
    "airspace",
    "드론",
    "무인기",
    "자율비행",
    "비행",
    "항공",
    "군집",
    "도심항공교통",
}

DRONE_RELEVANCE_TERMS = {
    "drone",
    "drones",
    "uav",
    "uas",
    "unmanned aerial",
    "quadcopter",
    "multirotor",
    "aerial",
    "swarm",
    "bvlos",
    "airspace",
    "uam",
    "air mobility",
    "드론",
    "무인기",
    "자율비행",
    "비행체",
    "도심항공교통",
}

PHYSICAL_AI_RELEVANCE_TERMS = {
    "physical ai",
    "robot",
    "robots",
    "robotic",
    "robotics",
    "humanoid",
    "autonomous robot",
    "mobile robot",
    "manipulation",
    "sim2real",
    "world model",
    "embodied ai",
    "computer vision",
    "로봇",
    "로보틱스",
    "휴머노이드",
    "피지컬 ai",
    "자율로봇",
    "비전 ai",
    "월드모델",
    "시뮬레이션",
}

TREND_TERMS = [
    "drone",
    "uav",
    "swarm",
    "delivery",
    "ai",
    "autonomous",
    "robotics",
    "inspection",
    "mapping",
    "navigation",
    "vision",
    "airspace",
    "defense",
    "safety",
    "semiconductor",
    "edge",
]

CATEGORY_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can",
    "could", "do", "does", "for", "from", "had", "has", "have", "he", "her",
    "his", "how", "if", "in", "into", "is", "it", "its", "just", "may",
    "more", "most", "new", "no", "nor", "not", "now", "of", "on", "one",
    "only", "or", "our", "out", "over", "own", "say", "says", "said", "she",
    "should", "so", "some", "still", "such", "than", "that", "the", "their",
    "them", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "two", "up", "us", "use", "very", "was", "we", "well",
    "were", "what", "when", "where", "which", "while", "who", "why", "will",
    "with", "would", "you", "your",
    # 한국어 일반 불용어
    "있는", "하는", "위한", "대한", "통해", "이번", "것으로", "되는", "있다",
    "했다", "한다", "된다", "또한", "하며", "것이", "것을", "등의", "에서",
    "으로", "까지", "부터", "이다", "이며", "한편", "기자", "뉴스",
    # 도메인 일반 단어 (너무 흔해서 카테고리로 부적절)
    "drone", "drones", "uav", "ai", "news", "global", "technology",
    "tech", "report", "article", "update", "company", "industry",
    "드론", "인공지능", "기술", "시장", "업계", "관련",
}

RESEARCH_SOURCES = {
    "Crossref Drone AI Research",
    "Europe PMC AI Robotics",
    "KCI Korea Drone AI Papers",
    "AI",
    "AIP Conference Proceedings",
    "Lecture Notes in Networks and Systems",
    "International Journal of Advanced Research in Science, Communication and Technology",
    "Journal of Systemics, Cybernetics and Informatics",
    "Contributions to Security and Defence Studies",
}

REPORT_SOURCE_IDS = {
    # 미국
    "src-faa-newsroom", "src-rand-uav", "src-gao-reports",
    "src-crs-reports", "src-brookings-ai", "src-nasa-uam", "src-darpa-news",
    # 유럽
    "src-easa-reports", "src-uk-caa", "src-dlr-de", "src-ec-transport",
    # 국제기구
    "src-wef-drones", "src-icao-news", "src-oecd-sti", "src-itu-news",
    # 한국
    "src-molit-kr", "src-msit-kr", "src-kari-kr", "src-kiast-kr",
    # 일본
    "src-mlit-jp", "src-jaxa-jp", "src-nedo-jp",
    # 중국
    "src-caac-cn",
    # 동남아
    "src-caas-sg",
    # 중동
    "src-uae-gcaa",
    # 아프리카
    "src-au-sti",
    # 인도
    "src-dgca-india",
    # 오세아니아
    "src-casa-au",
}

_KOREAN_PARTICLES = re.compile(
    r"(은|는|이|가|을|를|의|에|에서|에게|로|으로|도|만|까지|부터|처럼|보다|와|과|라|며|고|지만|든지)$"
)


# -- Pure utility functions --------------------------------------------


def strip_korean_particles(token: str) -> str:
    if not token:
        return token
    prev = ""
    result = token
    while result != prev:
        prev = result
        result = _KOREAN_PARTICLES.sub("", result)
    return result or token


def infer_topic(text: str) -> str:
    matches = []
    for topic, keywords in TOPIC_RULES.items():
        score = sum(keyword in text for keyword in keywords)
        matches.append((score, topic))
    score, topic = max(matches)
    return topic if score else "Drone + AI"


def infer_region(text: str) -> str:
    matches = []
    for region, keywords in REGION_RULES.items():
        score = sum(keyword in text for keyword in keywords)
        matches.append((score, region))
    score, region = max(matches)
    return region if score else "Global"


def extract_highlights(text: str) -> list[str]:
    candidates = [
        "logistics",
        "inspection",
        "defense",
        "autonomy",
        "computer vision",
        "delivery",
        "mapping",
        "regulation",
        "safety",
        "research",
        "semiconductor",
        "infrastructure",
        "agriculture",
        "swarm",
        "자율비행",
        "인공지능",
        "로봇",
        "드론배송",
        "항공안전",
        "반도체",
        "군집",
    ]
    highlights = [word.title() for word in candidates if word in text]
    return highlights[:3] or ["Monitoring", "Automation", "Analysis"]


def score_impact(text: str, highlights: list[str]) -> int:
    base = 60 + min(len(highlights) * 6, 18)
    if "regulation" in text or "rule" in text:
        base += 10
    if "funding" in text or "investment" in text:
        base += 6
    if "research" in text or "model" in text:
        base += 4
    return min(base, 99)


def canonicalize(headline: str) -> str:
    lowered = headline.lower()
    lowered = re.sub(r"[^\w\s]", " ", lowered)
    tokens = [
        token
        for token in lowered.split()
        if token not in STOP_WORDS and token not in GENERIC_TOKENS and len(token) > 1
    ]
    return " ".join(tokens[:10])


def strip_html(value: str) -> str:
    result = []
    inside_tag = False
    for char in value:
        if char == "<":
            inside_tag = True
            continue
        if char == ">":
            inside_tag = False
            continue
        if not inside_tag:
            result.append(char)
    return html_mod.unescape(" ".join("".join(result).split())).strip()


def extract_xml_text(node: Any, candidates: list[str]) -> str:
    candidate_set = {name.lower() for name in candidates}
    for child in node.iter():
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in candidate_set and (child.text or "").strip():
            return child.text.strip()
    return ""


# -- Date parsers ------------------------------------------------------


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError):
        return None


def parse_runtime_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


def parse_kci_date(value: str | None) -> datetime | None:
    if not value:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    try:
        if len(digits) >= 6:
            return datetime(
                int(digits[:4]),
                int(digits[4:6]),
                1,
                tzinfo=timezone.utc,
            )
        if len(digits) >= 4:
            return datetime(int(digits[:4]), 1, 1, tzinfo=timezone.utc)
    except ValueError:
        return None
    return None


def parse_crossref_date(value: dict[str, Any] | None) -> datetime | None:
    if not value:
        return None
    date_parts = value.get("date-parts", [])
    if not date_parts:
        return None
    parts = date_parts[0]
    year = parts[0] if len(parts) > 0 else 1970
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    try:
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None


# -- Document classification -------------------------------------------


def classify_doc_type(url: str, source: str, title: str) -> str:
    url_lower = url.lower()
    source_lower = source.lower()
    title_lower = title.lower()

    if url_lower.endswith(".pdf"):
        return "보고서"

    gov_domains = (".gov", ".go.kr", ".gov.au", ".gov.uk", ".gc.ca", ".gob.", ".gov.br")
    intl_orgs = ("icao.int", "oecd.org", "itu.int", "weforum.org", "worldbank.org", "un.org")
    think_tanks = ("rand.org", "brookings.edu", "gao.gov", "crs", "carnegie", "cfr.org")

    if any(d in url_lower for d in gov_domains):
        return "정부문서"
    if any(d in url_lower for d in intl_orgs):
        return "국제기구"
    if any(d in source_lower for d in think_tanks) or any(d in url_lower for d in think_tanks):
        return "보고서"

    report_keywords = ["report", "whitepaper", "white paper", "보고서", "백서", "통계",
                       "analysis", "study", "guidelines", "framework", "규제", "정책",
                       "報告", "白書", "报告", "白皮书"]
    if any(kw in title_lower for kw in report_keywords):
        return "보고서"

    stats_keywords = ["statistics", "statistical", "forecast", "market size", "market share",
                      "infographic", "chart", "dataset", "data set", "open data",
                      "통계", "현황", "전망", "시장규모", "추이", "인포그래픽",
                      "데이터", "수치", "실적", "성장률",
                      "統計", "予測", "市場規模", "统计", "市场规模"]
    if any(kw in title_lower for kw in stats_keywords):
        return "통계"

    stats_domains = ("data.go.kr", "kosis.kr", "statista.com", "data.oecd.org",
                     "data.worldbank.org", "stats.oecd.org", "data.gov", "kaggle.com",
                     "e-stat.go.jp", "data.europa.eu")
    if any(d in url_lower for d in stats_domains):
        return "통계"

    paper_keywords = ["journal", "proceedings", "arxiv", "doi.org", "abstract",
                      "ieee", "acm", "springer", "elsevier", "wiley"]
    if any(kw in url_lower or kw in source_lower for kw in paper_keywords):
        return "논문"

    return "뉴스"


def classify_content_type(item: NewsItem, sources: list[dict[str, Any]]) -> str:
    if item.source_id in REPORT_SOURCE_IDS:
        return "report"
    source_cfg = next((s for s in sources if s.get("id") == item.source_id), None)
    if source_cfg and source_cfg.get("content_class") == "report":
        return "report"
    if item.source in RESEARCH_SOURCES:
        return "research"
    return "news"


# -- NewsItem dataclass ------------------------------------------------


@dataclass
class NewsItem:
    id: str
    topic: str
    region: str
    headline: str
    summary: str
    highlights: list[str]
    source: str
    impact: int
    timestamp: str
    url: str
    status: str = "queued"
    duplicate_group: str | None = None
    related_sources: list[str] = field(default_factory=list)
    duplicate_count: int = 0
    canonical_key: str = ""
    merged_summary: str | None = None
    related_articles: list[dict[str, str]] = field(default_factory=list)
    editor_note: str = ""
    source_id: str = ""
    translated_headline: str = ""
    translated_summary: str = ""
    translated_to_ko: bool = False
    auto_categories: list[str] = field(default_factory=list)
    content_type: str = "news"
    doc_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "region": self.region,
            "headline": self.headline,
            "summary": self.summary,
            "highlights": self.highlights,
            "source": self.source,
            "impact": self.impact,
            "timestamp": self.timestamp,
            "url": self.url,
            "status": self.status,
            "duplicate_group": self.duplicate_group,
            "related_sources": self.related_sources,
            "duplicate_count": self.duplicate_count,
            "merged_summary": self.merged_summary,
            "related_articles": self.related_articles,
            "editor_note": self.editor_note,
            "source_id": self.source_id,
            "translated_headline": self.translated_headline,
            "translated_summary": self.translated_summary,
            "translated_to_ko": self.translated_to_ko,
            "auto_categories": self.auto_categories,
            "content_type": self.content_type,
            "doc_type": self.doc_type,
        }


# -- Article normalization ---------------------------------------------


def normalize_article(
    headline: str,
    summary: str,
    source_name: str,
    source_id: str,
    url: str,
    sources: list[dict[str, Any]],
    published_at: datetime | None = None,
) -> NewsItem:
    text = f"{headline} {summary} {source_name}".lower()
    highlights = extract_highlights(text)
    topic = infer_topic(text)
    region = SOURCE_REGION_MAP.get(source_id) or infer_region(text)
    timestamp = (published_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    impact = score_impact(text, highlights)

    item = NewsItem(
        id=f"news-{uuid.uuid4().hex[:10]}",
        topic=topic,
        region=region,
        headline=headline or "Untitled article",
        summary=summary or "요약 정보가 아직 제공되지 않았습니다.",
        highlights=highlights,
        source=source_name,
        source_id=source_id,
        impact=impact,
        timestamp=timestamp.isoformat(),
        url=url,
        canonical_key=canonicalize(headline),
    )
    item.content_type = classify_content_type(item, sources)
    return item
