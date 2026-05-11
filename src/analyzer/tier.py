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
