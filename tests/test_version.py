"""The X-ORYKSA-SDK header must report the real package version: fail if the code drifts from pyproject.toml."""

import re
from pathlib import Path

import oryksa
from oryksa import _http


def test_version_matches_pyproject():
    text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version = "([^"]+)"', text, re.M)
    assert m, "pyproject.toml has a version"
    assert oryksa.VERSION == oryksa.__version__ == m.group(1)
    assert _http.SDK_HEADER == "python/" + m.group(1)


def test_public_names():
    for name in oryksa.__all__:
        assert hasattr(oryksa, name), name
