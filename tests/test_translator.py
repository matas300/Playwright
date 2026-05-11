from unittest.mock import patch, MagicMock
from src.translator import translate_to_italian


def test_translate_uses_deep_translator(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    mock_translator = MagicMock()
    mock_translator.translate.return_value = "Affitto appartamento"
    with patch("src.translator.GoogleTranslator", return_value=mock_translator):
        result = translate_to_italian("Nuomoju butą", source_lang="lt")
    assert result == "Affitto appartamento"
    mock_translator.translate.assert_called_once_with("Nuomoju butą")


def test_translate_caches_result(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    mock_translator = MagicMock()
    mock_translator.translate.return_value = "Ciao"
    with patch("src.translator.GoogleTranslator", return_value=mock_translator):
        translate_to_italian("Labas", source_lang="lt")
        translate_to_italian("Labas", source_lang="lt")
    assert mock_translator.translate.call_count == 1


def test_translate_returns_none_on_error(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    mock_translator = MagicMock()
    mock_translator.translate.side_effect = Exception("Rate limited")
    with patch("src.translator.GoogleTranslator", return_value=mock_translator):
        result = translate_to_italian("Test", source_lang="lt")
    assert result is None


def test_translate_empty_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert translate_to_italian("", source_lang="lt") == ""
