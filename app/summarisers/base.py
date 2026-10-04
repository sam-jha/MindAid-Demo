"""The ONE interface every summariser follows: summarise(entries) -> structured summary.

The summary is a plain dict with these fields:
  narrative, themes (list), mood_pattern, concerning_content (list of {excerpt, note}),
  priority {level, reason}, suggested_session_focus, uncertainty_note, generated_by
priority.level is one of: urgent | notable | routine | unassessed
"""
from typing import Protocol

from app.models import Entry

PRIORITY_LEVELS = ("urgent", "notable", "routine", "unassessed")


class Summariser(Protocol):
    def summarise(self, entries: list[Entry]) -> dict: ...


class SummariserError(Exception):
    """A summary couldn't be produced. The message is safe to show to the psychologist."""


class SummaryBlocked(SummariserError):
    """The AI service's content filter refused to produce a summary. The psychologist must read the entries."""
