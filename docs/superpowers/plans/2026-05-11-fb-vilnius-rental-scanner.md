# FB Bot Scan — Vilnius Rental Scanner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally-run web app that scans 4 private Facebook groups for Vilnius rental ads, filters them by date/neighborhood/budget, translates from Lithuanian to Italian, and presents results in a dashboard with editable filters.

**Architecture:** Flask web app + Playwright-driven scanner (manual trigger only) + SQLite storage + regex/keyword-based analyzer (no LLM). Runtime data lives in `%APPDATA%/fb-bot-scan/` to keep secrets out of OneDrive/git.

**Tech Stack:** Python 3.11+, Flask, Playwright (Chromium, headed), SQLite, deep-translator, python-dateutil.

**Spec reference:** `docs/superpowers/specs/2026-05-11-fb-vilnius-rental-scanner-design.md`

---

## File Structure

**Repo (committed to git):**
```
.gitignore                       # excludes data/, .venv/, __pycache__/, etc.
README.md                        # quickstart instructions
requirements.txt                 # Python deps
config.example.json              # template with defaults, no secrets
run.bat                          # Windows one-click launcher
src/
├── __init__.py
├── paths.py                     # %APPDATA% directory resolver
├── config.py                    # load/save config.json
├── models.py                    # dataclasses: Post, ScanRun
├── db.py                        # SQLite layer
├── translator.py                # deep-translator wrapper + cache
├── selectors.py                 # FB DOM selectors (isolated for FB updates)
├── scanner.py                   # Playwright orchestration
├── analyzer/
│   ├── __init__.py              # exposes analyze_post()
│   ├── prices.py                # extract_price()
│   ├── dates.py                 # extract_date_range()
│   ├── neighborhoods.py         # extract_neighborhood()
│   ├── duration.py              # extract_duration_signal()
│   └── tier.py                  # decide_tier() — orchestrator
├── app.py                       # Flask app + routes
├── scan_job.py                  # background scan thread + status state
templates/
├── base.html
├── index.html                   # dashboard
└── config_page.html
static/
├── style.css
└── app.js
tests/
├── __init__.py
├── conftest.py                  # pytest fixtures
├── test_paths.py
├── test_config.py
├── test_db.py
├── test_analyzer_prices.py
├── test_analyzer_dates.py
├── test_analyzer_neighborhoods.py
├── test_analyzer_duration.py
├── test_analyzer_tier.py
└── test_translator.py
docs/superpowers/...              # spec + plan
```

**Runtime data (NOT in git, in `%APPDATA%/fb-bot-scan/`):**
```
config.json                       # user's actual config (copied from example on first run)
auth_state.json                   # FB session cookies
posts.db                          # SQLite database
translator_cache.json             # translation cache
```

---

## Task 1: Project scaffold + git init

**Files:**
- Create: `.gitignore`, `requirements.txt`, `README.md`, `config.example.json`, `run.bat`
- Create: `src/__init__.py`, `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Create `.gitignore`**

Content:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.venv/
venv/
env/

# Runtime data — defense in depth, real data lives in %APPDATA%
data/
auth_state.json
config.json
*.db
translator_cache.json

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
desktop.ini

# Playwright
.playwright/
```

- [ ] **Step 2: Create `requirements.txt`**

```
flask>=3.0,<4.0
playwright>=1.41,<2.0
deep-translator>=1.11,<2.0
python-dateutil>=2.8,<3.0
pytest>=8.0,<9.0
```

- [ ] **Step 3: Create `config.example.json`**

```json
{
  "groups": [
    {"id": "", "share_url": "https://www.facebook.com/share/g/1CtQQmxeEF/", "name": "Gruppo 1", "enabled": true},
    {"id": "", "share_url": "https://www.facebook.com/share/g/1ASTG8yZqn/", "name": "Gruppo 2", "enabled": true},
    {"id": "", "share_url": "https://www.facebook.com/share/g/1PgoVa8t9r/", "name": "Gruppo 3", "enabled": true},
    {"id": "", "share_url": "https://www.facebook.com/share/g/1aVjok3F84/", "name": "Gruppo 4", "enabled": true}
  ],
  "budget": {"ideal_max": 600, "hard_max": 650, "near_budget_max": 700},
  "summer_window": {"start_no_later_than": "06-10", "end_no_earlier_than": "08-27"},
  "neighborhoods": {
    "green": ["senamiestis", "uzupis", "užupis", "naujamiestis", "zverynas", "žvėrynas", "paupys", "snipiskes", "šnipiškės", "antakalnis", "antakalniu"],
    "yellow": ["seskine", "šeškinė", "zirmunai", "žirmūnai", "ozas", "akropolis"],
    "red": ["fabijoniskes", "fabijoniškės", "karoliniskes", "karoliniškės", "virsuliskes", "viršuliškės", "lazdynai", "justiniskes", "justiniškės", "pilaite", "pilaitė", "naujininkai", "baltupiai", "jeruzale"]
  },
  "scan": {"lookback_hours": 36, "max_posts_per_group": 80, "delay_min_s": 2, "delay_max_s": 6}
}
```

- [ ] **Step 4: Create `README.md`**

```markdown
# FB Bot Scan — Vilnius Rental Scanner

Locally-run web app that scans private Facebook rental groups in Vilnius and surfaces relevant summer rental listings.

## Setup (Windows)

1. Install Python 3.11+
2. `python -m venv .venv`
3. `.venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `playwright install chromium`
6. Double-click `run.bat` (or run `python -m src.app`)
7. Open `http://localhost:5000` in your browser
8. Click "Login a Facebook" — a Chrome window opens, log in (2FA OK), session saved automatically

## Usage

- Click "Scansiona" to scan all enabled groups
- Use sticky filters at top of dashboard to narrow results without re-scanning
- Click on a card photo for full view; click "FB" to open original post
- Mark "Ignora" to hide a post from future views

## Data location

Cookies and database stored in `%APPDATA%\fb-bot-scan\` (NOT in this repo).

## Configuration

Edit defaults at `/config` page in the running app, or directly in `%APPDATA%\fb-bot-scan\config.json`.

## Design docs

- Spec: `docs/superpowers/specs/2026-05-11-fb-vilnius-rental-scanner-design.md`
- Plan: `docs/superpowers/plans/2026-05-11-fb-vilnius-rental-scanner.md`
```

- [ ] **Step 5: Create `run.bat`**

```bat
@echo off
cd /d "%~dp0"
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
    playwright install chromium
) else (
    call .venv\Scripts\activate.bat
)
python -m src.app
pause
```

- [ ] **Step 6: Create empty `src/__init__.py` and `tests/__init__.py`**

Both files empty.

- [ ] **Step 7: Create `tests/conftest.py`**

```python
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
```

- [ ] **Step 8: Init git and first commit**

```powershell
git init
git add .gitignore requirements.txt README.md config.example.json run.bat src/__init__.py tests/__init__.py tests/conftest.py docs/
git commit -m "chore: project scaffold and design docs"
```

Expected: clean commit with no `auth_state.json` / `config.json` / `*.db`.

---

## Task 2: Paths module (%APPDATA% resolver)

**Files:**
- Create: `src/paths.py`
- Test: `tests/test_paths.py`

- [ ] **Step 1: Write failing test**

`tests/test_paths.py`:

```python
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
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_paths.py -v`
Expected: `ImportError: No module named 'src.paths'`

- [ ] **Step 3: Implement `src/paths.py`**

```python
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
```

- [ ] **Step 4: Run tests, expect pass**

Run: `pytest tests/test_paths.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/paths.py tests/test_paths.py
git commit -m "feat: runtime path resolution for %APPDATA%/fb-bot-scan"
```

---

## Task 3: Models (dataclasses)

**Files:**
- Create: `src/models.py`

- [ ] **Step 1: Create `src/models.py`**

```python
"""Domain models for posts and scan runs."""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


@dataclass
class Post:
    id: str
    group_id: str
    url: str
    author_name: Optional[str] = None
    author_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    text_original: str = ""
    text_translated: Optional[str] = None
    language: Optional[str] = None
    price_eur: Optional[int] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    neighborhood: Optional[str] = None
    neighborhood_tier: Optional[str] = None
    duration_signal: Optional[str] = None
    tier: str = "skip"
    match_reasons: list[str] = field(default_factory=list)
    photo_urls: list[str] = field(default_factory=list)
    discovered_at: Optional[datetime] = None
    is_ignored: bool = False


@dataclass
class ScanRun:
    id: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str = "running"
    posts_found: int = 0
    posts_new: int = 0
    error_message: Optional[str] = None
```

- [ ] **Step 2: Smoke check**

