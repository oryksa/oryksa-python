"""ai(): the AI doing what your app needs, counted as ORYKSA interactions (POST /v1/client/ai)."""

import pytest

from oryksa import AiResult, OryksaClient, OryksaError, ai_body, ai_result

from conftest import TOKEN

ANSWER = {
    "object": "ai_result",
    "text": '{"size":"205/55 R16 91V"}',
    "json": {"size": "205/55 R16 91V"},
    "oryksa": {"interactions_spent": 1, "interactions_remaining": 99},
}


def test_ai_sends_instructions_photos_and_schema_and_reads_the_json(rec):
    rec.queue(200, ANSWER)
    c = OryksaClient(token=TOKEN, http_client=rec.client())
    r = c.ai(instructions="Read the tyre size. Never invent.", images=[{"base64": "AQID"}], schema={"type": "object"})
    assert rec.target() == "POST /v1/client/ai"
    assert rec.req().headers["Authorization"] == "Bearer " + TOKEN
    assert rec.body() == {
        "platform": "python",
        "instructions": "Read the tyre size. Never invent.",
        "images": [{"base64": "AQID", "mime": "image/jpeg"}],
        "schema": {"type": "object"},
    }
    assert "message" not in rec.body()
    assert isinstance(r, AiResult)
    assert r.json == {"size": "205/55 R16 91V"}
    assert r.text == '{"size":"205/55 R16 91V"}'
    assert r.interactions_spent == 1
    assert r.interactions_remaining == 99


def test_ai_body_all_options():
    b = ai_body(
        instructions="Classify the review.",
        input="Great service!",
        images=[{"base64": "AQ", "mime": "image/png"}, {"base64": "Ag"}],
        schema={},
        max_tokens=200,
        temperature=0,
    )
    assert b == {
        "platform": "python",
        "instructions": "Classify the review.",
        "input": "Great service!",
        "images": [{"base64": "AQ", "mime": "image/png"}, {"base64": "Ag", "mime": "image/jpeg"}],
        "schema": {},
        "max_tokens": 200,
        "temperature": 0,
    }
    assert ai_body(input="Translate: good morning") == {"platform": "python", "input": "Translate: good morning"}


def test_ai_body_guards():
    with pytest.raises(ValueError, match="needs"):
        ai_body()
    with pytest.raises(ValueError, match="needs"):
        ai_body(instructions="", input="")
    p = {"base64": "AQ"}
    with pytest.raises(ValueError, match="at most 4"):
        ai_body(input="x", images=[p, p, p, p, p])
    assert len(ai_body(images=[p, p, p, p])["images"]) == 4
    with pytest.raises(TypeError):
        ai_body(images={"base64": "AQ"})
    with pytest.raises(TypeError):
        ai_body(images=["AQ"])


def test_ai_guards_send_nothing(rec):
    c = OryksaClient(token=TOKEN, http_client=rec.client())
    with pytest.raises(ValueError):
        c.ai()
    assert rec.requests == []


def test_ai_result_reading():
    t = ai_result({"object": "ai_result", "text": "Lisboa.", "json": None, "oryksa": {"interactions_spent": 1}})
    assert t == AiResult(text="Lisboa.", json=None, interactions_spent=1, interactions_remaining=None)
    assert ai_result(None) == AiResult(text="", json=None, interactions_spent=0, interactions_remaining=None)
    assert ai_result({"json": [1, 2], "oryksa": {"interactions_remaining": 0}}).json == [1, 2]
    assert ai_result({"json": [1, 2], "oryksa": {"interactions_remaining": 0}}).interactions_remaining == 0
    assert ai_result({"json": "not an object"}).json is None


def test_ai_used_up_is_402(rec):
    rec.queue(402, {"error": {"code": "interaction_limit_reached", "message": "used up", "upgrade_url": "https://app.oryksa.com/billing"}})
    with pytest.raises(OryksaError) as e:
        OryksaClient(token=TOKEN, http_client=rec.client()).ai(input="Hi")
    assert e.value.status == 402
    assert e.value.code == "interaction_limit_reached"
