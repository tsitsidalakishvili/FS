from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Entity:
    label: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class Relationship:
    source_label: str
    source_id: str
    rel_type: str
    target_label: str
    target_id: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestionBatch:
    source: str
    entities: list[Entity]
    relationships: list[Relationship]
