"""Schemas for the task domain."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TaskStatus = Literal["todo", "doing", "done", "cancelled"]
TaskOrigin = Literal["self_initiated", "assigned"]
TaskContext = Literal["company", "personal", "learning"]


class TaskCreate(BaseModel):
    """Payload used to create a task."""

    title: str = Field(min_length=1, max_length=500)
    description_md: str = ""
    status: TaskStatus = "todo"
    priority: int = Field(default=2, ge=0, le=4)
    origin: TaskOrigin = "self_initiated"
    assigned_by: str | None = None
    context: TaskContext = "personal"
    due_at: datetime | None = None
    effort_minutes_estimate: int | None = Field(default=None, ge=0)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title_required")
        return cleaned


class TaskUpdate(BaseModel):
    """Partial update of a task."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description_md: str | None = None
    status: TaskStatus | None = None
    priority: int | None = Field(default=None, ge=0, le=4)
    origin: TaskOrigin | None = None
    assigned_by: str | None = None
    context: TaskContext | None = None
    due_at: datetime | None = None
    effort_minutes_estimate: int | None = Field(default=None, ge=0)


class TaskOut(BaseModel):
    """Serialised task."""

    model_config = {"from_attributes": True}

    id: int
    title: str
    description_md: str
    status: str
    priority: int
    origin: str
    assigned_by: str | None
    context: str
    due_at: datetime | None
    effort_minutes_estimate: int | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    last_activity_at: datetime | None
    deleted_at: datetime | None
