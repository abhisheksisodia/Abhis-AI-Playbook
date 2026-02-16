"""Dataclasses that implement the system data contracts."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ScoreBreakdown:
    audience_fit: float
    practicality: float
    originality: float
    freshness: float
    brand_safety: float

    def total(self) -> float:
        return (
            self.audience_fit
            + self.practicality
            + self.originality
            + self.freshness
            + self.brand_safety
        )


@dataclass
class ItemPayload:
    """Represents a discovered and scored content item."""

    id: str
    title: str
    url: str
    source: str
    author: Optional[str]
    type: str  # youtube|blog|manual
    published_at: Optional[datetime]
    discovered_at: datetime
    raw_text: str
    score: float = 0.0
    score_breakdown: Optional[ScoreBreakdown] = None
    rationale: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        payload = asdict(self)
        if self.published_at:
            payload["published_at"] = self.published_at.strftime("%Y-%m-%d")
        if self.discovered_at:
            payload["discovered_at"] = self.discovered_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        return payload


@dataclass
class TimestampHighlight:
    time: str
    description: str


@dataclass
class SocialCopy:
    tweet: str
    linkedin: str


@dataclass
class SeoMetadata:
    title: str
    meta_description: str


@dataclass
class SummaryPayload:
    item_id: str
    title: str
    url: str
    tldr: str
    why_it_matters: str
    bullets: List[str]
    risks: List[str]
    quote_or_metric: str
    timestamps: List[TimestampHighlight] = field(default_factory=list)
    social: Optional[SocialCopy] = None
    seo: Optional[SeoMetadata] = None
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        payload = asdict(self)
        payload["generated_at"] = self.generated_at.strftime("%Y-%m-%d %H:%M:%S")
        return payload


@dataclass
class PlaybookTip:
    title: str
    description: str
    checklist: List[str]


@dataclass
class CTA:
    text: str
    subscribe_url: str
    consulting_url: str


@dataclass
class NewsletterDraft:
    issue_number: int
    issue_date: datetime
    hook: str
    top_picks: List[SummaryPayload]
    quick_hits: List[Dict[str, str]]
    playbook_tip: PlaybookTip
    cta: CTA
    metadata: Dict[str, int]

    def to_dict(self) -> Dict:
        payload = {
            "issue_number": self.issue_number,
            "issue_date": self.issue_date.strftime("%Y-%m-%d"),
            "hook": self.hook,
            "top_picks": [summary.to_dict() for summary in self.top_picks],
            "quick_hits": self.quick_hits,
            "playbook_tip": asdict(self.playbook_tip),
            "cta": asdict(self.cta),
            "metadata": self.metadata,
        }
        return payload
