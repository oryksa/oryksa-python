"""The server client (secret key): every call, its path, its JSON body and its headers, like the JS SDK."""

import httpx
import pytest

from oryksa import VERSION, Oryksa, OryksaError

from conftest import SECRET


def server(rec, **kw):
    return Oryksa(SECRET, http_client=rec.client(), **kw)


def test_constructor_guards():
    with pytest.raises(ValueError, match="oryk_live_"):
        Oryksa("nope")
    with pytest.raises(ValueError, match="oryk_live_"):
        Oryksa("")
    with pytest.raises(ValueError):
        Oryksa("oryk_cs_session_token_is_not_a_key")


def test_headers_on_every_call(rec):
    o = server(rec)
    o.account()
    h = rec.req().headers
    assert rec.target() == "GET /v1/account"
    assert str(rec.req().url).startswith("https://api.oryksa.com/v1/")
    assert h["Authorization"] == "Bearer " + SECRET
    assert h["X-ORYKSA-SDK"] == "python/" + VERSION
    assert h["Accept"] == "application/json"
    assert h["User-Agent"].startswith("oryksa-python/" + VERSION)
    assert "Content-Type" not in h, "no body, no Content-Type"
    assert rec.req().content == b""


def test_chat_body_drops_missing_options(rec):
    rec.queue(200, {"object": "chat_reply", "conversation_id": "c1", "status": "replied", "reply": "Yes, 9 to 13."})
    o = server(rec)
    r = o.chat("Are you open on Saturday?")
    assert rec.target() == "POST /v1/chat"
    assert rec.req().headers["Content-Type"] == "application/json"
    assert rec.body() == {"message": "Are you open on Saturday?"}
    assert r["reply"] == "Yes, 9 to 13."
    o.chat("And Sunday?", conversation_id="c1", customer_name="Ana")
    assert rec.body() == {"message": "And Sunday?", "conversation_id": "c1", "customer_name": "Ana"}


def test_chat_pending_202_is_an_answer_not_an_error(rec):
    rec.queue(202, {"object": "chat_reply", "conversation_id": "c1", "status": "pending", "reply": None, "hint": "Read it later"})
    r = server(rec).chat("Hi")
    assert r["status"] == "pending"
    assert r["reply"] is None


def test_body_is_utf8_json(rec):
    server(rec).chat("Olá, estão abertos?")
    assert rec.req().content == '{"message":"Olá, estão abertos?"}'.encode("utf-8")


def test_conversations(rec):
    o = server(rec)
    o.conversations()
    assert rec.target() == "GET /v1/conversations"
    o.conversations(limit=5)
    assert rec.target() == "GET /v1/conversations?limit=5"
    o.conversation("user-42")
    assert rec.target() == "GET /v1/conversations/user-42"
    o.conversation("a/b c")
    assert rec.target() == "GET /v1/conversations/a%2Fb%20c"


def test_agent(rec):
    o = server(rec)
    o.agent.update({"agent_name": "Nova", "languages": ["en", "pt"]})
    assert rec.target() == "PATCH /v1/agent"
    assert rec.body() == {"agent_name": "Nova", "languages": ["en", "pt"]}
    o.agent.update(tone="friendly")
    assert rec.body() == {"tone": "friendly"}
    o.agent.appearance({"greeting": {"en": "Hi!"}}, gender="female")
    assert rec.target() == "PATCH /v1/agent/appearance"
    assert rec.body() == {"greeting": {"en": "Hi!"}, "gender": "female"}


def test_knowledge(rec):
    o = server(rec)
    o.knowledge.get()
    assert rec.target() == "GET /v1/knowledge"
    o.knowledge.set_pages([{"title": "Prices", "content": "Premium 4.99 EUR"}], site_url="https://example.com")
    assert rec.target() == "PUT /v1/knowledge/pages"
    assert rec.body() == {"pages": [{"title": "Prices", "content": "Premium 4.99 EUR"}], "site_url": "https://example.com"}
    o.knowledge.set_pages([{"content": "x"}], business_summary="A gym")
    assert rec.body() == {"pages": [{"content": "x"}], "business_summary": "A gym"}
    o.knowledge.crawl("https://example.com")
    assert rec.target() == "POST /v1/knowledge/crawl"
    assert rec.body() == {"url": "https://example.com"}
    o.knowledge.crawl("https://example.com", max_pages=10)
    assert rec.body() == {"url": "https://example.com", "max_pages": 10}
    o.knowledge.add_faq([{"question": "Parking?", "answer": "Yes, free."}])
    assert rec.target() == "POST /v1/knowledge/faq"
    assert rec.body() == {"items": [{"question": "Parking?", "answer": "Yes, free."}]}


