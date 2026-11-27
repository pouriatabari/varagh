"""The strict schemas every AI answer must satisfy."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.base import TASK_CONTEXTS, TASK_ORIGINS


class StrictModel(BaseModel):
    """A model that refuses unknown fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class QuickAddDraft(StrictModel):
    """What the AI understood of a quick-add string."""

    title: str = Field(min_length=1, max_length=500)
    due_at: datetime | None = None
    priority: int = 2
    context: str = "personal"
    origin: str = "self_initiated"
    assigned_by: str | None = None
    effort_minutes_estimate: int | None = Field(default=None, ge=0, le=100000)
    note_md: str = ""

    @field_validator("priority")
    @classmethod
    def _check_priority(cls, value: int) -> int:
        """The priority must be between 0 and 3."""
        if value not in (0, 1, 2, 3):
            raise ValueError(f"unknown priority: {value}")
        return value

    @field_validator("context")
    @classmethod
    def _check_context(cls, value: str) -> str:
        """The context must be one of the known contexts."""
        if value not in TASK_CONTEXTS:
            raise ValueError(f"unknown context: {value}")
        return value

    @field_validator("origin")
    @classmethod
    def _check_origin(cls, value: str) -> str:
        """The origin must be one of the known origins."""
        if value not in TASK_ORIGINS:
            raise ValueError(f"unknown origin: {value}")
        return value


class JournalEntryDraft(StrictModel):
    """One entry proposed out of a free-text journal."""

    text: str = Field(min_length=1, max_length=1000)
    minutes: int | None = Field(default=None, ge=0, le=1440)
    kind: str = "work"
    task_id: int | None = None


class JournalProposal(StrictModel):
    """What the AI proposes to write into the journal."""

    entries: list[JournalEntryDraft] = Field(default_factory=list)
    summary_fa: str = ""


class ClassificationDraft(StrictModel):
    """The domains the AI suggests for a task."""

    domains: list[str] = Field(default_factory=list, max_length=3)


class SyllabusDraft(StrictModel):
    """The units the AI found in a syllabus."""

    units: list[str] = Field(default_factory=list)


class PlanItem(StrictModel):
    """One item of the plan of the day."""

    title: str = Field(min_length=1, max_length=300)
    task_id: int | None = None
    minutes: int | None = Field(default=None, ge=0, le=1440)
    note_fa: str = ""


class ChartSpec(StrictModel):
    """A chart the model asks for.

    The model names a series of the payload; the labels and the values are
    resolved by the server, so no figure can be invented.
    """

    type: Literal["bar", "line", "doughnut", "pie"] = "bar"
    series: str = Field(min_length=1, max_length=100)
    title_fa: str = Field(default="", max_length=200)
    basis: Literal["measured", "estimated", "elapsed"] = "measured"


class DailyPlanDraft(StrictModel):
    """The plan the AI proposes for today."""

    plan: list[PlanItem] = Field(default_factory=list)
    summary_fa: str = ""
    charts: list[ChartSpec] = Field(default_factory=list, max_length=6)


class AchievementDraft(StrictModel):
    """One achievement proposed by the AI, grounded in tasks.

    The proposal also carries what the reward engine needs: the virtue it
    belongs to, the domain of the craft, the tier it asks for and whether
    the impact is concrete. The server checks all of it again and lowers
    the tier when the evidence does not prove it.
    """

    title: str = Field(min_length=1, max_length=500)
    description_fa: str = ""
    task_ids: list[int] = Field(default_factory=list)
    impact_fa: str = ""
    virtue: str = "prowess"
    domain: str = ""
    suggested_tier: str = "bronze"
    concrete: bool = False
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ReviewDraft(StrictModel):
    """The draft of a review."""

    achievements_technical: list[AchievementDraft] = Field(default_factory=list)
    achievements_work: list[AchievementDraft] = Field(default_factory=list)
    comparison: str = ""
    bottlenecks: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    narrative_fa: str = ""
    charts: list[ChartSpec] = Field(default_factory=list, max_length=6)


class AnswerDraft(StrictModel):
    """The answer of the «ask my data» feature."""

    answer_fa: str = Field(min_length=1)
    used_task_ids: list[int] = Field(default_factory=list)
    used_dates: list[str] = Field(default_factory=list)
    charts: list[ChartSpec] = Field(default_factory=list, max_length=6)


class RealmSuggestionDraft(StrictModel):
    """The realm the AI suggests for a domain.

    Only the key of a realm that was offered may be answered; the server
    checks it again before the realm is written.
    """

    realm_key: str = Field(min_length=1, max_length=40)
    reason_fa: str = Field(default="", max_length=300)
