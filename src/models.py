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
