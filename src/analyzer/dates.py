"""Date range extraction from multi-language rental ad text."""
import re
from datetime import date
from calendar import monthrange

_MONTH_NAMES = {
    # Lithuanian
    "sausis": 1, "sausio": 1,
    "vasaris": 2, "vasario": 2,
    "kovas": 3, "kovo": 3,
    "balandis": 4, "balandzio": 4, "balandžio": 4,
    "geguzes": 5, "gegužės": 5, "geguze": 5, "gegužė": 5,
    "birzelis": 6, "birželis": 6, "birzelio": 6, "birželio": 6,
    "liepa": 7, "liepos": 7,
    "rugpjutis": 8, "rugpjūtis": 8, "rugpjucio": 8, "rugpjūčio": 8,
    "rugsejis": 9, "rugsėjis": 9, "rugsejo": 9, "rugsėjo": 9,
    "spalis": 10, "spalio": 10,
    "lapkritis": 11, "lapkricio": 11, "lapkričio": 11,
    "gruodis": 12, "gruodzio": 12, "gruodžio": 12,
    # English
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
    # Russian
    "январь": 1, "января": 1,
    "февраль": 2, "февраля": 2,
    "март": 3, "марта": 3,
    "апрель": 4, "апреля": 4,
    "май": 5, "мая": 5,
    "июнь": 6, "июня": 6,
    "июль": 7, "июля": 7,
    "август": 8, "августа": 8,
    "сентябрь": 9, "сентября": 9,
    "октябрь": 10, "октября": 10,
    "ноябрь": 11, "ноября": 11,
    "декабрь": 12, "декабря": 12,
}

_MONTH_PATTERN = "|".join(sorted(_MONTH_NAMES.keys(), key=len, reverse=True))

_RE_ISO_RANGE = re.compile(
    r"(\d{4})[\.\-/](\d{1,2})[\.\-/](\d{1,2})\s*[-–—]\s*"
    r"(\d{4})[\.\-/](\d{1,2})[\.\-/](\d{1,2})",
)

# DD.MM.YYYY - DD.MM.YYYY (European full date, year explicit)
_RE_EURO_FULL_RANGE = re.compile(
    r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s*[-–—]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})",
)

# MM.DD range (dot-separated, month first, no year): e.g. "06.01 - 09.01"
_RE_MMDOT_RANGE = re.compile(
    r"(\d{2})\.(\d{2})\s*[-–—]\s*(\d{2})\.(\d{2})",
)

# D/M or D-M range with word separator (to / по / iki / -)
_RE_SLASH_RANGE = re.compile(
    r"(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{4}|\d{2}))?\s*(?:[-–—]|to|iki|по|до)\s*"
    r"(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{4}|\d{2}))?",
    re.IGNORECASE,
)

_RE_NAMED_FULL = re.compile(
    rf"(?:nuo\s+|from\s+|с\s+)?(\d{{1,2}})?\s*({_MONTH_PATTERN})(?:\s+(\d{{1,2}}))?"
    rf"\s*(?:[-–—]|iki|to|по|до)\s*"
    rf"(\d{{1,2}})?\s*({_MONTH_PATTERN})(?:\s+(\d{{1,2}}))?",
    re.IGNORECASE,
)


def _parse_day(d, default: int) -> int:
    if d is None or d == "":
        return default
    return int(d)


def _last_day(year: int, month: int) -> int:
    return monthrange(year, month)[1]


def _resolve_year(y_str: str | None, current_year: int) -> int:
    if y_str is None:
        return current_year
    y = int(y_str)
    if len(y_str) == 2:
        y += 2000
    return y


def extract_date_range(text: str, current_year: int) -> tuple[date | None, date | None]:
    if not text:
        return None, None

    # YYYY.MM.DD - YYYY.MM.DD (ISO)
    if m := _RE_ISO_RANGE.search(text):
        try:
            start = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            end = date(int(m.group(4)), int(m.group(5)), int(m.group(6)))
            return start, end
        except ValueError:
            pass

    # DD.MM.YYYY - DD.MM.YYYY (European full date)
    if m := _RE_EURO_FULL_RANGE.search(text):
        try:
            d1, mo1, y1, d2, mo2, y2 = m.groups()
            start = date(int(y1), int(mo1), int(d1))
            end = date(int(y2), int(mo2), int(d2))
            return start, end
        except ValueError:
            pass

    # MM.DD (dot-separated two-digit, month first, no year): e.g. "06.01 - 09.01"
    if m := _RE_MMDOT_RANGE.search(text):
        try:
            mo1, d1, mo2, d2 = m.groups()
            start = date(current_year, int(mo1), int(d1))
            end = date(current_year, int(mo2), int(d2))
            return start, end
        except ValueError:
            pass

    # D/M or D-M with word separator (to / по / iki / -): e.g. "1/6 to 31/8"
    if m := _RE_SLASH_RANGE.search(text):
        try:
            d1, mo1, y1, d2, mo2, y2 = m.groups()
            year1 = _resolve_year(y1, current_year)
            year2 = _resolve_year(y2, current_year)
            start = date(year1, int(mo1), int(d1))
            end = date(year2, int(mo2), int(d2))
            return start, end
        except ValueError:
            pass

    if m := _RE_NAMED_FULL.search(text):
        day1_pre, month1, day1_post, day2_pre, month2, day2_post = m.groups()
        try:
            mo1 = _MONTH_NAMES[month1.lower()]
            mo2 = _MONTH_NAMES[month2.lower()]
            day1 = _parse_day(day1_pre or day1_post, default=1)
            day2 = _parse_day(day2_pre or day2_post, default=_last_day(current_year, mo2))
            start = date(current_year, mo1, day1)
            end = date(current_year, mo2, day2)
            return start, end
        except (ValueError, KeyError):
            pass

    return None, None
