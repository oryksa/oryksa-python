"""Check the signature of an ORYKSA webhook (header ``ORYKSA-Signature: t=<unix seconds>,v1=<hex HMAC-SHA256>``)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional, Union, cast

from .errors import OryksaError

RawBody = Union[bytes, bytearray, memoryview, str]


def _parts(header: Optional[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in str(header or "").split(","):
        k, _, v = p.partition("=")
        out[k.strip()] = v.strip()
    return out


def verify_webhook(raw_body: RawBody, signature_header: Optional[str], secret: str, *, tolerance_seconds: float = 300) -> Dict[str, Any]:
    """Verify an ORYKSA webhook and return the event (``{id, type, created_at, data}``).

    Pass the RAW request body (the bytes as received, before any JSON parsing), the
    ``ORYKSA-Signature`` header and the webhook ``secret`` (whsec_...). Raises
    ``OryksaError(400, "invalid_signature")`` when the timestamp is missing or older than
    ``tolerance_seconds``, or when the signature does not match.
    """
    parts = _parts(signature_header)
    try:
        t = int(parts.get("t") or 0)
    except ValueError:
        t = 0
    if not t or abs(time.time() - t) > tolerance_seconds:
        raise OryksaError(400, "invalid_signature", "Webhook timestamp is missing or too old.")
    body = raw_body.encode("utf-8") if isinstance(raw_body, str) else bytes(raw_body)
    expected = hmac.new(str(secret).encode("utf-8"), str(t).encode("ascii") + b"." + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected.encode("ascii"), parts.get("v1", "").encode("utf-8")):
        raise OryksaError(400, "invalid_signature", "Webhook signature does not match.")
    return cast(Dict[str, Any], json.loads(body))
