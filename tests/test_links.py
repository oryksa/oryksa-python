"""The links of the AI's replies, offline: the same rules as the JS SDK (test/links.test.js)."""

from oryksa import LinkPart, link_parts, links_in, without_links

FIRST = "https://shop.example.com/services/landing-page-focused-on-conversions"
SECOND = "https://shop.example.com/services/explore/28"
REPLY = (
    "Yes, I found some web designers for your landing page. You can check this "
    "professional landing page service focused on conversions:\n" + FIRST + "\n"
    "If you want more options, here is the list: " + SECOND + "."
)


def test_links_in_order_without_the_final_dot():
    assert links_in(REPLY) == [FIRST, SECOND]
    assert links_in("a https://x.example/a, b https://x.example/a! c https://y.example/b; d https://z.example/c? e https://w.example/d") == [
        "https://x.example/a",
        "https://y.example/b",
        "https://z.example/c",
    ]
    assert links_in('(see https://x.example/a) or "https://y.example/b"…') == ["https://x.example/a", "https://y.example/b"]
    assert links_in("no links here, write to info@example.com") == []
    assert links_in(REPLY) == [FIRST, SECOND], "the same answer twice (no state kept between calls)"
    assert links_in(REPLY, max=1) == [FIRST]
    assert links_in(None) == []


def test_without_links():
    t = without_links(REPLY)
    assert "http" not in t
    assert "conversions:" not in t
    assert "focused on conversions" in t
    assert not t.endswith(":")
    assert without_links("See https://x.example/a .") == "See."


def test_link_parts_web_and_email():
    text = "Snowboard at " + FIRST + ". Mail info@example.com or " + SECOND + "."
    parts = link_parts(text)
    assert "".join(p.text for p in parts) == text
    assert [(p.text, p.url) for p in parts if p.url] == [
        (FIRST, FIRST),
        ("info@example.com", "mailto:info@example.com"),
        (SECOND, SECOND),
    ]
    assert parts[0] == LinkPart("Snowboard at ", None)
    assert link_parts("") == []
    assert link_parts("plain") == [LinkPart("plain", None)]


def test_an_email_inside_a_link_is_part_of_the_link():
    u = "https://example.com/contact?to=info@example.com"
    assert [(p.text, p.url) for p in link_parts("Write: " + u) if p.url] == [(u, u)]
