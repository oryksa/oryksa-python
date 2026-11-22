"""The app client (session token): chat, attachments, token refresh, link previews, send_and_wait."""

import base64

import pytest

from oryksa import Oryksa, OryksaClient, OryksaError, VERSION

from conftest import SECRET, TOKEN


def app(rec, **kw):
    kw.setdefault("token", TOKEN)
    return OryksaClient(http_client=rec.client(), **kw)


def test_constructor_guards():
    with pytest.raises(ValueError, match="token"):
        OryksaClient()
    with pytest.raises(ValueError, match="secret API key"):
        OryksaClient(token=SECRET)
    with pytest.raises(ValueError, match="secret API key"):
        OryksaClient(SECRET)


def test_agent_messages_and_headers(rec):
    rec.queue(200, {"object": "agent", "name": "Nova", "avatar": "https://example.com/a.png", "conversation_id": "user-42"})
    rec.queue(200, {"object": "conversation", "id": "user-42", "messages": [{"role": "user", "content": "Hi"}]})
    c = app(rec)
    assert c.agent()["name"] == "Nova"
    assert rec.target() == "GET /v1/client/agent"
    assert rec.req().headers["Authorization"] == "Bearer " + TOKEN
    assert rec.req().headers["X-ORYKSA-SDK"] == "python/" + VERSION
    assert c.messages()["messages"][0]["content"] == "Hi"
    assert rec.target() == "GET /v1/client/messages"


def test_send_bodies_with_and_without_attachments(rec):
    rec.queue(200, {"status": "replied", "reply": "Recebi o documento."})
    c = app(rec)
    pdf = base64.b64encode(b"%PDF-1.4 example quote").decode()
    r = c.send("Veja o orçamento", file={"base64": pdf, "name": "orcamento.pdf", "mime": "application/pdf"})
    assert r["reply"] == "Recebi o documento."
    assert rec.target() == "POST /v1/client/chat"
    assert rec.body() == {"message": "Veja o orçamento", "file_base64": pdf, "file_name": "orcamento.pdf", "file_mime": "application/pdf"}
    c.send("", image={"base64": "/9j/AAA=", "mime": "image/jpeg"})
    assert rec.body() == {"message": "", "image_base64": "/9j/AAA=", "image_mime": "image/jpeg"}
    c.send("Olá")
    assert rec.body() == {"message": "Olá"}, "no attachment, no attachment fields"
    c.send("photo", image={"base64": "AQID"})
    assert rec.body() == {"message": "photo", "image_base64": "AQID", "image_mime": "image/jpeg"}
    c.send("doc", file={"base64": "AQID"})
    assert rec.body() == {"message": "doc", "file_base64": "AQID", "file_name": "file", "file_mime": "application/octet-stream"}
    c.send("empty photo", image={"base64": ""})
    assert rec.body() == {"message": "empty photo"}


def test_get_token_is_asked_when_needed_and_again_when_the_token_expires(rec):
    tokens = iter(["oryk_cs_first", "oryk_cs_second"])
    asked = []

    def get_token():
        t = next(tokens)
        asked.append(t)
        return t

    rec.queue(200, {"name": "Nova"})
    rec.queue(401, {"error": {"code": "session_expired", "message": "This client token expired. Ask your server for a new one."}})
    rec.queue(200, {"name": "Nova"})
    c = app(rec, token=None, get_token=get_token)
    c.agent()
    assert asked == ["oryk_cs_first"]
    assert rec.req(0).headers["Authorization"] == "Bearer oryk_cs_first"
    assert c.agent()["name"] == "Nova"
    assert asked == ["oryk_cs_first", "oryk_cs_second"]
    assert rec.req(1).headers["Authorization"] == "Bearer oryk_cs_first"
    assert rec.req(2).headers["Authorization"] == "Bearer oryk_cs_second"
    assert rec.target(2) == "GET /v1/client/agent"


def test_without_get_token_an_expired_token_is_an_error(rec):
    rec.queue(401, {"error": {"code": "session_expired", "message": "expired"}})
    with pytest.raises(OryksaError) as e:
        app(rec).agent()
    assert e.value.code == "session_expired"
    assert len(rec.requests) == 1


