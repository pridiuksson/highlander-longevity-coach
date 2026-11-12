"""Pure library wrapper for the proactive-coach insight ledger."""
from __future__ import annotations

import contextlib
import io
from typing import Optional

from . import _ledger_impl as _mod


def _capture(fn, *a, **kw) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*a, **kw)
    return buf.getvalue().strip()


def add(source: str, cls: str, headline: str, dedup_key: Optional[str] = None) -> str:
    return _capture(_mod.cmd_add, source, cls, headline, dedup_key)


def resolve(entry_id: str, outcome: str) -> str:
    return _capture(_mod.cmd_resolve, entry_id, outcome)


def report(as_json: bool = False) -> str:
    return _capture(_mod.cmd_report, as_json)


def reflect(as_json: bool = False) -> str:
    return _capture(_mod.cmd_reflect, as_json)


def pending() -> str:
    return _capture(_mod.cmd_pending)


def ledger_path() -> str:
    if hasattr(_mod, "_ledger_path"):
        return _mod._ledger_path()
    return _mod.LEDGER