"""ORM model package — import every model so Alembic autogenerate sees them."""

from app.models.base import (
    ACHIEVEMENT_KINDS,
    BOARD_ITEM_TYPES,
    DOMAIN_SOURCES,
    LEARNING_ITEM_KINDS,
    LEARNING_ITEM_STATUSES,
    REVIEW_PERIOD_TYPES,
    TASK_CONTEXTS,
    TASK_ORIGINS,
    TASK_STATUSES,
    TIME_ENTRY_KINDS,
    Base,
    utcnow,
)
from app.models.learning import LearningItem, LearningLog, LearningUnit
from app.models.review import Achievement, AchievementTask, Review
from app.models.system import AIRun, NotificationLog, Setting
from app.models.task import BoardItem, Domain, Task, TaskDomain, TaskNote
from app.models.timing import DailyJournal, TimeEntry

__all__ = [
    "ACHIEVEMENT_KINDS",
    "BOARD_ITEM_TYPES",
    "DOMAIN_SOURCES",
    "LEARNING_ITEM_KINDS",
    "LEARNING_ITEM_STATUSES",
    "REVIEW_PERIOD_TYPES",
    "TASK_CONTEXTS",
    "TASK_ORIGINS",
    "TASK_STATUSES",
    "TIME_ENTRY_KINDS",
    "AIRun",
    "Achievement",
    "AchievementTask",
    "Base",
    "BoardItem",
    "DailyJournal",
    "Domain",
    "LearningItem",
    "LearningLog",
    "LearningUnit",
    "NotificationLog",
    "Review",
    "Setting",
    "Task",
    "TaskDomain",
    "TaskNote",
    "TimeEntry",
    "utcnow",
]
