"""verify_webhook: the signature the ORYKSA server sends (ORYKSA-Signature: t=<unix>,v1=<hex HMAC-SHA256("<t>.<raw body>")>)."""

import hashlib
import hmac
import json
import pickle
import time

import pytest

from oryksa import OryksaError, verify_webhook

SECRET = "whsec_unit_example"
BODY = json.dumps({"id": "evt_1", "type": "message.replied", "created_at": "2026-01-01T00:00:00+00:00", "data": {"text": "Olá"}},
                  ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sign(body: bytes, t: int, secret: str = SECRET) -> str:
    return "t=%d,v1=%s" % (t, hmac.new(secret.encode(), str(t).encode() + b"." + body, hashlib.sha256).hexdigest())


def test_valid_signature_bytes_or_text():
    t = int(time.time())
    ev = verify_webhook(BODY, sign(BODY, t), SECRET)
    assert ev["type"] == "message.replied"
    assert ev["data"]["text"] == "Olá"
    assert verify_webhook(BODY.decode("utf-8"), sign(BODY, t), SECRET) == ev
    assert verify_webhook(bytearray(BODY), sign(BODY, t), SECRET) == ev


def test_bad_signature():
    t = int(time.time())
    header = sign(BODY, t)
    with pytest.raises(OryksaError) as e:
        verify_webhook(BODY, header[:-1] + ("0" if header[-1] != "0" else "1"), SECRET)
    assert (e.value.status, e.value.code) == (400, "invalid_signature")
    with pytest.raises(OryksaError):
        verify_webhook(BODY + b" ", header, SECRET)
    with pytest.raises(OryksaError):
        verify_webhook(BODY, header, "whsec_other")
    with pytest.raises(OryksaError):
        verify_webhook(BODY, "t=%d,v1=café" % t, SECRET)


def test_timestamp_missing_or_too_old():
    t = int(time.time())
    for header in (None, "", "v1=abc", "t=abc,v1=abc", sign(BODY, t - 1000)):
        with pytest.raises(OryksaError) as e:
            verify_webhook(BODY, header, SECRET)
        assert e.value.code == "invalid_signature"
    assert verify_webhook(BODY, sign(BODY, t - 1000), SECRET, tolerance_seconds=2000)["id"] == "evt_1"


def test_error_is_picklable():
    e = OryksaError(402, "plan_required", "Not in the plan.", {"upgrade_url": "https://app.oryksa.com/billing"})
    back = pickle.loads(pickle.dumps(e))
    assert (back.status, back.code, back.message, back.upgrade_url) == (402, "plan_required", "Not in the plan.", "https://app.oryksa.com/billing")
