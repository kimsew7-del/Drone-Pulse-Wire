from __future__ import annotations

import html as html_mod
import json
import os
import re
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.models import NewsItem


# ── Module-level cache ────────────────────────────────────────

_topic_translation_cache: dict[str, str] = {}

_LANG_MAP = {
    "en": "en", "ko": "ko", "ja": "ja", "zh-CN": "zh-CN",
    "de": "de", "fr": "fr", "ar": "ar", "ru": "ru",
    "hi": "hi", "pt-BR": "pt",
}


# ── Detection ─────────────────────────────────────────────────


def looks_korean(text: str) -> bool:
    if not text:
        return False
    letters = re.findall(r"[a-zA-Z가-힣]", text)
    if not letters:
        return False
    korean_count = sum(1 for c in letters if "\uac00" <= c <= "\ud7a3")
    return korean_count / len(letters) > 0.3


def translation_enabled() -> bool:
    has_ollama = bool(os.environ.get("OLLAMA_MODEL", "").strip())
    has_papago = bool(os.environ.get("PAPAGO_CLIENT_ID", "").strip() and os.environ.get("PAPAGO_CLIENT_SECRET", "").strip())
    has_libre = bool(os.environ.get("LIBRETRANSLATE_URL", "").strip())
    return has_ollama or has_papago or has_libre


# ── Validation / cleaning ────────────────────────────────────


def is_valid_translation(translated: str, original: str) -> bool:
    if not translated or translated == original:
        return False
    letters = re.findall(r"[a-zA-Z가-힣]", translated)
    if not letters:
        return False
    korean_count = sum(1 for c in letters if "\uac00" <= c <= "\ud7a3")
    if korean_count / len(letters) < 0.15:
        return False
    if len(translated) < len(original) * 0.15:
        return False
    if len(translated) > len(original) * 5:
        return False
    junk_patterns = [r"^\.{2,}$", r"^N/?A$", r"^번역[:\s]", r"^Translation[:\s]"]
    for pattern in junk_patterns:
        if re.match(pattern, translated, re.IGNORECASE):
            return False
    return True


def cyrillic_to_korean(text: str) -> str:
    table = {
        "Зеленский": "젤렌스키", "Зеленський": "젤렌스키",
        "Путин": "푸틴", "Москва": "모스크바",
        "Украина": "우크라이나", "Россия": "러시아",
        "Киев": "키이우",
    }
    for cyrillic, korean in table.items():
        text = text.replace(cyrillic, korean)
    if re.search(r"[\u0400-\u04FF]", text):
        return ""
    return text


def clean_translation(text: str, mode: str) -> str:
    cleaned = " ".join((text or "").split())
    cleaned = re.sub(
        r"^(번역|한국어\s*번역|korean\s*translation|translation)\s*[:：]\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^['\"""'']+|['\"""'']+$", "", cleaned)
    cleaned = re.sub(r"[\u0400-\u04FF]+", lambda m: cyrillic_to_korean(m.group()), cleaned)
    if mode == "headline":
        cleaned = cleaned.rstrip(". ")
    return cleaned.strip()


# ── Engine: Ollama ────────────────────────────────────────────


