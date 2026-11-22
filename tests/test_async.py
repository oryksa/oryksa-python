"""The async clients: the same calls, awaited (asyncio.run, no test plugin needed)."""

import asyncio

import httpx
import pytest

from oryksa import AsyncOryksa, AsyncOryksaClient, OryksaError, VERSION

from conftest import SECRET, TOKEN


def run(coro):
    return asyncio.run(coro)


def test_async_server_calls(rec):
    async def main():
        rec.queue(200, {"object": "chat_reply", "status": "replied", "reply": "Yes."})
        rec.queue(201, {"client_token": TOKEN, "conversation_id": "user-42"})
        async with AsyncOryksa(SECRET, http_client=rec.async_client()) as o:
            r = await o.chat("Open on Saturday?", conversation_id="c1")
            s = await o.create_session(conversation_id="user-42")
            await o.account()
            await o.conversations(limit=3)
            await o.conversation("c1")
            await o.agent.update({"agent_name": "Nova"})
            await o.agent.appearance(gender="male")
            await o.knowledge.get()
            await o.knowledge.set_pages([{"content": "x"}])
            await o.knowledge.crawl("https://example.com", max_pages=2)
            await o.knowledge.add_faq([{"question": "q", "answer": "a"}])
            await o.widget.snippet(framework="vue")
            await o.widget.set_domains(["example.com"])
            await o.webhooks.list()
            await o.webhooks.create("https://example.com/hook")
            await o.webhooks.delete("wh_1")
            await o.webhooks.test("wh_1")
        return r, s

    r, s = run(main())
    assert r["reply"] == "Yes."
    assert s["client_token"] == TOKEN
    assert [rec.target(i) for i in range(len(rec.requests))] == [
        "POST /v1/chat",
        "POST /v1/sessions",
        "GET /v1/account",
        "GET /v1/conversations?limit=3",
        "GET /v1/conversations/c1",
        "PATCH /v1/agent",
        "PATCH /v1/agent/appearance",
        "GET /v1/knowledge",
        "PUT /v1/knowledge/pages",
        "POST /v1/knowledge/crawl",
        "POST /v1/knowledge/faq",
        "GET /v1/widget?framework=vue&lang=&position=",
        "PUT /v1/widget/domains",
        "GET /v1/webhooks",
        "POST /v1/webhooks",
        "DELETE /v1/webhooks/wh_1",
        "POST /v1/webhooks/wh_1/test",
    ]
    assert rec.body(0) == {"message": "Open on Saturday?", "conversation_id": "c1"}
    assert rec.body(1) == {"conversation_id": "user-42", "ttl_minutes": 60}
    assert rec.req(0).headers["Authorization"] == "Bearer " + SECRET
    assert rec.req(0).headers["X-ORYKSA-SDK"] == "python/" + VERSION


def test_async_learn_app(rec):
    async def main():
        o = AsyncOryksa(SECRET, http_client=rec.async_client())
        return await o.learn_app("FitTrack", description="Fitness app.", faq=[{"question": "q", "answer": "a"}])

    out = run(main())
    assert [rec.target(i) for i in range(3)] == ["PATCH /v1/agent", "PUT /v1/knowledge/pages", "POST /v1/knowledge/faq"]
    assert set(out) == {"agent", "pages", "faq"}


def test_async_client_ai_send_and_link_preview(rec):
    async def main():
        rec.queue(200, {"object": "ai_result", "text": "Bom dia", "json": None, "oryksa": {"interactions_spent": 1, "interactions_remaining": 41}})
        rec.queue(200, {"status": "replied", "reply": "Got the photo."})
        rec.queue(200, {"url": "https://shop.example.com/a", "title": "A"})
        async with AsyncOryksaClient(token=TOKEN, http_client=rec.async_client()) as c:
            r = await c.ai(instructions="Translate to Portuguese.", input="Good morning")
            s = await c.send("Look", image={"base64": "AQID", "mime": "image/png"})
            p1 = await c.link_preview("https://shop.example.com/a")
            p2 = await c.link_preview("https://shop.example.com/a")
            await c.agent()
            await c.messages()
        return r, s, p1, p2

    r, s, p1, p2 = run(main())
    assert (r.text, r.interactions_spent, r.interactions_remaining) == ("Bom dia", 1, 41)
    assert rec.body(0) == {"platform": "python", "instructions": "Translate to Portuguese.", "input": "Good morning"}
    assert s["reply"] == "Got the photo."
    assert rec.body(1) == {"message": "Look", "image_base64": "AQID", "image_mime": "image/png"}
    assert p1 == p2 and p1["title"] == "A"
    assert [rec.target(i) for i in range(len(rec.requests))] == [
        "POST /v1/client/ai",
        "POST /v1/client/chat",
        "GET /v1/client/link-preview?url=https%3A%2F%2Fshop.example.com%2Fa",
        "GET /v1/client/agent",
        "GET /v1/client/messages",
    ]


def test_async_get_token_sync_or_async_and_refresh(rec):
    tokens = iter(["oryk_cs_first", "oryk_cs_second"])

    async def get_token():
        await asyncio.sleep(0)
        return next(tokens)

    async def main():
        rec.queue(401, {"error": {"code": "session_expired", "message": "expired"}})
        rec.queue(200, {"name": "Nova"})
        c = AsyncOryksaClient(get_token=get_token, http_client=rec.async_client())
        a = await c.agent()
        c2 = AsyncOryksaClient(get_token=lambda: "oryk_cs_sync", http_client=rec.async_client())
        await c2.messages()
        return a

    assert run(main())["name"] == "Nova"
    assert [r.headers["Authorization"] for r in rec.requests] == ["Bearer oryk_cs_first", "Bearer oryk_cs_second", "Bearer oryk_cs_sync"]


def test_async_send_and_wait(rec):
    async def main():
        rec.queue(202, {"conversation_id": "c1", "status": "pending", "reply": None})
        rec.queue(200, {"messages": [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]})
        c = AsyncOryksaClient(token=TOKEN, http_client=rec.async_client())
        return await c.send_and_wait("Hi", poll_interval=0)

    assert run(main()) == {"object": "chat_reply", "conversation_id": "c1", "status": "replied", "reply": "Hello!"}


def test_async_errors():
    def boom(request):
        raise httpx.ReadTimeout("", request=request)

    async def main():
        c = AsyncOryksaClient(token=TOKEN, http_client=httpx.AsyncClient(transport=httpx.MockTransport(boom)))
        with pytest.raises(OryksaError) as e:
            await c.agent()
        assert (e.value.status, e.value.code) == (0, "network_error")
        assert "ReadTimeout" in e.value.message
        assert await c.link_preview("https://shop.example.com/a") is None
        with pytest.raises(ValueError):
            await c.ai()

    run(main())
    with pytest.raises(ValueError):
        AsyncOryksa("nope")
    with pytest.raises(ValueError):
        AsyncOryksaClient(token=SECRET)
