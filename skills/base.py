from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class SkillResult(BaseModel):
    skill: str
    data: dict
    source: str
    source_url: str = ""   # actual page URL — shown as tappable link to user
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ok: bool = True
    error: str | None = None

    @classmethod
    def failure(cls, skill: str, source: str, error: str) -> "SkillResult":
        return cls(skill=skill, data={}, source=source, ok=False, error=error)


class Skill(ABC):
    name: str
    description: str

    @abstractmethod
    async def run(self, query: str) -> SkillResult: ...


_registry: dict[str, "Skill"] = {}


def register(skill: Skill) -> None:
    _registry[skill.name] = skill


def all_skills() -> list[Skill]:
    return list(_registry.values())


def get_skill(name: str) -> Skill | None:
    return _registry.get(name)
