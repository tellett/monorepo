from __future__ import annotations

import pathlib
from typing import Annotated, Literal, Union

import yaml
from pydantic import BaseModel, Field


class LinearSettings(BaseModel):
    api_key: str
    sync_interval_minutes: int = 60


class AssignedSource(BaseModel):
    type: Literal["assigned"] = "assigned"
    output_file: str = "assigned.org"


class TeamSource(BaseModel):
    type: Literal["team"]
    slug: str
    output_file: str


class ProjectSource(BaseModel):
    type: Literal["project"]
    id: str
    output_file: str


Source = Annotated[
    Union[AssignedSource, TeamSource, ProjectSource],
    Field(discriminator="type"),
]


class Config(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    linear: LinearSettings
    sources: list[Source]
    config_dir: pathlib.Path


def load_config(path: pathlib.Path) -> Config:
    raw = yaml.safe_load(path.read_text())
    return Config(config_dir=path.parent, **raw)
