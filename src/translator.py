"""Translate Lithuanian post text to Italian via deep-translator with on-disk cache."""
import hashlib
import json
import time

from deep_translator import GoogleTranslator

from src.paths import get_translator_cache_path

_THROTTLE_S = 0.5
_last_call = 0.0


def _key(text: str, source_lang: str) -> str:
    return hashlib.sha256(f"{source_lang}::{text}".encode("utf-8")).hexdigest()


def _cache_load() -> dict:
    path = get_translator_cache_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _cache_save(cache: dict) -> None:
    get_translator_cache_path().write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def translate_to_italian(text: str, source_lang: str = "lt") -> str | None:
    global _last_call
    if not text:
        return ""

    cache = _cache_load()
    key = _key(text, source_lang)
    if key in cache:
        return cache[key]

    now = time.monotonic()
    delta = now - _last_call
    if delta < _THROTTLE_S:
        time.sleep(_THROTTLE_S - delta)

    try:
        translator = GoogleTranslator(source=source_lang, target="it")
        result = translator.translate(text)
        _last_call = time.monotonic()
        if result:
            cache[key] = result
            _cache_save(cache)
        return result
    except Exception:
        return None
