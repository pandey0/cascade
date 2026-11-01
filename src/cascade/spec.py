"""Decision specification (YAML) validated with pydantic."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class Example(BaseModel):
    input: str
    label: str


class TeacherConfig(BaseModel):
    provider: str = Field(description="Provider key; resolved by an adapter, not by this module")
    model: str = Field(description="Exact model id; record it, model names change")
    prompt_version: str = "v1"


class Target(BaseModel):
    agreement: float = Field(gt=0.0, lt=1.0, description="Minimum agreement with the teacher")
    delta: float = Field(
        default=0.1, gt=0.0, lt=1.0, description="Failure probability of the bound"
    )


class Budget(BaseModel):
    max_teacher_usd: float | None = Field(default=None, gt=0.0)


class DecisionSpec(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    description: str = ""
    labels: list[str] = Field(min_length=2)
    examples: list[Example] = Field(default_factory=list)
    teacher: TeacherConfig
    target: Target
    budget: Budget = Field(default_factory=Budget)
    shadow_mode: bool = True

    @field_validator("labels")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            msg = "labels must be unique"
            raise ValueError(msg)
        return v

    def model_post_init(self, __context: object) -> None:
        unknown = {e.label for e in self.examples} - set(self.labels)
        if unknown:
            msg = f"examples use labels not in spec: {sorted(unknown)}"
            raise ValueError(msg)

    @property
    def risk_alpha(self) -> float:
        """Risk (disagreement) target implied by the agreement target."""
        return 1.0 - self.target.agreement


def load_spec(path: str | Path) -> DecisionSpec:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return DecisionSpec.model_validate(data)
