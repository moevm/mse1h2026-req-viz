from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class NodeCreate(BaseModel):
    label: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Node label (e.g. Technology, Company)",
    )
    name: str = Field(
        ..., min_length=1, max_length=500, description="Human-readable name"
    )
    description: str | None = Field(default=None, max_length=5000)
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Key-value properties"
    )
    source: str | None = Field(
        default=None,
        max_length=200,
        description="Data source (e.g. wikidata, stackoverflow)",
    )

    @field_validator("label")
    @classmethod
    def label_must_be_pascal_case(cls, v: str) -> str:
        if not v[0].isupper():
            msg = f"Label must start with uppercase letter, got '{v}'"
            raise ValueError(msg)
        return v


class NodeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    properties: dict[str, Any] | None = Field(
        default=None, description="Merged with existing properties"
    )
    source: str | None = None


class NodeResponse(BaseModel):
    uid: str
    label: str
    name: str
    description: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None
    created_at: datetime
    updated_at: datetime


class RelationshipCreate(BaseModel):
    source_uid: str = Field(..., min_length=1, description="Source node uid")
    target_uid: str = Field(..., min_length=1, description="Target node uid")
    rel_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Relationship type (e.g. USED_WITH)",
    )
    weight: float = Field(default=1.0, ge=0.0, description="Relationship weight")
    properties: dict[str, Any] = Field(default_factory=dict)
    source: str | None = Field(default=None, max_length=200)

    @field_validator("rel_type")
    @classmethod
    def rel_type_must_be_upper_snake(cls, v: str) -> str:
        if v != v.upper():
            msg = f"Relationship type must be UPPER_SNAKE_CASE, got '{v}'"
            raise ValueError(msg)
        if " " in v:
            msg = f"Relationship type must not contain spaces, got '{v}'"
            raise ValueError(msg)
        return v


class RelationshipUpdate(BaseModel):
    weight: float | None = Field(default=None, ge=0.0)
    properties: dict[str, Any] | None = None
    source: str | None = None


class RelationshipResponse(BaseModel):
    source_uid: str
    target_uid: str
    rel_type: str
    weight: float
    properties: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None
    created_at: datetime
    updated_at: datetime


class NodeFilter(BaseModel):
    labels: list[str] | None = Field(
        default=None, description="Filter by one or more labels"
    )
    name_contains: str | None = Field(
        default=None, description="Substring search in name (case-insensitive)"
    )
    properties_match: dict[str, Any] | None = Field(
        default=None, description="Exact match on property keys"
    )
    source: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    limit: int = Field(default=100, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


class RelationshipFilter(BaseModel):
    rel_types: list[str] | None = Field(
        default=None, description="Filter by relationship types"
    )
    weight_min: float | None = Field(default=None, ge=0.0)
    weight_max: float | None = Field(default=None, ge=0.0)
    source: str | None = None
    limit: int = Field(default=100, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


class SubgraphFilter(BaseModel):
    node_filter: NodeFilter | None = None
    rel_filter: RelationshipFilter | None = None
    center_uid: str | None = Field(
        default=None, description="Center node uid for neighborhood extraction"
    )
    depth: int = Field(
        default=1, ge=1, le=10, description="Traversal depth from center node"
    )
    limit: int = Field(default=100, ge=1, le=10000, description="Max nodes in response")


class SubgraphResponse(BaseModel):
    nodes: list[NodeResponse] = Field(default_factory=list)
    relationships: list[RelationshipResponse] = Field(default_factory=list)
    total_nodes: int = 0
    total_relationships: int = 0
