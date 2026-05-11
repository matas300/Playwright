"""Configuration load/save with fallback to config.example.json."""
import json
import shutil
from pathlib import Path

from src.paths import get_config_path

REPO_ROOT = Path(__file__).parent.parent
EXAMPLE_CONFIG = REPO_ROOT / "config.example.json"


def load_config() -> dict:
    path = get_config_path()
    if not path.exists():
        shutil.copy(EXAMPLE_CONFIG, path)
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    path = get_config_path()
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