def translate_with_ollama(text: str, mode: str = "summary", model_override: str | None = None) -> str | None:
    model = model_override or os.environ.get("OLLAMA_MODEL", "").strip()
    if not model:
        return None

    base_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").strip()
    system_prompt = (
        "You are a professional English-to-Korean translator for a drone/AI news service.\n"
        "Rules:\n"
        "- Output ONLY the Korean translation. No explanations, notes, labels, or quotation marks.\n"
        "- Write natural, fluent Korean news prose. Avoid awkward literal translation.\n"
        "- Domain terms: UAV=UAV, BVLOS=BVLOS, eVTOL=eVTOL, LiDAR=LiDAR, "
        "UTM=UTM, UAS=UAS, AI=AI, LLM=LLM, GCS=GCS.\n"
        "- Keep brand/person/product names in English or their common Korean form "
        "(e.g. DJI, Boeing, Skydio, NVIDIA).\n"
        "- Never output Cyrillic characters. Transliterate into Korean "
        "(e.g. Zelenskyy=젤렌스키, Putin=푸틴).\n"
        "- If the source is not English, still translate to Korean.\n"
    )
    if mode == "headline":
        user_prompt = (
            "Translate this headline to Korean. One sentence, no period.\n"
            "Example: \"DJI launches new autonomous drone for inspections\" → "
            "\"DJI, 점검용 자율비행 드론 신제품 출시\"\n\n"
            f"{text}"
        )
        max_tokens = 120
    else:
        user_prompt = (
            "Translate this summary to Korean. 1-3 sentences, no bullet points.\n"
            "Example: \"The FAA has approved new BVLOS rules for commercial drones, "
            "allowing operators to fly beyond visual line of sight in controlled airspace.\" → "
            "\"FAA가 상업용 드론의 BVLOS 비행 규정을 새로 승인하여 "
            "통제 공역 내에서 가시권 밖 비행이 가능해졌다.\"\n\n"
            f"{text}"
        )
        max_tokens = 300
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "options": {
            "temperature": 0.1,
            "num_predict": max_tokens,
        },
    }
    request = Request(
        f'{base_url.rstrip("/")}/api/chat',
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "DronePulseWire/0.1 (+https://localhost)",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=40) as response:
            body = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    return body.get("message", {}).get("content", "").strip() or None


# ── Engine: Papago ────────────────────────────────────────────


