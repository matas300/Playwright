import pytest
from src.analyzer.neighborhoods import extract_neighborhood, normalize


CONFIG_NEIGHBORHOODS = {
    "green": ["senamiestis", "uzupis", "užupis", "naujamiestis", "zverynas", "žvėrynas", "paupys", "snipiskes", "šnipiškės", "antakalnis"],
    "yellow": ["seskine", "šeškinė", "zirmunai", "žirmūnai", "ozas", "akropolis"],
    "red": ["fabijoniskes", "fabijoniškės", "karoliniskes", "viršuliškės", "lazdynai"],
}


@pytest.mark.parametrize("text,expected_name,expected_tier", [
    ("Nuomoju butą Užupyje", "užupis", "green"),
    ("Apartment in Old Town Senamiestis", "senamiestis", "green"),
    ("Located in Žirmūnai near Akropolis", "žirmūnai", "yellow"),
    ("Free flat in Fabijoniškės", "fabijoniškės", "red"),
    ("Butas Snipiskese", "snipiskes", "green"),
    ("3 min walk to Ozas mall", "ozas", "yellow"),
    ("Apartment in Vilnius city center", None, None),
])
def test_extract_neighborhood(text, expected_name, expected_tier):
    name, tier = extract_neighborhood(text, CONFIG_NEIGHBORHOODS)
    assert name == expected_name
    assert tier == expected_tier


def test_normalize_strips_accents_and_lowercases():
    assert normalize("Užupis") == "uzupis"
    assert normalize("ŠEŠKINĖ") == "seskine"
    assert normalize("Antakalnis ") == "antakalnis"


def test_priority_green_beats_red():
    text = "Walking from Karoliniškės to Užupis"
    name, tier = extract_neighborhood(text, CONFIG_NEIGHBORHOODS)
    assert tier == "green"
    assert name == "užupis"
