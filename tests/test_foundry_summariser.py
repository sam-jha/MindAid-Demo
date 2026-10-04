"""FoundrySummariser tests. The model call is replaced with a fake, so nothing is sent to Azure."""
import json
from datetime import datetime

import httpx
import pytest

from app import config
from app.models import Entry, User
from app.summarisers import get_summariser
from app.summarisers.base import SummariserError
from app.summarisers.foundry import NO_RISK_DISCLAIMER, FoundrySummariser

ENTRIES = [
    Entry(text="I can't sleep.\nNothing helps.", created_at=datetime(2026, 1, 1, 9, 0), is_demo=False),
    Entry(text="I don't see the point anymore.", created_at=datetime(2026, 1, 2, 9, 0), is_demo=False),
]
GOOD = {
    "narrative": "Sleep trouble and hopelessness.", "themes": ["sleep"], "mood_pattern": "Declining.",
    "concerning_content": [{"excerpt": "I don't see the point anymore.", "note": "Hopelessness."}],
    "priority": {"level": "urgent", "reason": "Hopelessness in latest entry."},
    "suggested_session_focus": "Risk assessment.", "uncertainty_note": "Short entries.",
}


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(config, "AZURE_AI_ENDPOINT", "https://example.invalid/")
    monkeypatch.setattr(config, "AZURE_AI_DEPLOYMENT", "dep")
    monkeypatch.setattr(config, "AZURE_AI_API_KEY", "not-a-real-key")


def fake_model(monkeypatch, payload, model="gpt-4.1-mini-test"):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr(FoundrySummariser, "_call_model", lambda self, messages: (text, model))


def test_good_response_is_parsed(monkeypatch):
    fake_model(monkeypatch, GOOD)
    s = FoundrySummariser().summarise(ENTRIES)
    assert s["priority"]["level"] == "urgent" and s["generated_by"] == "foundry:gpt-4.1-mini-test"
    assert s["concerning_content"][0]["note"] == "Hopelessness."  # verbatim quote, so no warning added


def test_no_risk_disclaimer_always_added_by_code(monkeypatch):
    fake_model(monkeypatch, {**GOOD, "uncertainty_note": ""})
    assert NO_RISK_DISCLAIMER in FoundrySummariser().summarise(ENTRIES)["uncertainty_note"]


def test_non_verbatim_quote_is_kept_but_marked_unverified(monkeypatch):
    bad = {**GOOD, "concerning_content": [{"excerpt": "I want to disappear", "note": "x"}]}
    fake_model(monkeypatch, bad)
    items = FoundrySummariser().summarise(ENTRIES)["concerning_content"]
    assert len(items) == 1 and "Unverified" in items[0]["note"]  # never silently dropped


def test_quote_matches_across_line_breaks(monkeypatch):
    q = {**GOOD, "concerning_content": [{"excerpt": "I can't sleep. Nothing helps.", "note": "x"}]}
    fake_model(monkeypatch, q)
    assert "Unverified" not in FoundrySummariser().summarise(ENTRIES)["concerning_content"][0]["note"]


def test_invalid_priority_becomes_unassessed(monkeypatch):
    fake_model(monkeypatch, {**GOOD, "priority": {"level": "fine", "reason": "all good"}})
    assert FoundrySummariser().summarise(ENTRIES)["priority"]["level"] == "unassessed"


def test_unreadable_output_raises_friendly_error(monkeypatch):
    fake_model(monkeypatch, "this is not json")
    with pytest.raises(SummariserError):
        FoundrySummariser().summarise(ENTRIES)


def test_missing_config_raises(monkeypatch):
    monkeypatch.setattr(config, "AZURE_AI_API_KEY", "")
    with pytest.raises(SummariserError):
        FoundrySummariser().summarise(ENTRIES)


def test_content_filter_gives_read_raw_entries_message(monkeypatch):
    resp = httpx.Response(400, text='{"error":{"code":"content_filter"}}')
    monkeypatch.setattr(httpx, "post", lambda *a, **k: resp)
    with pytest.raises(SummariserError, match="raw entries"):
        FoundrySummariser()._call_model([])


