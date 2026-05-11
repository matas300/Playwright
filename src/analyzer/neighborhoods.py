"""Neighborhood detection with tier priority green > yellow > red."""
import re
import unicodedata


def normalize(s: str) -> str:
    s = s.strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _candidate_matches(text_norm: str, candidate_norm: str) -> bool:
    """Check if candidate_norm matches anywhere in text_norm.

    Tries progressively shorter stems to handle Lithuanian inflected forms
    (e.g. 'uzupis' won't match 'uzupyje' exactly, but stem 'uzup' will).
    Minimum stem length: 4 characters.
    """
    min_stem = max(4, len(candidate_norm) - 3)
    for length in range(len(candidate_norm), min_stem - 1, -1):
        stem = candidate_norm[:length]
        if re.search(rf"(?<!\w){re.escape(stem)}", text_norm):
            return True
    return False


def _pick_best_form(originals: list[str], original_text: str) -> str:
    """Among candidates with the same normalized form, pick based on original text style.

    If the original (non-normalized) text contains accented/special characters,
    prefer the accented config form (more special chars).
    If the original text is ASCII-only, prefer the ASCII config form.
    """
    text_has_specials = any(ord(c) > 127 for c in original_text)
    if text_has_specials:
        return max(originals, key=lambda o: sum(1 for c in o if ord(c) > 127))
    else:
        return min(originals, key=lambda o: sum(1 for c in o if ord(c) > 127))


def _find_match(text_norm: str, original_text: str, candidates: list[str]) -> str | None:
    """Return the first matching candidate from candidates list.

    Matching uses stem prefix to handle Lithuanian inflected forms.
    Among candidates with the same normalized form, picks the form
    best matching the text's character style (accented vs ASCII).
    Returns the first (in list order) distinct-normalized-form match.
    """
    seen_norms: set[str] = set()
    for original in candidates:
        norm = normalize(original)
        if norm in seen_norms:
            continue
        if _candidate_matches(text_norm, norm):
            # Collect all candidates with this same normalized form
            same_norm = [o for o in candidates if normalize(o) == norm]
            seen_norms.add(norm)
            return _pick_best_form(same_norm, original_text)
    return None


def extract_neighborhood(text: str, neighborhoods_cfg: dict) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    text_norm = normalize(text)
    for tier in ("green", "yellow", "red"):
        if match := _find_match(text_norm, text, neighborhoods_cfg.get(tier, [])):
            return match, tier
    return None, None
