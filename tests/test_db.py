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
