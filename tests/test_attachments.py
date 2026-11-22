"""Attachments, offline: the same limits and types as the JS SDK (test/attach.test.js)."""

import base64

from oryksa import (
    MAX_FILE_BYTES,
    MAX_PHOTO_BYTES,
    base64_bytes,
    document_attachment,
    document_from_path,
    mime_of,
    photo_attachment,
    scaled_size,
)


def b64(n):
    return base64.b64encode(bytes([7]) * n).decode()


def test_limits():
    assert MAX_PHOTO_BYTES == 2 * 1024 * 1024
    assert MAX_FILE_BYTES == 8 * 1024 * 1024
    for n in (0, 1, 2, 3, 4, 1000, 1001, 1002):
        assert base64_bytes(b64(n)) == n
    assert base64_bytes("AQID\nBAU=") == 5, "line breaks do not count"


def test_photo_attachment():
    assert photo_attachment({"base64": b64(MAX_PHOTO_BYTES + 1), "mime": "image/jpeg"}) == {"error": "big"}
    assert photo_attachment({"base64": b64(10)}) == {"image": {"base64": b64(10), "mime": "image/jpeg"}}
    assert photo_attachment(None) == {"error": "failed"}
    assert photo_attachment({"base64": ""}) == {"error": "failed"}


def test_document_attachment():
    assert document_attachment({"base64": b64(MAX_FILE_BYTES + 1), "name": "big.pdf"}) == {"error": "big"}
    assert document_attachment({"too_big": True, "name": "big.pdf"}) == {"error": "big"}
    ok8 = document_attachment({"base64": b64(MAX_FILE_BYTES), "name": "Contrato.PDF"})
    assert ok8["file"]["mime"] == "application/pdf"
    assert ok8["file"]["name"] == "Contrato.PDF"
    assert document_attachment(None) == {"error": "failed"}
    assert document_attachment({"name": "x.pdf"}) == {"error": "failed"}


def test_a_picture_from_the_document_picker():
    assert document_attachment({"base64": b64(1000), "name": "foto.png"}) == {"image": {"base64": b64(1000), "mime": "image/png"}}
    assert document_attachment({"base64": b64(MAX_PHOTO_BYTES + 1), "name": "foto.png"})["file"]["mime"] == "image/png"
    assert document_attachment({"base64": "", "name": "notas", "mime": "text/markdown"})["file"]["mime"] == "text/markdown"


def test_mime_of():
    assert mime_of("a.doc") == "application/msword"
    assert mime_of("a.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert mime_of("lista.TXT") == "text/plain"
    assert mime_of("a.csv") == "text/csv"
    assert mime_of("a.zip") == "application/octet-stream"
    assert mime_of("no-extension") == "application/octet-stream"


def test_scaled_size():
    assert scaled_size(3200, 2000) == (1600, 1000)
    assert scaled_size(2000, 3200) == (1000, 1600)
    assert scaled_size(800, 600) == (800, 600)
    assert scaled_size(0, 600) == (0, 0)
    s = scaled_size(4000, 3000, max_side=1000)
    assert (s.width, s.height) == (1000, 750)
    assert scaled_size(3, 1, max_side=2) == (2, 1), "rounds half up, like Math.round"


def test_document_from_path(tmp_path):
    pdf = tmp_path / "quote.pdf"
    pdf.write_bytes(b"%PDF-1.4 example")
    d = document_from_path(pdf)
    assert d == {"base64": base64.b64encode(b"%PDF-1.4 example").decode(), "name": "quote.pdf", "mime": "application/pdf"}
    assert document_attachment(d) == {"file": d}
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"\xff\xd8\xff example")
    assert "image" in document_attachment(document_from_path(str(photo)))
    big = tmp_path / "big.pdf"
    with open(big, "wb") as f:
        f.truncate(MAX_FILE_BYTES + 1)
    assert document_from_path(big) == {"too_big": True, "name": "big.pdf"}, "too large: not even read"
    assert document_attachment(document_from_path(big)) == {"error": "big"}
