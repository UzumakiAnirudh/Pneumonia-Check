from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HistoryItem(BaseModel):
    id: str
    created_at: datetime
    source_name: Optional[str] = None
    models: list[str]
    final_label: str
    confidence: float
    thumbnail: str
    is_mock: bool
    agree: Optional[bool] = None