Run: `python -c "from src.models import Post, ScanRun; p = Post(id='1', group_id='g', url='u'); print(p.tier)"`
Expected: `skip`

- [ ] **Step 3: Commit**

```powershell
git add src/models.py
git commit -m "feat: Post and ScanRun dataclasses"
```

---

## Task 4: Config loader

**Files:**
- Create: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

`tests/test_config.py`:

```python
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
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_config.py -v`
Expected: ImportError or 3 failures.

- [ ] **Step 3: Implement `src/config.py`**

```python
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
```

- [ ] **Step 4: Run tests, expect pass**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/config.py tests/test_config.py
git commit -m "feat: config loader with example bootstrap"
```

---

## Task 5: DB schema + initialization

**Files:**
- Create: `src/db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write failing test**

`tests/test_db.py`:

```python
from src.db import init_db, get_connection


def test_init_db_creates_tables(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    init_db()
    conn = get_connection()
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "posts" in tables
    assert "scan_runs" in tables
    conn.close()


def test_init_db_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    init_db()
    init_db()
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_db.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `src/db.py` skeleton**

```python
"""SQLite storage layer."""
import sqlite3

from src.paths import get_db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL,
  url TEXT NOT NULL,
  author_name TEXT,
  author_url TEXT,
  posted_at TIMESTAMP,
  text_original TEXT,
  text_translated TEXT,
  language TEXT,
  price_eur INTEGER,
  date_start DATE,
  date_end DATE,
  neighborhood TEXT,
  neighborhood_tier TEXT,
  duration_signal TEXT,
  tier TEXT NOT NULL,
  match_reasons TEXT,
  photo_urls TEXT,
  discovered_at TIMESTAMP NOT NULL,
  is_ignored INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tier ON posts(tier, discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_posted ON posts(posted_at DESC);

CREATE TABLE IF NOT EXISTS scan_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TIMESTAMP NOT NULL,
  ended_at TIMESTAMP,
  status TEXT,
  posts_found INTEGER DEFAULT 0,
  posts_new INTEGER DEFAULT 0,
  error_message TEXT
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests, expect pass**

Run: `pytest tests/test_db.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/db.py tests/test_db.py
git commit -m "feat: SQLite schema initialization"
```

---

## Task 6: DB — Post CRUD + dedup

**Files:**
- Modify: `src/db.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_db.py`:

```python
from datetime import datetime, date
from src.models import Post
from src.db import insert_post, get_post_by_id, get_posts, mark_ignored


def _sample_post(post_id: str = "abc123", tier: str = "S") -> Post:
    return Post(
        id=post_id,
        group_id="123456",
        url=f"https://facebook.com/groups/123456/posts/{post_id}",
        author_name="Test User",
        posted_at=datetime(2026, 5, 10, 14, 0, 0),
        text_original="Nuomoju butą",
        text_translated="Affitto appartamento",
        language="lt",
        price_eur=580,
        date_start=date(2026, 6, 1),
        date_end=date(2026, 8, 31),
        neighborhood="Užupis",
        neighborhood_tier="green",
        duration_signal="summer",
        tier=tier,
        match_reasons=["summer_explicit_match", "neighborhood_green"],
        photo_urls=["https://cdn/1.jpg"],
        discovered_at=datetime(2026, 5, 11, 14, 30, 0),
    )


def test_insert_and_get_post(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    init_db()
    insert_post(_sample_post())
    fetched = get_post_by_id("abc123")
    assert fetched is not None
    assert fetched.tier == "S"
    assert fetched.price_eur == 580
    assert fetched.match_reasons == ["summer_explicit_match", "neighborhood_green"]
    assert fetched.photo_urls == ["https://cdn/1.jpg"]
    assert fetched.date_start == date(2026, 6, 1)


def test_insert_post_dedupes_by_id(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    init_db()
    insert_post(_sample_post(tier="S"))
    inserted = insert_post(_sample_post(tier="C"))
    assert inserted is False
    fetched = get_post_by_id("abc123")
    assert fetched.tier == "S"


def test_get_posts_filters_by_tier(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    init_db()
    insert_post(_sample_post("p1", tier="S"))
    insert_post(_sample_post("p2", tier="C"))
    insert_post(_sample_post("p3", tier="skip"))
    results = get_posts(tiers=["S", "C"])
    assert {p.id for p in results} == {"p1", "p2"}


def test_mark_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    init_db()
    insert_post(_sample_post("p1"))
    mark_ignored("p1")
    assert get_post_by_id("p1").is_ignored is True


def test_get_posts_excludes_ignored_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    init_db()
    insert_post(_sample_post("p1"))
    insert_post(_sample_post("p2"))
    mark_ignored("p1")
    results = get_posts()
    assert {p.id for p in results} == {"p2"}
```

- [ ] **Step 2: Run tests, expect failure**

Run: `pytest tests/test_db.py -v`
Expected: 5 new failures.

- [ ] **Step 3: Implement Post CRUD in `src/db.py`**

Append to `src/db.py`:

```python
import json
from datetime import datetime, date
from typing import Optional, Iterable

from src.models import Post


def _post_to_row(post: Post) -> dict:
    return {
        "id": post.id,
        "group_id": post.group_id,
        "url": post.url,
        "author_name": post.author_name,
        "author_url": post.author_url,
        "posted_at": post.posted_at.isoformat() if post.posted_at else None,
        "text_original": post.text_original,
        "text_translated": post.text_translated,
        "language": post.language,
        "price_eur": post.price_eur,
        "date_start": post.date_start.isoformat() if post.date_start else None,
        "date_end": post.date_end.isoformat() if post.date_end else None,
        "neighborhood": post.neighborhood,
        "neighborhood_tier": post.neighborhood_tier,
        "duration_signal": post.duration_signal,
        "tier": post.tier,
        "match_reasons": json.dumps(post.match_reasons),
        "photo_urls": json.dumps(post.photo_urls),
        "discovered_at": (post.discovered_at or datetime.now()).isoformat(),
        "is_ignored": 1 if post.is_ignored else 0,
    }


def _row_to_post(row: sqlite3.Row) -> Post:
    return Post(
        id=row["id"],
        group_id=row["group_id"],
        url=row["url"],
        author_name=row["author_name"],
        author_url=row["author_url"],
        posted_at=datetime.fromisoformat(row["posted_at"]) if row["posted_at"] else None,
        text_original=row["text_original"] or "",
        text_translated=row["text_translated"],
        language=row["language"],
        price_eur=row["price_eur"],
        date_start=date.fromisoformat(row["date_start"]) if row["date_start"] else None,
        date_end=date.fromisoformat(row["date_end"]) if row["date_end"] else None,
        neighborhood=row["neighborhood"],
        neighborhood_tier=row["neighborhood_tier"],
        duration_signal=row["duration_signal"],
        tier=row["tier"],
        match_reasons=json.loads(row["match_reasons"]) if row["match_reasons"] else [],
        photo_urls=json.loads(row["photo_urls"]) if row["photo_urls"] else [],
        discovered_at=datetime.fromisoformat(row["discovered_at"]) if row["discovered_at"] else None,
        is_ignored=bool(row["is_ignored"]),
    )


def insert_post(post: Post) -> bool:
    """Insert a post. Returns True if newly inserted, False if duplicate (by id)."""
    conn = get_connection()
    try:
        row = _post_to_row(post)
        cursor = conn.execute(
            """INSERT OR IGNORE INTO posts (
                id, group_id, url, author_name, author_url, posted_at,
                text_original, text_translated, language,
                price_eur, date_start, date_end,
                neighborhood, neighborhood_tier, duration_signal,
                tier, match_reasons, photo_urls,
                discovered_at, is_ignored
            ) VALUES (
                :id, :group_id, :url, :author_name, :author_url, :posted_at,
                :text_original, :text_translated, :language,
                :price_eur, :date_start, :date_end,
                :neighborhood, :neighborhood_tier, :duration_signal,
                :tier, :match_reasons, :photo_urls,
                :discovered_at, :is_ignored
            )""",
            row,
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_post_by_id(post_id: str) -> Optional[Post]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        return _row_to_post(row) if row else None
    finally:
        conn.close()


def get_posts(
    tiers: Optional[Iterable[str]] = None,
    include_ignored: bool = False,
    limit: int = 500,
) -> list[Post]:
    conn = get_connection()
    try:
        query = "SELECT * FROM posts WHERE 1=1"
        params: list = []
        if tiers is not None:
            placeholders = ",".join("?" for _ in tiers)
            query += f" AND tier IN ({placeholders})"
            params.extend(tiers)
        if not include_ignored:
            query += " AND is_ignored = 0"
        query += " ORDER BY discovered_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [_row_to_post(r) for r in rows]
    finally:
        conn.close()


def mark_ignored(post_id: str) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE posts SET is_ignored = 1 WHERE id = ?", (post_id,))
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests, expect pass**

Run: `pytest tests/test_db.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/db.py tests/test_db.py
git commit -m "feat: Post CRUD with dedup and tier filtering"
```

---

## Task 7: DB — ScanRun tracking

**Files:**
- Modify: `src/db.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_db.py`:

```python
from src.models import ScanRun
from src.db import insert_scan_run, update_scan_run, get_latest_scan_run


def test_scan_run_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    init_db()
    run = ScanRun(started_at=datetime(2026, 5, 11, 14, 0), status="running")
    run_id = insert_scan_run(run)
    assert run_id > 0
    update_scan_run(run_id, status="done", ended_at=datetime(2026, 5, 11, 14, 5), posts_found=47, posts_new=12)
    latest = get_latest_scan_run()
    assert latest.status == "done"
    assert latest.posts_new == 12
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_db.py::test_scan_run_lifecycle -v`
Expected: ImportError.

- [ ] **Step 3: Implement ScanRun CRUD**

Append to `src/db.py`:

```python
from src.models import ScanRun


def insert_scan_run(run: ScanRun) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO scan_runs (started_at, ended_at, status, posts_found, posts_new, error_message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                (run.started_at or datetime.now()).isoformat(),
                run.ended_at.isoformat() if run.ended_at else None,
                run.status,
                run.posts_found,
                run.posts_new,
                run.error_message,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_scan_run(
    run_id: int,
    status: Optional[str] = None,
    ended_at: Optional[datetime] = None,
    posts_found: Optional[int] = None,
    posts_new: Optional[int] = None,
    error_message: Optional[str] = None,
) -> None:
    fields, params = [], []
    if status is not None:
        fields.append("status = ?"); params.append(status)
    if ended_at is not None:
        fields.append("ended_at = ?"); params.append(ended_at.isoformat())
    if posts_found is not None:
        fields.append("posts_found = ?"); params.append(posts_found)
    if posts_new is not None:
        fields.append("posts_new = ?"); params.append(posts_new)
    if error_message is not None:
        fields.append("error_message = ?"); params.append(error_message)
    if not fields:
        return
    params.append(run_id)
    conn = get_connection()
    try:
        conn.execute(f"UPDATE scan_runs SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
    finally:
        conn.close()


def get_latest_scan_run() -> Optional[ScanRun]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM scan_runs ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        return ScanRun(
            id=row["id"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            status=row["status"],
            posts_found=row["posts_found"] or 0,
            posts_new=row["posts_new"] or 0,
            error_message=row["error_message"],
        )
    finally:
        conn.close()
```

- [ ] **Step 4: Run test, expect pass**

Run: `pytest tests/test_db.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/db.py tests/test_db.py
git commit -m "feat: ScanRun lifecycle tracking"
```

---

## Task 8: Analyzer — price extraction

**Files:**
- Create: `src/analyzer/__init__.py`, `src/analyzer/prices.py`
- Test: `tests/test_analyzer_prices.py`

- [ ] **Step 1: Write failing tests**

`tests/test_analyzer_prices.py`:

```python
import pytest
from src.analyzer.prices import extract_price


@pytest.mark.parametrize("text,expected", [
    ("Nuomoju butą už 580 eur/mėn", 580),
    ("Kaina: 600€", 600),
    ("Price 650 EUR per month", 650),
    ("Nuomos kaina – 450 eurų", 450),
    ("€720 month rent", 720),
    ("Apartment in Užupis, 500 eur/mėn + utilities", 500),
    ("Kaina 500€, užstatas 250€", 500),
    ("Nuomoju butą Užupyje, susisiekite", None),
    ("Tel +37060012345 metai 2026", None),
    ("Užstatas 50 eur", None),
    ("Kaina 8000 EUR", None),
])
def test_extract_price(text, expected):
    assert extract_price(text) == expected
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_analyzer_prices.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

`src/analyzer/__init__.py` (empty for now).

`src/analyzer/prices.py`:

```python
"""Price extraction from rental ad text."""
import re

_PATTERNS = [
    re.compile(r"(\d{2,4})\s*(?:€|EUR|eur|Eur|euro|eurų|EU\b)", re.IGNORECASE),
    re.compile(r"(?:€|EUR|eur)\s*(\d{2,4})", re.IGNORECASE),
]

MIN_PRICE = 100
MAX_PRICE = 2000


def extract_price(text: str) -> int | None:
    """Return the highest plausible monthly price in EUR, or None."""
    if not text:
        return None
    candidates: list[int] = []
    for pattern in _PATTERNS:
        for match in pattern.finditer(text):
            try:
                val = int(match.group(1))
                if MIN_PRICE <= val <= MAX_PRICE:
                    candidates.append(val)
            except (ValueError, IndexError):
                continue
    return max(candidates) if candidates else None
```

- [ ] **Step 4: Run tests, expect pass**

Run: `pytest tests/test_analyzer_prices.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/analyzer/__init__.py src/analyzer/prices.py tests/test_analyzer_prices.py
git commit -m "feat(analyzer): price extraction from multi-language text"
```

---

## Task 9: Analyzer — date extraction

**Files:**
- Create: `src/analyzer/dates.py`
- Test: `tests/test_analyzer_dates.py`

- [ ] **Step 1: Write failing tests**

`tests/test_analyzer_dates.py`:

```python
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
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_analyzer_dates.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `src/analyzer/dates.py`**

```python
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

_RE_NUMERIC_RANGE = re.compile(
    r"(\d{1,2})[\.\-/](\d{1,2})(?:[\.\-/](\d{4}|\d{2}))?\s*[-–—]\s*"
    r"(\d{1,2})[\.\-/](\d{1,2})(?:[\.\-/](\d{4}|\d{2}))?",
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


def extract_date_range(text: str, current_year: int) -> tuple[date | None, date | None]:
    if not text:
        return None, None

    if m := _RE_ISO_RANGE.search(text):
        try:
            start = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            end = date(int(m.group(4)), int(m.group(5)), int(m.group(6)))
            return start, end
        except ValueError:
            pass

    if m := _RE_NUMERIC_RANGE.search(text):
        try:
            d1, mo1, y1, d2, mo2, y2 = m.groups()
            year1 = int(y1) if y1 else current_year
            year2 = int(y2) if y2 else current_year
            if y1 and len(y1) == 2:
                year1 += 2000
            if y2 and len(y2) == 2:
                year2 += 2000
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
```

- [ ] **Step 4: Run tests, expect pass**

Run: `pytest tests/test_analyzer_dates.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/analyzer/dates.py tests/test_analyzer_dates.py
git commit -m "feat(analyzer): date range extraction (LT/EN/RU, numeric and named)"
```

---

## Task 10: Analyzer — neighborhood detection

**Files:**
- Create: `src/analyzer/neighborhoods.py`
- Test: `tests/test_analyzer_neighborhoods.py`

- [ ] **Step 1: Write failing tests**

`tests/test_analyzer_neighborhoods.py`:

```python
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
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_analyzer_neighborhoods.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `src/analyzer/neighborhoods.py`**

```python
"""Neighborhood detection with tier priority green > yellow > red."""
import re
import unicodedata


def normalize(s: str) -> str:
    s = s.strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _find_match(text_norm: str, candidates: list[str]) -> str | None:
    matches = []
    for original in candidates:
        norm = normalize(original)
        if re.search(rf"\b{re.escape(norm)}", text_norm):
            matches.append(original)
    if not matches:
        return None
    return max(matches, key=len)


def extract_neighborhood(text: str, neighborhoods_cfg: dict) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    text_norm = normalize(text)
    for tier in ("green", "yellow", "red"):
        if match := _find_match(text_norm, neighborhoods_cfg.get(tier, [])):
            return match, tier
    return None, None
```

- [ ] **Step 4: Run tests, expect pass**

Run: `pytest tests/test_analyzer_neighborhoods.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/analyzer/neighborhoods.py tests/test_analyzer_neighborhoods.py
git commit -m "feat(analyzer): tier-prioritized neighborhood detection"
```

---

## Task 11: Analyzer — duration signal detection

**Files:**
- Create: `src/analyzer/duration.py`
- Test: `tests/test_analyzer_duration.py`

- [ ] **Step 1: Write failing tests**

`tests/test_analyzer_duration.py`:

```python
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
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_analyzer_duration.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `src/analyzer/duration.py`**

```python
"""Duration signal extraction: summer / short_term / available_now / long_term."""
import re

_PATTERNS = [
    ("summer", [
        r"\bvasarai\b", r"\bvasaros\b", r"\bvasarą\b",
        r"\bна\s+лето\b",
        r"\bfor\s+summer\b", r"\bsummer\s+rent\b", r"\bsummer\s+only\b",
    ]),
    ("short_term", [
        r"\btrumpalaikė\b", r"\btrumpalaike\b", r"\btrumpam\b",
        r"\bshort[-\s]?term\b",
        r"\bкраткосрочн", r"\bна\s+короткий\s+срок\b",
    ]),
    ("available_now", [
        r"\biškart\b", r"\biskart\b", r"\bnuo\s+dabar\b", r"\bšiandien\b", r"\blaisvas\b",
        r"\bavailable\s+now\b", r"\bfree\s+now\b", r"\bmove\s+in(?:\s+immediately)?\b",
        r"\bсразу\b", r"\bсвободна\b",
    ]),
    ("long_term", [
        r"\bilgalaikė\b", r"\bilgalaike\b", r"\bilgam\b", r"\bmetams\b",
        r"\blong[-\s]?term\b",
        r"\bдолгосрочн", r"\bна\s+долгий\s+срок\b",
    ]),
]

_COMPILED = [(name, [re.compile(p, re.IGNORECASE | re.UNICODE) for p in pats]) for name, pats in _PATTERNS]


def extract_duration_signal(text: str) -> str | None:
    if not text:
        return None
    for name, patterns in _COMPILED:
        if any(p.search(text) for p in patterns):
            return name
    return None
```

- [ ] **Step 4: Run tests, expect pass**

Run: `pytest tests/test_analyzer_duration.py -v`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/analyzer/duration.py tests/test_analyzer_duration.py
git commit -m "feat(analyzer): duration signal detection"
```

---

## Task 12: Analyzer — tier decision orchestrator

**Files:**
- Create: `src/analyzer/tier.py`
- Modify: `src/analyzer/__init__.py`
- Test: `tests/test_analyzer_tier.py`

- [ ] **Step 1: Write failing tests**

`tests/test_analyzer_tier.py`:

```python
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
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_analyzer_tier.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `src/analyzer/tier.py`**

```python
"""Combine price/date/neighborhood/duration signals into a final tier."""
from dataclasses import dataclass, field
from datetime import date

from src.analyzer.prices import extract_price
from src.analyzer.dates import extract_date_range
from src.analyzer.neighborhoods import extract_neighborhood
from src.analyzer.duration import extract_duration_signal


@dataclass
class AnalyzedPost:
    price_eur: int | None = None
    date_start: date | None = None
    date_end: date | None = None
    neighborhood: str | None = None
    neighborhood_tier: str | None = None
    duration_signal: str | None = None
    tier: str = "skip"
    match_reasons: list[str] = field(default_factory=list)


def _parse_mm_dd(s: str, year: int) -> date:
    mo, d = s.split("-")
    return date(year, int(mo), int(d))


def _is_summer_match(start: date | None, end: date | None, cfg: dict, year: int) -> tuple[bool, bool]:
    """Returns (is_match, is_conflict).

    is_match: explicit dates cover required window
    is_conflict: explicit dates exist but DON'T cover the window
    """
    if start is None or end is None:
        return False, False
    target_start = _parse_mm_dd(cfg["summer_window"]["start_no_later_than"], year)
    target_end = _parse_mm_dd(cfg["summer_window"]["end_no_earlier_than"], year)
    if start <= target_start and end >= target_end:
        return True, False
    return False, True


def analyze_post(text: str, config: dict, current_year: int) -> AnalyzedPost:
    result = AnalyzedPost()
    if not text:
        result.tier = "skip"
        result.match_reasons = ["empty_text"]
        return result

    result.price_eur = extract_price(text)
    result.date_start, result.date_end = extract_date_range(text, current_year=current_year)
    result.neighborhood, result.neighborhood_tier = extract_neighborhood(text, config["neighborhoods"])
    result.duration_signal = extract_duration_signal(text)

    budget = config["budget"]
    is_summer, is_conflict = _is_summer_match(result.date_start, result.date_end, config, current_year)

    reasons = []
    if is_summer:
        reasons.append("summer_explicit_match")
    if is_conflict:
        reasons.append("dates_conflict")
    if result.duration_signal:
        reasons.append(f"duration_{result.duration_signal}")
    if result.neighborhood_tier:
        reasons.append(f"neighborhood_{result.neighborhood_tier}")

    if is_conflict and not is_summer:
        result.tier = "skip"
        result.match_reasons = reasons
        return result
    if result.duration_signal == "long_term" and not is_summer:
        result.tier = "skip"
        result.match_reasons = reasons + ["explicit_long_term"]
        return result
    if result.price_eur is not None and result.price_eur > budget["near_budget_max"]:
        result.tier = "skip"
        result.match_reasons = reasons + ["over_max_budget"]
        return result

    in_hard_budget = result.price_eur is None or result.price_eur <= budget["hard_max"]
    in_near_budget = result.price_eur is not None and budget["hard_max"] < result.price_eur <= budget["near_budget_max"]

    if is_summer:
        if not in_hard_budget and in_near_budget:
            result.tier = "over_budget"
        elif result.neighborhood_tier == "green":
            result.tier = "S"
        elif result.neighborhood_tier == "yellow":
            result.tier = "A"
        elif result.neighborhood_tier == "red":
            result.tier = "E"
        else:
            result.tier = "B"
        result.match_reasons = reasons
        return result

    if result.duration_signal == "available_now":
        if not in_hard_budget and in_near_budget:
            result.tier = "over_budget"
        elif result.neighborhood_tier == "green":
            result.tier = "B"
        elif result.neighborhood_tier == "yellow":
            result.tier = "D"
        elif result.neighborhood_tier == "red":
            result.tier = "E"
        else:
            result.tier = "C"
        result.match_reasons = reasons
        return result

    if result.date_start is None and result.date_end is None:
        if not in_hard_budget and in_near_budget:
            result.tier = "over_budget"
        elif result.neighborhood_tier == "green":
            result.tier = "C"
        elif result.neighborhood_tier == "yellow":
            result.tier = "D"
        elif result.neighborhood_tier == "red":
            result.tier = "skip"
        else:
            result.tier = "C"
        result.match_reasons = reasons
        return result

    result.tier = "skip"
    result.match_reasons = reasons + ["no_match"]
    return result
```

- [ ] **Step 4: Update `src/analyzer/__init__.py`**

```python
"""Analyzer entrypoint."""
from src.analyzer.tier import analyze_post, AnalyzedPost

__all__ = ["analyze_post", "AnalyzedPost"]
```

- [ ] **Step 5: Run tests, expect pass**

Run: `pytest tests/test_analyzer_tier.py -v`
Expected: 9 passed.

- [ ] **Step 6: Commit**

```powershell
git add src/analyzer/tier.py src/analyzer/__init__.py tests/test_analyzer_tier.py
git commit -m "feat(analyzer): tier decision orchestrator"
```

---

## Task 13: Translator with cache

**Files:**
- Create: `src/translator.py`
- Test: `tests/test_translator.py`

- [ ] **Step 1: Write failing tests**

`tests/test_translator.py`:

```python
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
```

- [ ] **Step 2: Run test, expect failure**

Run: `pytest tests/test_translator.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `src/translator.py`**

```python
"""Translate Lithuanian post text to Italian via deep-translator with on-disk cache."""
import hashlib
import json
import time

from deep_translator import GoogleTranslator

from src.paths import get_translator_cache_path

_THROTTLE_S = 0.5
_last_call = 0.0


def _key(text: str, source_lang: str) -> str:
    return hashlib.sha256(f"{source_lang}::{text}".encode("utf-8")).hexdigest()


def _cache_load() -> dict:
    path = get_translator_cache_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _cache_save(cache: dict) -> None:
    get_translator_cache_path().write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def translate_to_italian(text: str, source_lang: str = "lt") -> str | None:
    global _last_call
    if not text:
        return ""

    cache = _cache_load()
    key = _key(text, source_lang)
    if key in cache:
        return cache[key]

    now = time.monotonic()
    delta = now - _last_call
    if delta < _THROTTLE_S:
        time.sleep(_THROTTLE_S - delta)

    try:
        translator = GoogleTranslator(source=source_lang, target="it")
        result = translator.translate(text)
        _last_call = time.monotonic()
        if result:
            cache[key] = result
            _cache_save(cache)
        return result
    except Exception:
        return None
```

- [ ] **Step 4: Run tests, expect pass**

Run: `pytest tests/test_translator.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/translator.py tests/test_translator.py
git commit -m "feat: translator with on-disk cache and throttling"
```

---

## Task 14: Selectors module

**Files:**
- Create: `src/selectors.py`

- [ ] **Step 1: Create `src/selectors.py`**

```python
"""Facebook DOM selectors. Isolated here because FB changes them often.

If scanning breaks, update these first. Last verified: 2026-05-11
"""

POST_ARTICLE = '[role="feed"] [role="article"]'
POST_PERMALINK = 'a[href*="/groups/"][href*="/posts/"], a[href*="/groups/"][href*="/permalink/"]'
POST_AUTHOR_NAME = 'strong span, h3 span'
POST_AUTHOR_LINK = 'a[href*="/user/"]'
POST_TIMESTAMP = 'a[href*="/posts/"] span[id], a[href*="/permalink/"] span[id]'
POST_TEXT_CONTAINER = '[data-ad-comet-preview="message"], [data-ad-preview="message"]'
POST_PHOTO_IMG = 'img[data-visualcompletion="media-vc-image"]'
POST_SEE_MORE_BUTTON = 'div[role="button"]:has-text("See more"), div[role="button"]:has-text("Daugiau"), div[role="button"]:has-text("Ещё")'

LOGIN_FORM_INPUT = 'input[name="email"]'
LOGIN_PROFILE_INDICATOR = '[aria-label="Your profile"], [role="banner"] [role="navigation"]'

GROUP_URL_TEMPLATE = "https://www.facebook.com/groups/{group_id}"
```

- [ ] **Step 2: Smoke check**

Run: `python -c "from src.selectors import POST_ARTICLE; print(POST_ARTICLE)"`
Expected: `[role="feed"] [role="article"]`

- [ ] **Step 3: Commit**

```powershell
git add src/selectors.py
git commit -m "feat: FB DOM selectors module"
```

---

## Task 15: Scanner — login + group ID resolution

**Files:**
- Create: `src/scanner.py`

⚠️ **Scanner is integration-heavy. We build it iteratively with manual smoke tests.**

- [ ] **Step 1: Create `src/scanner.py` skeleton**

```python
"""Playwright-driven scanner for FB rental groups."""
import random
import re
import time
from datetime import datetime, timedelta
from typing import Iterator

from playwright.sync_api import sync_playwright, BrowserContext

from src.paths import get_auth_state_path
from src import selectors as sel


class SessionExpiredError(Exception):
    pass


def _parse_relative_time(label: str, now: datetime) -> datetime | None:
    """Convert FB relative timestamps like '2 h', '3 d' to datetime."""
    if not label:
        return None
    m = re.match(r"(\d+)\s*(min|h|hr|d|day|w|wk|val|d\.)", label.lower().strip())
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    if unit == "min":
        return now - timedelta(minutes=n)
    if unit in ("h", "hr", "val"):
        return now - timedelta(hours=n)
    if unit in ("d", "day", "d."):
        return now - timedelta(days=n)
    if unit in ("w", "wk"):
        return now - timedelta(weeks=n)
    return None


class Scanner:
    def __init__(self, headless: bool = False, delay_range: tuple[float, float] = (2.0, 6.0)):
        self.headless = headless
        self.delay_min, self.delay_max = delay_range
        self._pw = None
        self._browser = None
        self._context: BrowserContext | None = None

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        auth_path = get_auth_state_path()
        storage = str(auth_path) if auth_path.exists() else None
        self._context = self._browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 800},
        )
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def _human_pause(self):
        time.sleep(random.uniform(self.delay_min, self.delay_max))

    def interactive_login(self) -> None:
        page = self._context.new_page()
        page.goto("https://www.facebook.com/login", timeout=60000)
        print("Effettua il login a Facebook nella finestra Chrome aperta.")
        for _ in range(60):
            time.sleep(5)
            try:
                if page.locator(sel.LOGIN_PROFILE_INDICATOR).first.is_visible(timeout=1000):
                    break
            except Exception:
                continue
        else:
            raise TimeoutError("Login non completato entro 5 minuti.")
        self._context.storage_state(path=str(get_auth_state_path()))
        page.close()

    def resolve_group_id(self, share_url: str) -> str | None:
        page = self._context.new_page()
        try:
            page.goto(share_url, timeout=30000, wait_until="domcontentloaded")
            self._human_pause()
            if m := re.search(r"/groups/(\d+)", page.url):
                return m.group(1)
            return None
        finally:
            page.close()

    def is_session_valid(self) -> bool:
        page = self._context.new_page()
        try:
            page.goto("https://www.facebook.com/", timeout=15000)
            return page.locator(sel.LOGIN_PROFILE_INDICATOR).first.is_visible(timeout=3000)
        except Exception:
            return False
        finally:
            page.close()

    def scan_group(self, group_id: str, lookback_hours: int = 36, max_posts: int = 80) -> Iterator[dict]:
        """Yield post dicts from a group feed. Stops at lookback cutoff or max_posts."""
        page = self._context.new_page()
        try:
            page.goto(sel.GROUP_URL_TEMPLATE.format(group_id=group_id), timeout=30000, wait_until="domcontentloaded")
            self._human_pause()

            if page.locator(sel.LOGIN_FORM_INPUT).count() > 0:
                raise SessionExpiredError("Redirected to login when accessing group.")

            cutoff = datetime.now() - timedelta(hours=lookback_hours)
            seen: set[str] = set()
            dry_scrolls = 0
            max_dry = 5

            while len(seen) < max_posts:
                articles = page.locator(sel.POST_ARTICLE).all()
                new_in_pass = 0
                oldest_in_pass: datetime | None = None

                for art in articles:
                    try:
                        permalink_el = art.locator(sel.POST_PERMALINK).first
                        if permalink_el.count() == 0:
                            continue
                        href = permalink_el.get_attribute("href") or ""
                        pm = re.search(r"/(?:posts|permalink)/(\d+)", href)
                        if not pm:
                            continue
                        post_id = pm.group(1)
                        if post_id in seen:
                            continue

                        try:
                            see_more = art.locator(sel.POST_SEE_MORE_BUTTON).first
                            if see_more.count() > 0 and see_more.is_visible():
                                see_more.click(timeout=2000)
                                time.sleep(0.5)
                        except Exception:
                            pass

                        text_container = art.locator(sel.POST_TEXT_CONTAINER).first
                        text = text_container.inner_text() if text_container.count() > 0 else ""

                        ts_el = art.locator(sel.POST_TIMESTAMP).first
                        ts_label = ts_el.inner_text() if ts_el.count() > 0 else ""
                        posted_at = _parse_relative_time(ts_label, datetime.now())

                        photo_urls = []
                        for img in art.locator(sel.POST_PHOTO_IMG).all()[:6]:
                            src = img.get_attribute("src")
                            if src:
                                photo_urls.append(src)

                        author_el = art.locator(sel.POST_AUTHOR_NAME).first
                        author_name = author_el.inner_text() if author_el.count() > 0 else None

                        full_url = f"https://www.facebook.com{href}" if href.startswith("/") else href

                        seen.add(post_id)
                        new_in_pass += 1
                        if posted_at and (oldest_in_pass is None or posted_at < oldest_in_pass):
                            oldest_in_pass = posted_at

                        yield {
                            "id": post_id,
                            "group_id": group_id,
                            "url": full_url,
                            "author_name": author_name,
                            "posted_at": posted_at,
                            "text": text,
                            "photo_urls": photo_urls,
                        }
                    except Exception as e:
                        print(f"[scan_group] skip article: {e}")
                        continue

                if oldest_in_pass and oldest_in_pass < cutoff:
                    break
                if new_in_pass == 0:
                    dry_scrolls += 1
                    if dry_scrolls >= max_dry:
                        break
                else:
                    dry_scrolls = 0

                page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
                self._human_pause()
        finally:
            page.close()
```

- [ ] **Step 2: Smoke check**

Run: `python -c "from src.scanner import Scanner; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```powershell
git add src/scanner.py
git commit -m "feat: Playwright-driven Scanner (login, resolve, scan_group)"
```

---

## Task 16: Scan job — background orchestration

**Files:**
- Create: `src/scan_job.py`

- [ ] **Step 1: Create `src/scan_job.py`**

```python
"""Background scan job: orchestrates Scanner + Analyzer + Translator + DB."""
import threading
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from src.scanner import Scanner, SessionExpiredError
from src.analyzer import analyze_post
from src.translator import translate_to_italian
from src.config import load_config, save_config
from src.db import init_db, insert_post, insert_scan_run, update_scan_run
from src.models import Post, ScanRun


@dataclass
class ScanState:
    status: str = "idle"
    progress_current: int = 0
    progress_total: int = 0
    current_group_name: str = ""
    posts_found: int = 0
    posts_new: int = 0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    error_message: Optional[str] = None


_state = ScanState()
_state_lock = threading.Lock()
_thread: Optional[threading.Thread] = None


def get_state() -> dict:
    with _state_lock:
        return {
            "status": _state.status,
            "progress_current": _state.progress_current,
            "progress_total": _state.progress_total,
            "current_group_name": _state.current_group_name,
            "posts_found": _state.posts_found,
            "posts_new": _state.posts_new,
            "started_at": _state.started_at.isoformat() if _state.started_at else None,
            "ended_at": _state.ended_at.isoformat() if _state.ended_at else None,
            "error_message": _state.error_message,
        }


def _set(**kwargs):
    with _state_lock:
        for k, v in kwargs.items():
            setattr(_state, k, v)


def is_running() -> bool:
    with _state_lock:
        return _state.status == "running"


def start_scan() -> bool:
    """Kick off a scan in a background thread. Returns False if one is already running."""
    global _thread
    if is_running():
        return False
    init_db()
    _set(status="running", progress_current=0, progress_total=0, current_group_name="",
         posts_found=0, posts_new=0, started_at=datetime.now(), ended_at=None, error_message=None)
    _thread = threading.Thread(target=_run, daemon=True)
    _thread.start()
    return True


def _run():
    config = load_config()
    enabled_groups = [g for g in config["groups"] if g.get("enabled", True)]
    _set(progress_total=len(enabled_groups))

    scan_run = ScanRun(started_at=_state.started_at, status="running")
    scan_run_id = insert_scan_run(scan_run)
    current_year = datetime.now().year
    posts_found = 0
    posts_new = 0

    try:
        with Scanner(delay_range=(config["scan"]["delay_min_s"], config["scan"]["delay_max_s"])) as scanner:
            for i, group in enumerate(enabled_groups, start=1):
                _set(progress_current=i, current_group_name=group.get("name", ""))

                group_id = group.get("id") or scanner.resolve_group_id(group["share_url"])
                if group_id and not group.get("id"):
                    group["id"] = group_id
                    save_config(config)
                if not group_id:
                    print(f"[scan_job] could not resolve group {group['share_url']}")
                    continue

                try:
                    for raw in scanner.scan_group(
                        group_id,
                        lookback_hours=config["scan"]["lookback_hours"],
                        max_posts=config["scan"]["max_posts_per_group"],
                    ):
                        posts_found += 1
                        analyzed = analyze_post(raw["text"], config, current_year=current_year)
                        translated = translate_to_italian(raw["text"], source_lang="lt")
                        post = Post(
                            id=raw["id"],
                            group_id=raw["group_id"],
                            url=raw["url"],
                            author_name=raw.get("author_name"),
                            posted_at=raw.get("posted_at"),
                            text_original=raw["text"],
                            text_translated=translated,
                            language="lt",
                            price_eur=analyzed.price_eur,
                            date_start=analyzed.date_start,
                            date_end=analyzed.date_end,
                            neighborhood=analyzed.neighborhood,
                            neighborhood_tier=analyzed.neighborhood_tier,
                            duration_signal=analyzed.duration_signal,
                            tier=analyzed.tier,
                            match_reasons=analyzed.match_reasons,
                            photo_urls=raw.get("photo_urls", []),
                            discovered_at=datetime.now(),
                        )
                        if insert_post(post):
                            posts_new += 1
                        _set(posts_found=posts_found, posts_new=posts_new)
                except SessionExpiredError:
                    _set(status="error", error_message="Sessione FB scaduta. Effettua nuovo login.",
                         ended_at=datetime.now())
                    update_scan_run(scan_run_id, status="error", ended_at=datetime.now(),
                                    posts_found=posts_found, posts_new=posts_new,
                                    error_message="session_expired")
                    return

        _set(status="done", ended_at=datetime.now())
        update_scan_run(scan_run_id, status="done", ended_at=datetime.now(),
                        posts_found=posts_found, posts_new=posts_new)
    except Exception as e:
        _set(status="error", ended_at=datetime.now(), error_message=str(e))
        update_scan_run(scan_run_id, status="error", ended_at=datetime.now(),
                        posts_found=posts_found, posts_new=posts_new, error_message=str(e))
```

- [ ] **Step 2: Smoke check**

Run: `python -c "from src.scan_job import start_scan, get_state, is_running; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```powershell
git add src/scan_job.py
git commit -m "feat: background scan job orchestration"
```

---

## Task 17: Flask app + routes

**Files:**
- Create: `src/app.py`

- [ ] **Step 1: Create `src/app.py`**

```python
"""Flask app: dashboard + config + scan API."""
import threading
from flask import Flask, render_template, request, jsonify

from src.config import load_config, save_config
from src.db import init_db, get_posts, mark_ignored, get_latest_scan_run
from src.scan_job import start_scan, get_state, is_running
from src.scanner import Scanner
from src.paths import get_auth_state_path


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    init_db()

    @app.route("/")
    def index():
        latest = get_latest_scan_run()
        session_present = get_auth_state_path().exists()
        return render_template("index.html",
                               latest_scan=latest,
                               session_present=session_present)

    @app.route("/api/scan", methods=["POST"])
    def api_scan():
        if start_scan():
            return jsonify({"started": True})
        return jsonify({"started": False, "reason": "already running"}), 409

    @app.route("/api/status")
    def api_status():
        return jsonify(get_state())

    @app.route("/api/posts")
    def api_posts():
        tiers = request.args.get("tiers", "S,A,B,C,D,E,over_budget").split(",")
        include_ignored = request.args.get("include_ignored") == "true"
        posts = get_posts(tiers=tiers, include_ignored=include_ignored)
        return jsonify([{
            "id": p.id,
            "group_id": p.group_id,
            "url": p.url,
            "author_name": p.author_name,
            "posted_at": p.posted_at.isoformat() if p.posted_at else None,
            "text_original": p.text_original,
            "text_translated": p.text_translated,
            "language": p.language,
            "price_eur": p.price_eur,
            "date_start": p.date_start.isoformat() if p.date_start else None,
            "date_end": p.date_end.isoformat() if p.date_end else None,
            "neighborhood": p.neighborhood,
            "neighborhood_tier": p.neighborhood_tier,
            "tier": p.tier,
            "match_reasons": p.match_reasons,
            "photo_urls": p.photo_urls,
            "is_ignored": p.is_ignored,
        } for p in posts])

    @app.route("/api/posts/<post_id>/ignore", methods=["POST"])
    def api_post_ignore(post_id):
        mark_ignored(post_id)
        return jsonify({"ok": True})

    @app.route("/config")
    def config_page():
        return render_template("config_page.html", config=load_config())

    @app.route("/api/config", methods=["GET", "POST"])
    def api_config():
        if request.method == "POST":
            save_config(request.json)
            return jsonify({"ok": True})
        return jsonify(load_config())

    @app.route("/api/login", methods=["POST"])
    def api_login():
        if is_running():
            return jsonify({"ok": False, "reason": "scan running"}), 409
        def _login():
            with Scanner() as scanner:
                scanner.interactive_login()
        t = threading.Thread(target=_login, daemon=True)
        t.start()
        return jsonify({"ok": True, "message": "Apertura browser per login..."})

    return app


if __name__ == "__main__":
    app = create_app()
    print("FB Bot Scan attivo su http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
```

- [ ] **Step 2: Smoke check Flask boots**

Run: `python -c "from src.app import create_app; app = create_app(); print(sorted([r.rule for r in app.url_map.iter_rules()]))"`
Expected: prints `['/', '/api/config', '/api/login', '/api/posts', '/api/posts/<post_id>/ignore', '/api/scan', '/api/status', '/config', '/static/<path:filename>']`

- [ ] **Step 3: Commit**

```powershell
git add src/app.py
git commit -m "feat: Flask app with scan/posts/config/login endpoints"
```

---

## Task 18: HTML templates

**Files:**
- Create: `templates/base.html`, `templates/index.html`, `templates/config_page.html`

- [ ] **Step 1: Create `templates/base.html`**

```html
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}FB Bot Scan{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
  <header class="topbar">
    <h1>🏠 FB Bot Scan — Vilnius Estate 2026</h1>
    <nav><a href="/">Dashboard</a> · <a href="/config">⚙ Config</a></nav>
  </header>
  <main>{% block content %}{% endblock %}</main>
  <script src="{{ url_for('static', filename='app.js') }}"></script>
  {% block extra_scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: Create `templates/index.html`**

```html
{% extends "base.html" %}
{% block content %}
<section class="status-bar">
  <button id="btn-scan" class="primary">🔄 Scansiona</button>
  <span id="scan-status">
    {% if latest_scan %}
      Ultimo: {{ latest_scan.started_at.strftime('%d/%m/%Y %H:%M') }}
      · <strong>{{ latest_scan.posts_new }}</strong> nuovi su {{ latest_scan.posts_found }}
    {% else %}
      Nessuna scansione ancora.
    {% endif %}
  </span>
  <span id="session-status">
    {% if session_present %}✅ Sessione attiva{% else %}⚠️ <button id="btn-login">Login a Facebook</button>{% endif %}
  </span>
</section>

<section class="filters" id="filters">
  <div>Prezzo €:
    <input type="number" id="filter-price-min" placeholder="min">
    <input type="number" id="filter-price-max" placeholder="max">
  </div>
  <div>Quartieri:
    <label><input type="checkbox" class="filter-tier-nb" value="green" checked> 🟢 Top</label>
    <label><input type="checkbox" class="filter-tier-nb" value="yellow" checked> 🟡 OK</label>
    <label><input type="checkbox" class="filter-tier-nb" value="red"> 🔴 Evitare</label>
  </div>
  <div>Tier:
    <label><input type="checkbox" class="filter-tier" value="S" checked> ⭐ S</label>
    <label><input type="checkbox" class="filter-tier" value="A" checked> ⭐ A</label>
    <label><input type="checkbox" class="filter-tier" value="B" checked> 👍 B</label>
    <label><input type="checkbox" class="filter-tier" value="C" checked> 🤷 C</label>
    <label><input type="checkbox" class="filter-tier" value="D" checked> 🟡 D</label>
    <label><input type="checkbox" class="filter-tier" value="E"> 🔴 E</label>
    <label><input type="checkbox" class="filter-tier" value="over_budget"> 💸 Over</label>
  </div>
  <div><label><input type="checkbox" id="filter-include-ignored"> Mostra ignorati</label></div>
</section>

<section class="progress" id="progress" style="display:none">
  <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
  <span id="progress-label"></span>
</section>

<section class="grid" id="results"></section>
{% endblock %}
```

- [ ] **Step 3: Create `templates/config_page.html`**

```html
{% extends "base.html" %}
{% block content %}
<section>
  <h2>Configurazione</h2>
  <p>Modifica il JSON e premi Salva. Le modifiche hanno effetto al prossimo scan.</p>
  <textarea id="config-json" rows="30" cols="100">{{ config | tojson(indent=2) }}</textarea>
  <div><button id="btn-save-config" class="primary">Salva</button> <span id="save-status"></span></div>
</section>
{% endblock %}
{% block extra_scripts %}
<script src="{{ url_for('static', filename='config.js') }}"></script>
{% endblock %}
```

- [ ] **Step 4: Commit**

```powershell
git add templates/
git commit -m "feat: HTML templates for dashboard and config"
```

---

## Task 19: CSS

**Files:**
- Create: `static/style.css`

- [ ] **Step 1: Create `static/style.css`**

```css
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; margin: 0; background: #f4f6f8; color: #222; }
.topbar { display: flex; justify-content: space-between; align-items: center; padding: 12px 24px; background: #1e293b; color: #fff; }
.topbar h1 { font-size: 18px; margin: 0; }
.topbar a { color: #cbd5e1; margin-left: 12px; text-decoration: none; }
main { padding: 16px 24px; max-width: 1400px; margin: 0 auto; }
.status-bar { background: #fff; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
button.primary { background: #2563eb; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; }
button.primary:hover { background: #1d4ed8; }
button.primary:disabled { background: #93a4c1; cursor: not-allowed; }
.filters { position: sticky; top: 0; background: #fff; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; display: flex; gap: 24px; flex-wrap: wrap; z-index: 10; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.filters label { margin-right: 8px; }
.filters input[type="number"] { width: 70px; padding: 4px 6px; border: 1px solid #d1d5db; border-radius: 4px; }
.progress { background: #fff; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px; }
.progress-bar { background: #e5e7eb; height: 8px; border-radius: 4px; overflow: hidden; margin-bottom: 4px; }
.progress-fill { background: #2563eb; height: 100%; width: 0%; transition: width 0.3s; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.card { background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: transform 0.15s; }
.card:hover { transform: translateY(-2px); }
.card .photo { width: 100%; height: 220px; object-fit: cover; background: #e5e7eb; display: block; }
.card .photo-strip { display: flex; gap: 4px; padding: 4px; background: #f4f6f8; }
.card .photo-strip img { width: 60px; height: 60px; object-fit: cover; border-radius: 4px; cursor: pointer; }
.card .body { padding: 12px; }
.tier-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 700; margin-right: 8px; }
.tier-S, .tier-A { background: #fef3c7; color: #92400e; }
.tier-B { background: #dbeafe; color: #1e40af; }
.tier-C { background: #f3f4f6; color: #4b5563; }
.tier-D { background: #fef9c3; color: #854d0e; }
.tier-E { background: #fee2e2; color: #991b1b; }
.tier-over_budget { background: #f5d0fe; color: #86198f; }
.meta { font-size: 13px; color: #475569; margin-bottom: 8px; }
.text-it { font-size: 14px; color: #1f2937; margin-bottom: 6px; white-space: pre-wrap; max-height: 200px; overflow: auto; }
.text-lt { font-size: 12px; color: #6b7280; font-style: italic; display: none; white-space: pre-wrap; max-height: 150px; overflow: auto; }
.card.show-lt .text-lt { display: block; }
.actions { display: flex; gap: 8px; margin-top: 8px; }
.actions button, .actions a { font-size: 12px; padding: 4px 10px; border-radius: 4px; text-decoration: none; border: 1px solid #d1d5db; background: #fff; color: #374151; cursor: pointer; }
.actions a.fb-link { background: #1877f2; color: #fff; border-color: #1877f2; }
textarea#config-json { width: 100%; font-family: ui-monospace, "Cascadia Code", Menlo, monospace; font-size: 13px; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; }
```

- [ ] **Step 2: Commit**

```powershell
git add static/style.css
git commit -m "feat: stylesheet"
```

---

## Task 20: Frontend JavaScript (XSS-safe DOM construction)

**Files:**
- Create: `static/app.js`, `static/config.js`

**Important:** all post data comes from Facebook posts (untrusted input). We use DOM API methods (`createElement`, `textContent`, `setAttribute`) instead of `innerHTML` for any user-supplied content. URLs are validated against an allowlist of known FB hostnames.

- [ ] **Step 1: Create `static/app.js`**

```javascript
"use strict";

const elScanBtn = document.getElementById("btn-scan");
const elResults = document.getElementById("results");
const elProgress = document.getElementById("progress");
const elProgressFill = document.getElementById("progress-fill");
const elProgressLabel = document.getElementById("progress-label");
const elScanStatus = document.getElementById("scan-status");
const elFilters = document.getElementById("filters");
const elLoginBtn = document.getElementById("btn-login");

let pollTimer = null;

const ALLOWED_HOSTS = new Set([
  "www.facebook.com",
  "facebook.com",
  "m.facebook.com",
  "mbasic.facebook.com",
  "scontent.fbcdn.net",
  "scontent.xx.fbcdn.net",
]);

function safeUrl(url) {
  if (typeof url !== "string") return null;
  try {
    const u = new URL(url);
    if (u.protocol !== "https:" && u.protocol !== "http:") return null;
    if (!ALLOWED_HOSTS.has(u.host) && !u.host.endsWith(".fbcdn.net") && !u.host.endsWith(".facebook.com")) {
      return null;
    }
    return u.toString();
  } catch {
    return null;
  }
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "dataset") for (const [dk, dv] of Object.entries(v)) node.dataset[dk] = dv;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    if (typeof c === "string") node.appendChild(document.createTextNode(c));
    else node.appendChild(c);
  }
  return node;
}

function tierEmoji(t) {
  return { S: "⭐", A: "⭐", B: "👍", C: "🤷", D: "🟡", E: "🔴", over_budget: "💸" }[t] || "·";
}

function renderCard(p) {
  const card = el("article", { class: "card", dataset: { id: p.id } });

  const photos = (p.photo_urls || []).map(safeUrl).filter(Boolean).slice(0, 4);
  if (photos[0]) {
    card.appendChild(el("img", { class: "photo", src: photos[0], alt: "", loading: "lazy" }));
  } else {
    card.appendChild(el("div", { class: "photo" }));
  }
  if (photos.length > 1) {
    const strip = el("div", { class: "photo-strip" });
    for (const u of photos.slice(1)) strip.appendChild(el("img", { src: u, alt: "", loading: "lazy" }));
    card.appendChild(strip);
  }

  const body = el("div", { class: "body" });

  const priceText = p.price_eur ? `€${p.price_eur}/mese` : "💰 prezzo non trovato";
  const badge = el("span", { class: `tier-badge tier-${p.tier}` }, `${tierEmoji(p.tier)} ${p.tier}`);
  body.appendChild(el("div", {}, badge, " ", priceText));

  const datesText = p.date_start && p.date_end
    ? `📅 ${p.date_start} → ${p.date_end}`
    : "📅 date non trovate";
  const nbText = p.neighborhood ? `📍 ${p.neighborhood}` : "📍 quartiere non riconosciuto";
  body.appendChild(el("div", { class: "meta" }, `${datesText} · ${nbText}`));

  body.appendChild(el("div", { class: "text-it" }, p.text_translated || "[traduzione non disponibile]"));
  body.appendChild(el("div", { class: "text-lt" }, p.text_original || ""));

  const actions = el("div", { class: "actions" });
  const fbUrl = safeUrl(p.url);
  if (fbUrl) {
    actions.appendChild(el("a", { class: "fb-link", href: fbUrl, target: "_blank", rel: "noopener noreferrer" }, "🔗 FB"));
  }
  const toggleBtn = el("button", {
    onclick: () => {
      card.classList.toggle("show-lt");
      toggleBtn.textContent = card.classList.contains("show-lt") ? "Nascondi LT" : "Mostra LT";
    },
  }, "Mostra LT");
  actions.appendChild(toggleBtn);

  const ignoreBtn = el("button", {
    onclick: async () => {
      await fetch(`/api/posts/${encodeURIComponent(p.id)}/ignore`, { method: "POST" });
      card.style.opacity = "0";
      setTimeout(() => card.remove(), 200);
    },
  }, "✖ Ignora");
  actions.appendChild(ignoreBtn);

  body.appendChild(actions);
  card.appendChild(body);
  return card;
}

async function refreshPosts() {
  const tiers = [...document.querySelectorAll(".filter-tier:checked")].map(el => el.value);
  const includeIgnored = document.getElementById("filter-include-ignored").checked;
  const priceMin = parseInt(document.getElementById("filter-price-min").value) || 0;
  const priceMax = parseInt(document.getElementById("filter-price-max").value) || 99999;
  const allowedNbTiers = new Set([...document.querySelectorAll(".filter-tier-nb:checked")].map(e => e.value));

  const url = `/api/posts?tiers=${encodeURIComponent(tiers.join(","))}&include_ignored=${includeIgnored}`;
  const r = await fetch(url);
  let posts = await r.json();

  posts = posts.filter(p => {
    if (p.price_eur != null && (p.price_eur < priceMin || p.price_eur > priceMax)) return false;
    if (p.neighborhood_tier && !allowedNbTiers.has(p.neighborhood_tier)) return false;
    return true;
  });

  elResults.replaceChildren(...posts.map(renderCard));
}

async function pollStatus() {
  const r = await fetch("/api/status");
  const s = await r.json();
  if (s.status === "running") {
    elProgress.style.display = "block";
    const pct = s.progress_total ? (s.progress_current / s.progress_total * 100).toFixed(0) : 0;
    elProgressFill.style.width = `${pct}%`;
    elProgressLabel.textContent = `Scansionando ${s.progress_current}/${s.progress_total}: ${s.current_group_name} — ${s.posts_new} nuovi`;
    elScanBtn.disabled = true;
  } else {
    elProgress.style.display = "none";
    elScanBtn.disabled = false;
    if (s.status === "done") {
      elScanStatus.textContent = `✅ Completato — ${s.posts_new} nuovi su ${s.posts_found}`;
      await refreshPosts();
      clearInterval(pollTimer);
      pollTimer = null;
    } else if (s.status === "error") {
      elScanStatus.textContent = `❌ Errore: ${s.error_message || "sconosciuto"}`;
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }
}

elScanBtn?.addEventListener("click", async () => {
  const r = await fetch("/api/scan", { method: "POST" });
  if (r.ok) {
    pollTimer = setInterval(pollStatus, 2000);
    pollStatus();
  }
});

elLoginBtn?.addEventListener("click", async () => {
  await fetch("/api/login", { method: "POST" });
  alert("Apri il Chrome che si è appena lanciato e fai login. La sessione si salva da sola.");
});

elFilters?.addEventListener("change", refreshPosts);

refreshPosts();
```

- [ ] **Step 2: Create `static/config.js`**

```javascript
"use strict";

document.getElementById("btn-save-config").addEventListener("click", async () => {
  const status = document.getElementById("save-status");
  let parsed;
  try {
    parsed = JSON.parse(document.getElementById("config-json").value);
  } catch (e) {
    status.textContent = "JSON non valido: " + e.message;
    return;
  }
  const r = await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsed),
  });
  status.textContent = r.ok ? "Salvato ✓" : "Errore";
});
```

- [ ] **Step 3: Smoke test the app**

Run:
```powershell
python -m src.app
```

Open `http://localhost:5000`. Expected:
- Header, "Scansiona" button, filters, empty results grid
- Open `/config` → see JSON textarea with config from `config.example.json`
- No console errors

Stop with Ctrl+C.

- [ ] **Step 4: Commit**

```powershell
git add static/app.js static/config.js
git commit -m "feat: XSS-safe DOM-based frontend"
```

---

## Task 21: First push to GitHub

- [ ] **Step 1: Verify nothing sensitive is staged**

Run:
```powershell
git ls-files | Select-String -Pattern "auth_state|config\.json$|\.db$"
```
Expected: empty output.

- [ ] **Step 2: Add remote and push**

Run:
```powershell
git remote add origin https://github.com/matas300/Playwright.git
git branch -M main
git push -u origin main
```

If git prompts for credentials, authenticate via gh / Git Credential Manager.

- [ ] **Step 3: Verify on GitHub**

Open `https://github.com/matas300/Playwright` in browser. Expected: all committed files visible, `docs/superpowers/` folder with spec + plan, no `auth_state.json` / `config.json` / `*.db`.

---

## Task 22: End-to-end manual smoke test

This task is run **on the target machine** (not the OneDrive PC), after cloning the repo fresh.

- [ ] **Step 1: Clone and bootstrap**

```powershell
git clone https://github.com/matas300/Playwright.git fb-bot-scan
cd fb-bot-scan
.\run.bat
```

Expected:
- `.venv` created, dependencies installed, chromium downloaded
- Flask logs "FB Bot Scan attivo su http://localhost:5000"

- [ ] **Step 2: First login**

Open `http://localhost:5000` in browser. Expected: "⚠️ Login a Facebook" button shown.

Click it. Expected:
- Chromium window opens at FB login page
- After completing login (including 2FA): the window closes automatically
- `%APPDATA%\fb-bot-scan\auth_state.json` exists
- Refresh dashboard: now shows "✅ Sessione attiva"

- [ ] **Step 3: Run a scan**

Click "Scansiona". Expected:
- Progress bar appears
- Chromium opens (visible) and navigates to each group in sequence, scrolling each
- Group IDs get resolved and saved into `%APPDATA%\fb-bot-scan\config.json`
- On completion: results grid populates with cards
- Each card shows: photo (if any), tier badge, price, dates, neighborhood, Italian translation
- "Mostra LT" toggles the original text
- "🔗 FB" opens the post on facebook.com
- "✖ Ignora" removes the card

- [ ] **Step 4: Verify filtering**

- Uncheck "🤷 C": C-tier cards disappear without re-scanning
- Set price max to 580: cards with higher price disappear
- Check "🔴 Evitare": red-tier neighborhoods appear if any
- Run scan again: dedup works, only new posts appear

- [ ] **Step 5: If selectors needed adjustment during smoke test**

If posts weren't extracted correctly (FB selectors changed), update `src/selectors.py`, then:

```powershell
git add src/selectors.py
git commit -m "fix(selectors): update FB DOM selectors from smoke test"
git push
```

- [ ] **Step 6: Run all unit tests as final regression check**

```powershell
pytest -v
```

Expected: all tests pass (paths: 2, config: 3, db: 8, analyzer_prices: 11, analyzer_dates: 8, analyzer_neighborhoods: 9, analyzer_duration: 14, analyzer_tier: 9, translator: 4 = 68 total).

---

## Validation criteria

After all tasks complete, the project should:
1. Boot via `run.bat` on a clean Windows machine with only Python installed
2. Save zero sensitive data to git or OneDrive (only `%APPDATA%/fb-bot-scan/`)
3. Find and classify posts from the 4 groups, with translation and tier assignment
4. Surface them in a clean dashboard ordered by relevance
5. Allow filter tweaks (budget, tier, neighborhood) without re-scanning
6. All unit tests pass (`pytest -v`)

## Out of scope (V2)

- Automatic Messenger DMs to landlords (FB ban risk too high)
- Desktop / Telegram push notifications
- LLM-based parsing fallback
- Scheduled (cron) scanning
- Multi-user
