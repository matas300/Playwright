import pytest
from src.analyzer.duration import extract_duration_signal


@pytest.mark.parametrize("text,expected", [
    ("Nuomoju vasarai", "summer"),
    ("For summer rent only", "summer"),
    ("Сдам на лето", "summer"),
    ("Vasaros laikotarpiui", "summer"),
    ("Laisvas iškart", "available_now"),
    ("Available now", "available_now"),
    ("Move in immediately", "available_now"),
    ("Можно сразу", "available_now"),
    ("Trumpalaikė nuoma", "short_term"),
    ("Short-term rental", "short_term"),
    ("Ilgalaikė nuoma metams", "long_term"),
    ("Long-term only please", "long_term"),
    ("Nuomoju butą Užupyje", None),
])
def test_extract_duration_signal(text, expected):
    assert extract_duration_signal(text) == expected


def test_summer_beats_long_term():
    assert extract_duration_signal("Vasarai, ilgalaikė nuoma negaliosima") == "summer"
