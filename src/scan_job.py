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
