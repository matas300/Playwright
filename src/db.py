"""SQLite storage layer."""
import json
import sqlite3
from datetime import datetime, date
from typing import Optional, Iterable

from src.paths import get_db_path
from src.models import Post, ScanRun

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
