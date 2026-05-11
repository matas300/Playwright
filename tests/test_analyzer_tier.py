import pytest
from src.analyzer.tier import analyze_post


CONFIG = {
    "budget": {"ideal_max": 600, "hard_max": 650, "near_budget_max": 700},
    "summer_window": {"start_no_later_than": "06-10", "end_no_earlier_than": "08-27"},
    "neighborhoods": {
        "green": ["užupis", "senamiestis"],
        "yellow": ["žirmūnai"],
        "red": ["fabijoniškės"],
    },
}


def test_tier_S_summer_green_budget_ok():
    text = "Nuomoju butą Užupyje vasarai nuo birželio 1 iki rugpjūčio 31, 580 eur/mėn"
    result = analyze_post(text, CONFIG, current_year=2026)
    assert result.tier == "S"
    assert result.price_eur == 580
    assert result.neighborhood_tier == "green"
    assert "summer_explicit_match" in result.match_reasons


def test_tier_A_summer_yellow():
    text = "Žirmūnai vasarai 06.01 - 08.31, 620 eur"
    result = analyze_post(text, CONFIG, current_year=2026)
    assert result.tier == "A"


def test_tier_B_available_now_green():
    text = "Apartment in Senamiestis, available now, 550 eur/mėn"
    result = analyze_post(text, CONFIG, current_year=2026)
    assert result.tier == "B"


def test_tier_C_unclear_dates_green():
    text = "Butas Užupyje, 600 eur/mėn"
    result = analyze_post(text, CONFIG, current_year=2026)
    assert result.tier == "C"


def test_tier_E_summer_red():
    text = "Fabijoniškės vasarai 06.01 - 08.31, 500 eur"
    result = analyze_post(text, CONFIG, current_year=2026)
    assert result.tier == "E"


def test_tier_over_budget():
    text = "Užupis vasarai 06.01 - 08.31, 680 eur"
    result = analyze_post(text, CONFIG, current_year=2026)
    assert result.tier == "over_budget"


def test_tier_skip_over_700():
    text = "Užupis 06.01 - 08.31, 900 eur"
    result = analyze_post(text, CONFIG, current_year=2026)
    assert result.tier == "skip"


def test_tier_skip_long_term_explicit():
    text = "Senamiestis, ilgalaikė nuoma metams, 600 eur"
    result = analyze_post(text, CONFIG, current_year=2026)
    assert result.tier == "skip"


def test_summer_window_check_fails_for_too_late_start():
    text = "Užupis nuo birželio 15 iki rugpjūčio 31, 580 eur"
    result = analyze_post(text, CONFIG, current_year=2026)
    assert result.tier == "skip"
    assert "dates_conflict" in result.match_reasons