def test_widget(rec):
    o = server(rec)
    o.widget.snippet()
    assert rec.target() == "GET /v1/widget?framework=html&lang=&position="
    o.widget.snippet(framework="react", lang="pt", position="left")
    assert rec.target() == "GET /v1/widget?framework=react&lang=pt&position=left"
    o.widget.set_domains(["example.com", "shop.example.com"])
    assert rec.target() == "PUT /v1/widget/domains"
    assert rec.body() == {"domains": ["example.com", "shop.example.com"]}
    o.widget.set_domains("example.com")
    assert rec.body() == {"domains": ["example.com"]}, "one domain as text is one domain, not its letters"


def test_webhooks(rec):
    o = server(rec)
    o.webhooks.list()
    assert rec.target() == "GET /v1/webhooks"
    o.webhooks.create("https://example.com/hook")
    assert rec.target() == "POST /v1/webhooks"
    assert rec.body() == {"url": "https://example.com/hook", "events": ["*"]}
    o.webhooks.create("https://example.com/hook", events=["message.replied", "booking.created"])
    assert rec.body() == {"url": "https://example.com/hook", "events": ["message.replied", "booking.created"]}
    o.webhooks.create("https://example.com/hook", events="limit.reached")
    assert rec.body()["events"] == ["limit.reached"]
    o.webhooks.delete("wh_example1")
    assert rec.target() == "DELETE /v1/webhooks/wh_example1"
    o.webhooks.test("wh_example1")
    assert rec.target() == "POST /v1/webhooks/wh_example1/test"
    assert rec.req().content == b"" and "Content-Type" not in rec.req().headers


def test_create_session(rec):
    rec.queue(201, {"object": "client_session", "client_token": "oryk_cs_example", "conversation_id": "user-42", "expires_at": "2026-01-01T00:00:00+00:00"})
    o = server(rec)
    s = o.create_session(conversation_id="user-42", customer_name="Ana")
    assert rec.target() == "POST /v1/sessions"
    assert rec.body() == {"conversation_id": "user-42", "customer_name": "Ana", "ttl_minutes": 60}
    assert s["client_token"] == "oryk_cs_example"
    o.create_session(customer_email="ana@example.com", customer_phone="+351 900 000 000", ttl_minutes=10)
    assert rec.body() == {"customer_email": "ana@example.com", "customer_phone": "+351 900 000 000", "ttl_minutes": 10}
    o.create_session()
    assert rec.body() == {"ttl_minutes": 60}


