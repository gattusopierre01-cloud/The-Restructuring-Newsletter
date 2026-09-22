"""Shared plumbing for the collectors.

A collector's only job is to turn a source into a list of Candidates. It does
no summarising and makes no editorial choice — select.py ranks, draft.py
writes. Keeping them apart means a source can be swapped without touching the
drafting, and a collector can be run on its own to see what it found.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

# The SEC asks for a descriptive User-Agent with a contact address, and other
# public services are happier with one too.
USER_AGENT = (
    "The Restructuring Brief/0.1 "
    "(+https://github.com/gattusopierre01-cloud/The-Restructuring-Newsletter)"
)


@dataclass
class Candidate:
    """One thing that might make it into an issue."""

    source_id: str
    kind: str  # "case" | "filing" | "statistic"
    jurisdiction: str
    title: str
    url: str
    date: dt.date | None = None
    court: str = ""
    citation: str = ""
    summary: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        data = dataclasses.asdict(self)
        data["date"] = self.date.isoformat() if self.date else None
        return data


class CollectorError(RuntimeError):
    """A source could not be read. One failure must not lose the whole issue."""


def fetch(url: str, *, accept: str = "application/json", timeout: int = 30) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": accept}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise CollectorError(f"{url} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise CollectorError(f"{url} could not be reached: {exc.reason}") from exc


def fetch_json(url: str, **kwargs) -> Any:
    raw = fetch(url, **kwargs)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CollectorError(f"{url} did not return JSON") from exc


def window(days: int, *, today: dt.date | None = None) -> tuple[dt.date, dt.date]:
    """The lookback window, slightly overlapping so nothing slips between issues."""
    end = today or dt.date.today()
    return end - dt.timedelta(days=days), end
