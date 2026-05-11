import json
from pathlib import Path

from src.config import load_config, save_config


def _minimal_config():
    return {
        "groups": [],
        "budget": {"ideal_max": 999, "hard_max": 999, "near_budget_max": 999},
        "neighborhoods": {"green": [], "yellow": [], "red": []},
        "summer_window": {"start_no_later_than": "06-10", "end_no_earlier_than": "08-27"},
        "scan": {"lookback_hours": 36, "max_posts_per_group": 80, "delay_min_s": 2, "delay_max_s": 6},
    }


def test_load_config_creates_from_example_on_first_run(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    repo_root = Path(__file__).parent.parent
    assert (repo_root / "config.example.json").exists()
    config = load_config()
    assert "groups" in config
    assert config["budget"]["ideal_max"] == 600
    assert (tmp_path / "fb-bot-scan" / "config.json").exists()


def test_load_config_returns_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    runtime_dir = tmp_path / "fb-bot-scan"
    runtime_dir.mkdir(parents=True)
    custom = _minimal_config()
    (runtime_dir / "config.json").write_text(json.dumps(custom))
    config = load_config()
    assert config["budget"]["ideal_max"] == 999


def test_save_config_writes_to_runtime_path(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    config = _minimal_config()
    config["budget"]["ideal_max"] = 500
    save_config(config)
    loaded = json.loads((tmp_path / "fb-bot-scan" / "config.json").read_text())
    assert loaded["budget"]["ideal_max"] == 500
