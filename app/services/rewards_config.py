"""The configuration of the reward engine.

Every number of the rewards lives in ``config/rewards.yaml``. The file is
read into a Pydantic model, so a wrong number is refused with a clear
message instead of breaking the app in the middle of a muster. The user
may change the numbers in the settings page; the defaults of the file can
always be restored.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
REWARDS_FILE = CONFIG_DIR / "rewards.yaml"

TIERS = ("bronze", "silver", "gold")
VIRTUES = ("prowess", "valor", "wisdom", "loyalty", "largesse", "temperance")


class EvidenceRule(BaseModel):
    """What a tier needs to be earned."""

    model_config = ConfigDict(extra="forbid")

    tasks: int = Field(ge=0)
    impact_note: bool = False
    concrete: bool = False


class CountingRules(BaseModel):
    """The cap and the diminishing returns of a month."""

    model_config = ConfigDict(extra="forbid")

    monthly_cap: int = Field(ge=0)
    diminishing_factor: float = Field(ge=0.0, le=1.0)


class TemperanceRules(BaseModel):
    """The medal of temperance."""

    model_config = ConfigDict(extra="forbid")

    overtime_minutes_threshold: int = Field(ge=0)
    weeks_with_target_met: int = Field(ge=0)


class VictoryRules(BaseModel):
    """The medal of victory."""

    model_config = ConfigDict(extra="forbid")

    completion_rate_gain: float = Field(ge=0)
    lead_time_drop: float = Field(ge=0)
    min_comparable_tasks: int = Field(ge=0)


class TitleRule(BaseModel):
    """The gates of a title."""

    model_config = ConfigDict(extra="forbid")

    key: str
    degrees: int = Field(ge=0)
    musters: int | None = None
    silver: int | None = None
    gold: int | None = None
    virtues: int | None = None
    virtues_must_include: list[str] = Field(default_factory=list)
    fiefs: int | None = None
    vigil: bool = False

    @field_validator("virtues_must_include")
    @classmethod
    def _known_virtues(cls, value: list[str]) -> list[str]:
        unknown = [name for name in value if name not in VIRTUES]
        if unknown:
            raise ValueError(f"unknown virtues: {', '.join(unknown)}")
        return value


class FiefRules(BaseModel):
    """When a domain becomes a fief."""

    model_config = ConfigDict(extra="forbid")

    medals_per_fief: int = Field(ge=1)


class EndgameRules(BaseModel):
    """The last title of the game."""

    model_config = ConfigDict(extra="forbid")

    realms: int = Field(ge=0)
    title: str


class OrderRule(BaseModel):
    """What an order needs to be given."""

    model_config = ConfigDict(extra="forbid")

    journal_days: int | None = Field(default=None, ge=0)
    learning_items: int | None = Field(default=None, ge=0)
    quarterly_musters: int | None = Field(default=None, ge=0)


class QuestRules(BaseModel):
    """The optional quests of a month."""

    model_config = ConfigDict(extra="forbid")

    per_month_min: int = Field(ge=0)
    per_month_max: int = Field(ge=0)
    medal_tier: str

    @field_validator("medal_tier")
    @classmethod
    def _known_tier(cls, value: str) -> str:
        if value not in TIERS:
            raise ValueError(f"unknown tier: {value}")
        return value


class RewardsConfig(BaseModel):
    """The whole configuration of the reward engine."""

    model_config = ConfigDict(extra="forbid")

    medal_tiers: dict[str, int]
    evidence: dict[str, EvidenceRule]
    virtues: list[str]
    degree_size: int = Field(ge=1)
    counting: CountingRules
    temperance: TemperanceRules
    victory: VictoryRules
    titles: list[TitleRule]
    fiefs: FiefRules
    endgame: EndgameRules
    orders: dict[str, OrderRule]
    quests: QuestRules

    @field_validator("medal_tiers")
    @classmethod
    def _known_tiers(cls, value: dict[str, int]) -> dict[str, int]:
        unknown = [name for name in value if name not in TIERS]
        if unknown:
            raise ValueError(f"unknown tiers: {', '.join(unknown)}")
        return value

    @field_validator("virtues")
    @classmethod
    def _known_virtue_list(cls, value: list[str]) -> list[str]:
        unknown = [name for name in value if name not in VIRTUES]
        if unknown:
            raise ValueError(f"unknown virtues: {', '.join(unknown)}")
        return value

    @field_validator("evidence")
    @classmethod
    def _rules_for_every_tier(cls, value: dict[str, EvidenceRule]) -> dict[str, EvidenceRule]:
        missing = [name for name in TIERS if name not in value]
        if missing:
            raise ValueError(f"the rules of these tiers are missing: {', '.join(missing)}")
        return value

    @field_validator("titles")
    @classmethod
    def _titles_ascending(cls, value: list[TitleRule]) -> list[TitleRule]:
        degrees = [rule.degrees for rule in value]
        if degrees != sorted(degrees):
            raise ValueError("the titles must go from the lowest to the highest")
        return value

    def tier_value(self, tier: str) -> int:
        """The value of a tier before the cap."""
        return self.medal_tiers[tier]

    def rule(self, tier: str) -> EvidenceRule:
        """The evidence a tier needs."""
        return self.evidence[tier]

    def title(self, key: str) -> TitleRule:
        """The rule of a title."""
        for rule in self.titles:
            if rule.key == key:
                return rule
        raise KeyError(key)


class ConfigError(RuntimeError):
    """The configuration of the rewards could not be read."""


def load_config(path: Path | None = None) -> RewardsConfig:
    """Read the configuration of the rewards and validate it.

    The file is read every time: the user may change it in the settings
    page, and a mistake must be reported, not hidden.
    """
    source = path or REWARDS_FILE
    try:
        raw = source.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(f"the rewards file could not be read: {error}") from error
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        raise ConfigError(f"the rewards file is not valid YAML: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError("the rewards file must hold a mapping")
    try:
        return RewardsConfig.model_validate(data)
    except ValidationError as error:
        raise ConfigError(f"the rewards file is not valid: {error}") from error


def default_config() -> RewardsConfig:
    """The configuration of the file, without any change of the user."""
    return load_config()


def merged_config(overrides: dict[str, Any] | None) -> RewardsConfig:
    """The configuration of the file with the changes of the user.

    The overrides are a partial document: a key that is not given keeps
    the value of the file. A wrong override is refused like a wrong file.
    """
    base = load_config().model_dump()
    if not overrides:
        return RewardsConfig.model_validate(base)
    merged = _deep_merge(base, overrides)
    try:
        return RewardsConfig.model_validate(merged)
    except ValidationError as error:
        raise ConfigError(f"the settings of the rewards are not valid: {error}") from error


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge two documents, the override winning."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result
