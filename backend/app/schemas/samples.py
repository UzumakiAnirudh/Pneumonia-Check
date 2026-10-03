from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SampleImage(BaseModel):
    id: str
    label: Literal["NORMAL", "BACTERIAL", "VIRAL"]
    title: str
    description: str
    url: str
    synthetic: bool = False
