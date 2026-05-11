import os
from unittest.mock import patch

from src.paths import get_app_data_dir, get_config_path, get_db_path, get_auth_state_path, get_translator_cache_path


def test_get_app_data_dir_on_windows(tmp_path):
    with patch.dict(os.environ, {"APPDATA": str(tmp_path)}):
        result = get_app_data_dir()
        assert result == tmp_path / "fb-bot-scan"
        assert result.exists()
        assert result.is_dir()


def test_paths_are_inside_app_data(tmp_path):
    with patch.dict(os.environ, {"APPDATA": str(tmp_path)}):
        base = get_app_data_dir()
        assert get_config_path() == base / "config.json"
        assert get_db_path() == base / "posts.db"
        assert get_auth_state_path() == base / "auth_state.json"
        assert get_translator_cache_path() == base / "translator_cache.json"
