"""
SignalPreFilter — fast keyword-based relevance screen applied BEFORE any AI call.

Eliminates ~40-60% of signals with zero keyword overlap with the user's
target industries, roles, or tracked companies. These get relevance_score=0.05
and skip AI classification entirely.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PreFilterResult:
    passes: bool
    relevance_score: float
    matched_keywords: list[str] = field(default_factory=list)
    reason: str = ""


class SignalPreFilter:
    _SIGNAL_KEYWORDS: list[str] = [
        "hiring", "headcount", "expansion", "funding", "raises",
        "series a", "series b", "series c", "acqui", "merger",
        "cto", "cfo", "coo", "vp of", "head of", "director of",
        "contract", "deal", "partnership", "revenue", "growth",
    ]

    def __init__(
        self,
        target_industries: list[str],
        target_roles: list[str],
        tracked_companies: list[str],
    ) -> None:
        self._keywords: list[str] = self._build_keyword_list(
            target_industries, target_roles, tracked_companies
        )

    def screen(self, title: str, description: str, company_name: str) -> PreFilterResult:
        if not self._keywords:
            return PreFilterResult(
                passes=False,
                relevance_score=0.05,
                reason="No profile keywords configured",
            )

        haystack = f"{title} {description} {company_name}".lower()
        matched = [kw for kw in self._keywords if kw.lower() in haystack]

        if matched:
            return PreFilterResult(
                passes=True,
                relevance_score=0.5,
                matched_keywords=matched,
                reason=f"Matched: {', '.join(matched[:3])}",
            )

        return PreFilterResult(
            passes=False,
            relevance_score=0.05,
            matched_keywords=[],
            reason="No keyword overlap with user profile",
        )

    def _build_keyword_list(
        self,
        industries: list[str],
        roles: list[str],
        companies: list[str],
    ) -> list[str]:
        user_keywords = industries + roles + companies
        # If user has no profile configured, return empty list so the guard
        # in screen() fires and passes=False for every signal.
        if not user_keywords:
            return []
        expanded: list[str] = []
        for kw in user_keywords:
            expanded.append(kw)
            parts = kw.split()
            if len(parts) > 1:
                expanded.extend(parts)
        return list(set(expanded + self._SIGNAL_KEYWORDS))
