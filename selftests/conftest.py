"""
Shared pytest fixtures + import path setup for the toolkit's regression suite.

These self-tests exercise the pipeline package directly and must run whether or
not the package is pip-installed, so we add `src/` to sys.path as a fallback.
Everything here is standard-library + pytest only: the suite never needs the
external GenLayer toolchain (genvm-lint / gltest / genlayer), so it runs in a
bare CI job in seconds.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def clean_env(monkeypatch):
    """Strip every GENLAYER_* / pipeline env var so a test starts from a known,
    empty environment and can set exactly the vars it wants to assert on."""
    import os

    for key in list(os.environ):
        if key.startswith("GENLAYER_") or key.startswith("PIPELINE_"):
            monkeypatch.delenv(key, raising=False)
    return monkeypatch
