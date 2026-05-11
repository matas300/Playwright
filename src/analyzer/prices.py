"""Price extraction from rental ad text."""
import re

_PATTERNS = [
    re.compile(r"(\d{2,4})\s*(?:€|EUR|eur|Eur|euro|eurų|EU\b)", re.IGNORECASE),
    re.compile(r"(?:€|EUR|eur)\s*(\d{2,4})", re.IGNORECASE),
]

MIN_PRICE = 100
MAX_PRICE = 2000


def extract_price(text: str) -> int | None:
    """Return the highest plausible monthly price in EUR, or None."""
    if not text:
        return None
    candidates: list[int] = []
    for pattern in _PATTERNS:
        for match in pattern.finditer(text):
            try:
                val = int(match.group(1))
                if MIN_PRICE <= val <= MAX_PRICE:
                    candidates.append(val)
            except (ValueError, IndexError):
                continue
    return max(candidates) if candidates else None
