"""Uniform error payloads: ``{"detail": {"code": ..., "message": ..., ...}}``."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, UploadFile


def api_error(status: int, code: str, message: str, **extra: Any) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message, **extra})


async def read_upload(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload fully into memory (never to disk), enforcing a size limit."""
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > max_bytes:
            raise api_error(
                413,
                "file_too_large",
                f"File exceeds the {max_bytes // (1024 * 1024)} MB limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)
