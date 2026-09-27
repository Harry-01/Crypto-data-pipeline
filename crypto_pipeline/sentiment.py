"""Lightweight rule-based sentiment scoring (VADER), tuned for short social/news text."""

from __future__ import annotations

from functools import lru_cache

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05


@lru_cache(maxsize=1)
def _analyzer() -> SentimentIntensityAnalyzer:
    return SentimentIntensityAnalyzer()


def score(text: str | None) -> float | None:
    """VADER compound score in [-1, 1]; None for empty text."""
    if not text or not text.strip():
        return None
    return round(_analyzer().polarity_scores(text)["compound"], 4)


def label(compound: float | None) -> str | None:
    if compound is None:
        return None
    if compound >= POSITIVE_THRESHOLD:
        return "positive"
    if compound <= NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"