def test_learn_app_makes_the_same_calls_as_the_js_sdk(rec):
    rec.queue(200, {"object": "agent", "updated": ["business_name"]})
    rec.queue(200, {"object": "knowledge_pages", "pages": 4, "chars": 300})
    rec.queue(200, {"object": "knowledge_faq", "added": 1, "updated": 0})
    out = server(rec).learn_app(
        "FitTrack",
        agent_name="Nova",
        description="Fitness app to log workouts.",
        url="https://fittrack.example.com",
        languages=["en", "pt"],
        services=["Premium"],
        screens=[
            {"title": "Workouts", "content": "Tap + to log a workout."},
            {"content": "Plans are in Premium.", "url": "https://fittrack.example.com/plans"},
            {"title": "Empty"},
        ],
        settings={"units": "metric", "sync": {"health": True}, "beta": False},
        faq=[{"question": "How do I cancel?", "answer": "Settings > Subscription > Cancel."}],
    )
    assert [rec.target(i) for i in range(3)] == ["PATCH /v1/agent", "PUT /v1/knowledge/pages", "POST /v1/knowledge/faq"]
    assert rec.body(0) == {
        "business_name": "FitTrack",
        "business_description": "Fitness app to log workouts.",
        "agent_name": "Nova",
        "languages": ["en", "pt"],
        "services": ["Premium"],
    }
    assert rec.body(1) == {
        "pages": [
            {"title": "FitTrack - overview", "content": "Fitness app to log workouts."},
            {"title": "Workouts", "content": "Tap + to log a workout."},
            {"title": "Screen", "url": "https://fittrack.example.com/plans", "content": "Plans are in Premium."},
            {"title": "FitTrack - configuration", "content": 'units: metric\nsync: {"health":true}\nbeta: false'},
        ],
        "site_url": "https://fittrack.example.com",
    }
    assert rec.body(2) == {"items": [{"question": "How do I cancel?", "answer": "Settings > Subscription > Cancel."}]}
    assert out["agent"]["object"] == "agent"
    assert out["pages"]["pages"] == 4
    assert out["faq"]["added"] == 1


def test_learn_app_with_only_a_name(rec):
    out = server(rec).learn_app("FitTrack")
    assert len(rec.requests) == 1
    assert rec.body() == {"business_name": "FitTrack"}
    assert set(out) == {"agent"}
    with pytest.raises(ValueError, match="name"):
        server(rec).learn_app("")


def test_errors_carry_status_code_message_and_extra(rec):
    rec.queue(402, {"error": {"code": "interaction_limit_reached", "message": "The plan's interaction limit for this period is used up.", "upgrade_url": "https://app.oryksa.com/billing"}})
    with pytest.raises(OryksaError) as e:
        server(rec).chat("Hi")
    err = e.value
    assert (err.status, err.code) == (402, "interaction_limit_reached")
    assert err.message == str(err) == "The plan's interaction limit for this period is used up."
    assert err.upgrade_url == "https://app.oryksa.com/billing"
    assert err.extra == {"upgrade_url": "https://app.oryksa.com/billing"}

    rec.queue(429, {"error": {"code": "rate_limited", "message": "Too many requests: max 30 per 60s.", "retry_after": 60}})
    with pytest.raises(OryksaError) as e:
        server(rec).chat("Hi")
    assert e.value.retry_after == 60 and e.value.code == "rate_limited"

    rec.queue(400, {"error": {"code": "invalid_request", "message": "Send instructions, input or an image.", "param": "input"}})
    with pytest.raises(OryksaError) as e:
        server(rec).account()
    assert e.value.param == "input"


def test_error_without_json(rec):
    rec.queue(502, raw=b"<html>Bad gateway</html>")
    with pytest.raises(OryksaError) as e:
        server(rec).account()
    assert (e.value.status, e.value.code, e.value.message) == (502, "http_502", "Request failed with HTTP 502")


def test_answer_without_json_is_an_empty_dict(rec):
    rec.queue(200, raw=b"")
    assert server(rec).account() == {}


def test_network_error():
    def boom(request):
        raise httpx.ConnectError("connection refused", request=request)

    o = Oryksa(SECRET, http_client=httpx.Client(transport=httpx.MockTransport(boom)))
    with pytest.raises(OryksaError) as e:
        o.account()
    assert (e.value.status, e.value.code) == (0, "network_error")
    assert "connection refused" in e.value.message


def test_base_url_and_timeout(rec):
    seen = {}

    def answer(request):
        seen["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, json={"ok": True})

    rec.answers.append(answer)
    o = Oryksa(SECRET, base_url="http://localhost:8000/v1/", timeout=5, http_client=rec.client())
    assert o.account() == {"ok": True}
    assert str(rec.req().url) == "http://localhost:8000/v1/account"
    assert seen["timeout"]["read"] == 5


def test_close_keeps_the_http_client_you_passed(rec):
    hc = rec.client()
    with Oryksa(SECRET, http_client=hc) as o:
        o.account()
    assert not hc.is_closed
    own = Oryksa(SECRET)
    own.close()
    assert own._t._http.is_closed
