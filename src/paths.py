"""Resolves runtime data paths in %APPDATA%/fb-bot-scan/ (or equivalent on non-Windows)."""
import os
from pathlib import Path


def get_app_data_dir() -> Path:
    if appdata := os.environ.get("APPDATA"):
        base = Path(appdata) / "fb-bot-scan"
    else:
        base = Path.home() / ".local" / "share" / "fb-bot-scan"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_config_path() -> Path:
    return get_app_data_dir() / "config.json"


def get_db_path() -> Path:
    return get_app_data_dir() / "posts.db"


def get_auth_state_path() -> Path:
    return get_app_data_dir() / "auth_state.json"


def get_translator_cache_path() -> Path:
    return get_app_data_dir() / "translator_cache.json"