def translate_with_papago(text: str) -> str | None:
    client_id = os.environ.get("PAPAGO_CLIENT_ID", "").strip()
    client_secret = os.environ.get("PAPAGO_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None

    body = urlencode({"source": "auto", "target": "ko", "text": text}).encode("utf-8")
    request = Request(
        "https://papago.apigw.ntruss.com/nmt/v1/translation",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-NCP-APIGW-API-KEY-ID": client_id,
            "X-NCP-APIGW-API-KEY": client_secret,
            "User-Agent": "DronePulseWire/0.1 (+https://localhost)",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    return payload.get("message", {}).get("result", {}).get("translatedText")


# ── Engine: LibreTranslate ────────────────────────────────────


def translate_with_libretranslate(text: str) -> str | None:
    base_url = os.environ.get("LIBRETRANSLATE_URL", "").strip()
    if not base_url:
        return None

    params: dict[str, str] = {
        "q": text,
        "source": "auto",
        "target": "ko",
        "format": "text",
    }
    api_key = os.environ.get("LIBRETRANSLATE_API_KEY", "").strip()
    if api_key:
        params["api_key"] = api_key

    request = Request(
        f'{base_url.rstrip("/")}/translate',
        data=json.dumps(params, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "DronePulseWire/0.1 (+https://localhost)",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    return payload.get("translatedText")


# ── High-level translation ────────────────────────────────────


def translate_text_to_korean(
    text: str,
    mode: str = "summary",
    cache: dict[str, str] | None = None,
    force: bool = False,
) -> str:
    original = text or ""
    normalized = html_mod.unescape(" ".join(original.split()))
    if not normalized or looks_korean(normalized):
        return original
    cache_key = f"{mode}:{normalized}"
    if cache is not None and not force:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    if not translation_enabled():
        if cache is not None:
            cache[cache_key] = original
        return original

    translated = (
        translate_with_ollama(normalized, mode=mode)
        or translate_with_papago(normalized)
        or translate_with_libretranslate(normalized)
    )
    if translated:
        cleaned = clean_translation(translated.strip(), mode)
        if is_valid_translation(cleaned, normalized):
            if cache is not None:
                cache[cache_key] = cleaned
            return cleaned

    if cache is not None:
        cache.pop(cache_key, None)
    return original


def apply_korean_translation(
    item: NewsItem,
    cache: dict[str, str] | None = None,
    force: bool = False,
) -> None:
    translated_headline = translate_text_to_korean(item.headline, mode="headline", cache=cache, force=force)
    translated_summary = translate_text_to_korean(item.summary, mode="summary", cache=cache, force=force)
    item.translated_headline = (
        translated_headline if translated_headline and translated_headline != item.headline else ""
    )
    item.translated_summary = (
        translated_summary if translated_summary and translated_summary != item.summary else ""
    )
    item.translated_to_ko = bool(item.translated_headline or item.translated_summary)


# ── Topic translation (Google Translate free API) ─────────────


def translate_topic(text: str, lang_code: str) -> str:
    if lang_code == "ko":
        return text

    cache_key = f"{lang_code}:{text}"
    cached = _topic_translation_cache.get(cache_key)
    if cached:
        return cached

    target = _LANG_MAP.get(lang_code, lang_code)

    try:
        params = urlencode({
            "client": "gtx",
            "sl": "ko",
            "tl": target,
            "dt": "t",
            "q": text,
        })
        req = Request(
            f"https://translate.googleapis.com/translate_a/single?{params}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urlopen(req, timeout=5) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        translated = "".join(seg[0] for seg in raw[0] if seg[0])
        if translated and translated != text:
            _topic_translation_cache[cache_key] = translated
            return translated
    except Exception:
        pass

    translated = translate_with_papago(text)
    if translated and translated != text:
        _topic_translation_cache[cache_key] = translated
        return translated

    return text


def translate_to_korean_gtx(text: str) -> str:
    if not text or looks_korean(text):
        return text
    cache_key = f"ko:{text[:200]}"
    cached = _topic_translation_cache.get(cache_key)
    if cached:
        return cached
    try:
        params = urlencode({
            "client": "gtx",
            "sl": "auto",
            "tl": "ko",
            "dt": "t",
            "q": text[:500],
        })
        req = Request(
            f"https://translate.googleapis.com/translate_a/single?{params}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urlopen(req, timeout=5) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        translated = "".join(seg[0] for seg in raw[0] if seg[0])
        if translated and translated != text:
            _topic_translation_cache[cache_key] = translated
            return translated
    except Exception:
        pass
    return text


# ── Compare translations (all engines) ────────────────────────


def compare_translations(text: str, mode: str = "headline") -> dict[str, Any]:
    import time

    normalized = html_mod.unescape(" ".join((text or "").split()))
    if not normalized:
        return {"original": "", "results": []}

    base_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").strip()
    try:
        with urlopen(Request(f'{base_url.rstrip("/")}/api/tags', headers={"Accept": "application/json"}), timeout=5) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
        models = [m["name"] for m in tags.get("models", [])]
    except Exception:
        models = []

    results: list[dict[str, Any]] = []

    for model_name in models:
        start = time.monotonic()
        raw = translate_with_ollama(normalized, mode=mode, model_override=model_name)
        elapsed = round(time.monotonic() - start, 2)
        cleaned = clean_translation(raw.strip(), mode) if raw else None
        valid = is_valid_translation(cleaned, normalized) if cleaned else False
        results.append({
            "model": model_name,
            "engine": "ollama",
            "translation": cleaned if valid else raw,
            "raw": raw,
            "valid": valid,
            "elapsed_sec": elapsed,
        })

    for engine_name, engine_fn in [("papago", translate_with_papago), ("libretranslate", translate_with_libretranslate)]:
        start = time.monotonic()
        raw = engine_fn(normalized)
        elapsed = round(time.monotonic() - start, 2)
        if raw:
            cleaned = clean_translation(raw.strip(), mode)
            valid = is_valid_translation(cleaned, normalized)
            results.append({
                "model": engine_name,
                "engine": engine_name,
                "translation": cleaned if valid else raw,
                "raw": raw,
                "valid": valid,
                "elapsed_sec": elapsed,
            })

    return {"original": normalized, "mode": mode, "results": results}