def test_network_failure_raises_friendly_error(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("no network")
    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(SummariserError):
        FoundrySummariser()._call_model([])


def test_long_history_keeps_newest_entries_and_says_so(monkeypatch):
    long = [Entry(text="x" * 4000, created_at=datetime(2026, 1, i + 1), is_demo=False) for i in range(10)]
    fake_model(monkeypatch, GOOD)
    s = FoundrySummariser().summarise(long)
    assert "most recent entries" in s["uncertainty_note"]


def test_summarise_button_shows_error_not_crash(psychologist, monkeypatch):
    monkeypatch.setattr(config, "SUMMARISER_MODE", "foundry")
    monkeypatch.setattr(config, "AZURE_AI_API_KEY", "")  # misconfigured on purpose
    r = psychologist.post("/psychologist/patients/3/summarise", follow_redirects=True)
    assert r.status_code == 200 and "not configured" in r.text


def test_get_summariser_picks_by_mode(monkeypatch):
    monkeypatch.setattr(config, "SUMMARISER_MODE", "foundry")
    assert isinstance(get_summariser(), FoundrySummariser)


def test_routine_reason_always_says_not_an_assurance(monkeypatch):
    fake_model(monkeypatch, {**GOOD, "concerning_content": [], "priority": {"level": "routine", "reason": "No risk indicators found."}})
    assert "not an assurance of safety" in FoundrySummariser().summarise(ENTRIES)["priority"]["reason"]


def test_summarise_all_continues_after_one_patient_fails(psychologist, monkeypatch):
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import Summary

    def picky(self, messages):
        if "JAMES-SECRET" in messages[1]["content"]:
            raise SummariserError("blocked by filter")
        return json.dumps({**GOOD, "concerning_content": []}), "m"

    monkeypatch.setattr(config, "SUMMARISER_MODE", "foundry")
    monkeypatch.setattr(FoundrySummariser, "_call_model", picky)
    r = psychologist.post("/psychologist/summarise-all", follow_redirects=True)
    assert "Generated 1 summaries" in r.text and "James Test" in r.text and "blocked by filter" in r.text
    with SessionLocal() as db:
        assert [s.patient_id for s in db.scalars(select(Summary))] == [2]  # Maya was still summarised


def test_filtered_response_is_retried(monkeypatch):
    from app.summarisers.foundry import _ResponseFiltered
    calls = []

    def flaky(self, messages):
        calls.append(1)
        if len(calls) == 1:
            raise _ResponseFiltered()
        return json.dumps(GOOD), "m"

    monkeypatch.setattr(FoundrySummariser, "_call_once", flaky)
    assert FoundrySummariser()._call_model([])[0] and len(calls) == 2


def test_always_filtered_gives_read_raw_entries_message(monkeypatch):
    from app.summarisers.foundry import _ResponseFiltered

    def always(self, messages):
        raise _ResponseFiltered()

    monkeypatch.setattr(FoundrySummariser, "_call_once", always)
    with pytest.raises(SummariserError, match="raw entries"):
        FoundrySummariser()._call_model([])


def test_blocked_patient_is_saved_as_blocked_and_sorted_below_urgent(psychologist, monkeypatch):
    import re
    from app.database import SessionLocal
    from app.models import Summary

    def picky(self, messages):
        if "JAMES-SECRET" in messages[1]["content"]:
            from app.summarisers.foundry import _ResponseFiltered
            raise _ResponseFiltered()
        return json.dumps({**GOOD, "concerning_content": [], "priority": {"level": "routine", "reason": "ok"}}), "m"

    monkeypatch.setattr(config, "SUMMARISER_MODE", "foundry")
    monkeypatch.setattr(FoundrySummariser, "_call_once", picky)
    psychologist.post("/psychologist/summarise-all")
    with SessionLocal() as db:
        levels = {s.patient_id: s.priority_level for s in db.query(Summary)}
    assert levels == {2: "routine", 3: "blocked"}
    page = psychologist.get("/psychologist").text
    assert re.findall(r'patient-name">([A-Za-z]+)', page) == ["James", "Maya"]  # blocked outranks routine
    assert "AI blocked - read entries" in page
    detail = psychologist.get("/psychologist/patients/3").text
    assert "No AI summary was produced" in detail and "not an assessment of risk" in detail


def test_blocked_attempt_is_not_shown_to_patient_as_a_summary(james, psychologist, monkeypatch):
    from app.summarisers.foundry import _ResponseFiltered

    def blocked(self, messages):
        raise _ResponseFiltered()

    monkeypatch.setattr(config, "SUMMARISER_MODE", "foundry")
    monkeypatch.setattr(FoundrySummariser, "_call_once", blocked)
    psychologist.post("/psychologist/patients/3/summarise")
    james.post("/patient/consent", data={"understood": "yes"})
    assert "generated a summary" not in james.get("/patient/log").text