def test_other_errors_are_not_retried(rec):
    rec.queue(402, {"error": {"code": "interaction_limit_reached", "message": "used up"}})
    with pytest.raises(OryksaError) as e:
        app(rec, get_token=lambda: "oryk_cs_new").send("Hi")
    assert e.value.status == 402
    assert len(rec.requests) == 1


def test_get_token_guards(rec):
    with pytest.raises(OryksaError) as e:
        app(rec, token=None, get_token=lambda: "").agent()
    assert e.value.code == "no_token"
    assert rec.requests == []
    with pytest.raises(ValueError, match="secret API key"):
        app(rec, token=None, get_token=lambda: SECRET).agent()

    async def later():
        return "oryk_cs_x"

    with pytest.raises(TypeError, match="AsyncOryksaClient"):
        app(rec, token=None, get_token=later).agent()


def test_send_and_wait_reads_the_conversation_until_the_reply_lands(rec):
    rec.queue(202, {"object": "chat_reply", "conversation_id": "user-42", "status": "pending", "reply": None})
    rec.queue(200, {"messages": [{"role": "user", "content": "Is there a 5K plan?"}]})
    rec.queue(200, {"messages": [{"role": "user", "content": "Is there a 5K plan?"}, {"role": "assistant", "content": "Yes, 6 weeks."}]})
    r = app(rec).send_and_wait("Is there a 5K plan?", poll_interval=0)
    assert r == {"object": "chat_reply", "conversation_id": "user-42", "status": "replied", "reply": "Yes, 6 weeks."}
    assert [rec.target(i) for i in range(3)] == ["POST /v1/client/chat", "GET /v1/client/messages", "GET /v1/client/messages"]


def test_send_and_wait_returns_at_once_when_replied_and_pending_after_max_wait(rec):
    rec.queue(200, {"status": "replied", "reply": "Hello!"})
    assert app(rec).send_and_wait("Hi")["reply"] == "Hello!"
    assert len(rec.requests) == 1
    rec.queue(202, {"status": "pending", "reply": None})
    r = app(rec).send_and_wait("Hi", max_wait=0)
    assert r["status"] == "pending"


def test_link_preview_one_request_kept_in_memory_none_on_failure(rec):
    page = "https://shop.example.com/products/blue-shoes"
    rec.queue(200, {"object": "link_preview", "url": page, "title": "Blue shoes", "image": "", "site": "shop.example.com", "price": None})
    c = app(rec)
    p = c.link_preview(page)
    assert p == {"object": "link_preview", "url": page, "title": "Blue shoes", "image": "", "site": "shop.example.com", "price": ""}
    assert rec.target() == "GET /v1/client/link-preview?url=https%3A%2F%2Fshop.example.com%2Fproducts%2Fblue-shoes"
    assert rec.req().headers["Authorization"] == "Bearer " + TOKEN
    assert c.link_preview(page) == p
    assert len(rec.requests) == 1, "kept in memory"
    c.link_preview("https://shop.example.com/p?id=5&c=a+b#top")
    assert rec.target().endswith("?url=https%3A%2F%2Fshop.example.com%2Fp%3Fid%3D5%26c%3Da%2Bb%23top"), "the whole address goes in the query"
    rec.queue(500, {"error": {"code": "boom", "message": "no"}})
    assert c.link_preview("https://shop.example.com/other") is None, "a failed preview is None, never an error"


def test_link_preview_values_are_text(rec):
    rec.queue(200, {"url": "https://shop.example.com/a", "title": "A", "price": 12.0, "site": None})
    p = app(rec).link_preview("https://shop.example.com/a")
    assert p["price"] == "12" and p["site"] == "" and p["image"] == ""


def test_server_session_then_app_client(rec):
    """The flow of the README: the server creates the session, the app only gets the token."""
    rec.queue(201, {"client_token": TOKEN, "conversation_id": "user-42"})
    rec.queue(200, {"status": "replied", "reply": "Hi Ana!"})
    s = Oryksa(SECRET, http_client=rec.client()).create_session(conversation_id="user-42", customer_name="Ana")
    c = OryksaClient(token=s["client_token"], http_client=rec.client())
    assert c.send("Hello")["reply"] == "Hi Ana!"
    assert rec.req(0).headers["Authorization"] == "Bearer " + SECRET
    assert rec.req(1).headers["Authorization"] == "Bearer " + TOKEN
