"""Per-account analysis history in SQLite (SQLModel).

Every record belongs to one user; every query is scoped by ``user_id`` so an account can never
read or delete another account's analyses (unknown or foreign IDs both return "not found").

Privacy: only a small thumbnail (192 px JPEG), the results and a timestamp are stored.
Full-resolution images and blended overlays are never persisted; heatmaps are stored at
thumbnail size so a result can be reopened.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from sqlalchemy import Engine
from sqlmodel import Field, Session, SQLModel, delete, select

from app.schemas.history import HistoryItem
from app.schemas.prediction import PredictResponse
from app.services.preprocessing import encode_jpeg_data_uri, encode_png_data_uri

THUMB_SIDE = 192


class AnalysisRecord(SQLModel, table=True):
    __tablename__ = "analyses"

    id: str = Field(primary_key=True)
    user_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(index=True)
    source_name: Optional[str] = None
    models: str
    final_label: str
    confidence: float
    is_mock: bool = False
    agree: Optional[bool] = None
    thumbnail: str
    payload: str


def _decode_data_uri(uri: str, flags: int = cv2.IMREAD_UNCHANGED) -> np.ndarray:
    raw = base64.b64decode(uri.split(",", 1)[1])
    return cv2.imdecode(np.frombuffer(raw, np.uint8), flags)


def _shrink(arr: np.ndarray, side: int = THUMB_SIDE) -> np.ndarray:
    h, w = arr.shape[:2]
    scale = min(1.0, side / max(h, w))
    return cv2.resize(
        arr,
        (max(1, round(w * scale)), max(1, round(h * scale))),
        interpolation=cv2.INTER_AREA,
    )


def compact_response(resp: PredictResponse) -> tuple[str, PredictResponse]:
    """Return (thumbnail data URI, response with thumbnail-sized images and no overlays)."""
    gray = _decode_data_uri(resp.image_png, cv2.IMREAD_GRAYSCALE)
    thumb = encode_jpeg_data_uri(_shrink(gray), quality=80)
    results = []
    for r in resp.results:
        if r.explanation is not None:
            heat = cv2.cvtColor(
                _decode_data_uri(r.explanation.heatmap_png, cv2.IMREAD_COLOR),
                cv2.COLOR_BGR2RGB,
            )
            th, tw = _shrink(gray).shape[:2]
            heat_small = cv2.resize(heat, (tw, th), interpolation=cv2.INTER_AREA)
            r = r.model_copy(
                update={
                    "explanation": r.explanation.model_copy(
                        update={
                            "heatmap_png": encode_png_data_uri(heat_small),
                            "overlay_png": None,
                        }
                    )
                }
            )
        results.append(r)
    return thumb, resp.model_copy(update={"image_png": thumb, "results": results})


class HistoryRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def add(self, resp: PredictResponse, user_id: str) -> None:
        thumb, compact = compact_response(resp)
        first = compact.results[0]
        record = AnalysisRecord(
            id=resp.id,
            user_id=user_id,
            created_at=resp.created_at,
            source_name=resp.source_name,
            models=",".join(r.model for r in compact.results),
            final_label=first.final_label,
            confidence=first.final_confidence,
            is_mock=resp.is_mock,
            agree=resp.agreement.agree if resp.agreement else None,
            thumbnail=thumb,
            payload=compact.model_dump_json(),
        )
        with Session(self.engine) as session:
            session.add(record)
            session.commit()

    def list(self, user_id: str, limit: int = 200) -> list[HistoryItem]:
        with Session(self.engine) as session:
            rows = session.exec(
                select(AnalysisRecord)
                .where(AnalysisRecord.user_id == user_id)
                .order_by(AnalysisRecord.created_at.desc())  # type: ignore[union-attr]
                .limit(limit)
            ).all()
        return [
            HistoryItem(
                id=r.id,
                created_at=r.created_at,
                source_name=r.source_name,
                models=r.models.split(","),
                final_label=r.final_label,
                confidence=r.confidence,
                thumbnail=r.thumbnail,
                is_mock=r.is_mock,
                agree=r.agree,
            )
            for r in rows
        ]

    def _owned(self, session: Session, item_id: str, user_id: str) -> AnalysisRecord | None:
        row = session.get(AnalysisRecord, item_id)
        return row if row is not None and row.user_id == user_id else None

    def get(self, item_id: str, user_id: str) -> PredictResponse | None:
        with Session(self.engine) as session:
            row = self._owned(session, item_id, user_id)
        if row is None:
            return None
        return PredictResponse.model_validate(json.loads(row.payload))

    def delete(self, item_id: str, user_id: str) -> bool:
        with Session(self.engine) as session:
            row = self._owned(session, item_id, user_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    def clear(self, user_id: str) -> int:
        with Session(self.engine) as session:
            result = session.exec(delete(AnalysisRecord).where(AnalysisRecord.user_id == user_id))  # type: ignore[call-overload]
            session.commit()
            return int(result.rowcount or 0)
