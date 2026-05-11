"""Duration signal extraction: summer / short_term / available_now / long_term."""
import re

_PATTERNS = [
    ("summer", [
        r"\bvasarai\b", r"\bvasaros\b", r"\bvasarą\b",
        r"\bна\s+лето\b",
        r"\bfor\s+summer\b", r"\bsummer\s+rent\b", r"\bsummer\s+only\b",
    ]),
    ("short_term", [
        r"\btrumpalaikė\b", r"\btrumpalaike\b", r"\btrumpam\b",
        r"\bshort[-\s]?term\b",
        r"\bкраткосрочн", r"\bна\s+короткий\s+срок\b",
    ]),
    ("available_now", [
        r"\biškart\b", r"\biskart\b", r"\bnuo\s+dabar\b", r"\bšiandien\b", r"\blaisvas\b",
        r"\bavailable\s+now\b", r"\bfree\s+now\b", r"\bmove\s+in(?:\s+immediately)?\b",
        r"\bсразу\b", r"\bсвободна\b",
    ]),
    ("long_term", [
        r"\bilgalaikė\b", r"\bilgalaike\b", r"\bilgam\b", r"\bmetams\b",
        r"\blong[-\s]?term\b",
        r"\bдолгосрочн", r"\bна\s+долгий\s+срок\b",
    ]),
]

_COMPILED = [(name, [re.compile(p, re.IGNORECASE | re.UNICODE) for p in pats]) for name, pats in _PATTERNS]


def extract_duration_signal(text: str) -> str | None:
    if not text:
        return None
    for name, patterns in _COMPILED:
        if any(p.search(text) for p in patterns):
            return name
    return None
