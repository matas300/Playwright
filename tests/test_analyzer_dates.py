import pytest
from datetime import date
from src.analyzer.dates import extract_date_range


CURRENT_YEAR = 2026


@pytest.mark.parametrize("text,expected_start,expected_end", [
    ("Nuoma 06.01 - 09.01", date(2026, 6, 1), date(2026, 9, 1)),
    ("Free from 1/6 to 31/8", date(2026, 6, 1), date(2026, 8, 31)),
    ("Period: 01.06.2026 - 31.08.2026", date(2026, 6, 1), date(2026, 8, 31)),
    ("Nuomoju nuo birželio 1 iki rugpjūčio 31", date(2026, 6, 1), date(2026, 8, 31)),
    ("Vasarai: birželis - rugpjūtis", date(2026, 6, 1), date(2026, 8, 31)),
    ("From June 5 to September 1", date(2026, 6, 5), date(2026, 9, 1)),
    ("С июня по август", date(2026, 6, 1), date(2026, 8, 31)),
    ("Nuomoju butą Užupyje", None, None),
])
def test_extract_date_range(text, expected_start, expected_end):
    start, end = extract_date_range(text, current_year=CURRENT_YEAR)
    assert start == expected_start
    assert end == expected_end
