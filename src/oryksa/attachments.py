"""Photos and documents for the chat: the same limits and types as the ORYKSA chats in every app.

A photo goes up to 2 MB (the AI looks at it), a document up to 8 MB (PDF, Word, text, CSV; the AI reads it).
"""

from __future__ import annotations

import base64
import math
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict, Mapping, NamedTuple, Optional, Union

#: The largest photo the chat sends (after it is made smaller): 2 MB.
MAX_PHOTO_BYTES = 2 * 1024 * 1024
#: The largest document the chat sends: 8 MB.
MAX_FILE_BYTES = 8 * 1024 * 1024

_OCTET = "application/octet-stream"
_DOC_MIME = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "csv": "text/csv",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}
_EXT = re.compile(r"\.([^./\\]+)$")
_SPACE = re.compile(r"\s+")


class Size(NamedTuple):
    width: int
    height: int


def _ext(name: Any) -> str:
    m = _EXT.search(str(name or ""))
    return m.group(1).lower() if m else ""


def mime_of(name: str) -> str:
    """The type of a file from its name (``application/octet-stream`` when it is not a known one)."""
    return _DOC_MIME.get(_ext(name), _OCTET)


def base64_bytes(b64: str) -> int:
    """How many bytes a base64 text holds."""
    s = _SPACE.sub("", str(b64 or ""))
    pad = 2 if s.endswith("==") else 1 if s.endswith("=") else 0
    return max(0, (len(s) * 3) // 4 - pad)


def _round(x: float) -> int:
    return int(math.floor(x + 0.5))


def scaled_size(width: float, height: float, max_side: float = 1600) -> Size:
    """The size of a photo of width x height pixels with its longest side at most max_side (never larger)."""
    if not (width > 0 and height > 0):
        return Size(0, 0)
    k = min(1.0, max_side / max(width, height))
    return Size(max(1, _round(width * k)), max(1, _round(height * k)))


def photo_attachment(p: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """A photo ``{base64, mime}`` as what the chat sends: ``{"image": {...}}`` or ``{"error": "big" | "failed"}``."""
    if not p or not isinstance(p.get("base64"), str) or not p.get("base64"):
        return {"error": "failed"}
    if base64_bytes(p["base64"]) > MAX_PHOTO_BYTES:
        return {"error": "big"}
    return {"image": {"base64": p["base64"], "mime": p.get("mime") or "image/jpeg"}}


def document_attachment(d: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """A document ``{base64, name, mime}`` (or ``{too_big: True}``) as what the chat sends: pictures up to
    2 MB as ``{"image": ...}`` (the AI looks at it), the rest as ``{"file": ...}`` up to 8 MB, else
    ``{"error": "big" | "failed"}``. The result goes straight into ``client.send(text, **result)``.
    """
    if not d:
        return {"error": "failed"}
    if d.get("too_big"):
        return {"error": "big"}
    if not isinstance(d.get("base64"), str):
        return {"error": "failed"}
    size = base64_bytes(d["base64"])
    if size > MAX_FILE_BYTES:
        return {"error": "big"}
    name = d.get("name") or "file"
    mime = _DOC_MIME.get(_ext(name)) or d.get("mime") or _OCTET
    if mime.startswith("image/") and size <= MAX_PHOTO_BYTES:
        return {"image": {"base64": d["base64"], "mime": mime}}
    return {"file": {"base64": d["base64"], "name": name, "mime": mime}}


def document_from_path(path: Union[str, "os.PathLike[str]"]) -> Dict[str, Any]:
    """A file on disk as ``{base64, name, mime}``, or ``{too_big: True, name}`` above 8 MB (without reading it)."""
    p = Path(path)
    name = p.name
    if p.stat().st_size > MAX_FILE_BYTES:
        return {"too_big": True, "name": name}
    mime = mime_of(name)
    if mime == _OCTET:
        mime = mimetypes.guess_type(name)[0] or _OCTET
    return {"base64": base64.b64encode(p.read_bytes()).decode("ascii"), "name": name, "mime": mime}


__all__ = [
    "MAX_PHOTO_BYTES", "MAX_FILE_BYTES", "Size", "mime_of", "base64_bytes", "scaled_size",
    "photo_attachment", "document_attachment", "document_from_path",
]
