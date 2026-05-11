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
