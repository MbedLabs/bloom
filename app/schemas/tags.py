"""Schemas for the tag base and the tags an artefact carries."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_serializer


class TagCreate(BaseModel):
    """A new tag of the base."""

    name: str = Field(..., min_length=1, max_length=80)


class TagUpdate(BaseModel):
    """A tag's new name."""

    name: str = Field(..., min_length=1, max_length=80)


class TagResponse(BaseModel):
    """One tag of the base."""

    id: int
    name: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z" if dt else None

    model_config = {"from_attributes": True}


class TagScopeResponse(BaseModel):
    """Whether the user's policies choose tags on a project, and the tags they may give."""

    limited: bool
    tags: List[TagResponse]


class ArtefactTagsUpdate(BaseModel):
    """The full set of tags an artefact carries after the change."""

    tag_ids: List[int] = Field(default_factory=list)
