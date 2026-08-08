"""Tests for the Phase 2.1 Autonomy & Trust Engine (services/autonomy_engine.py).

Acceptance per next_phase_2_architecture.md §7:
  * unit tests for decide() tier math (incl. hysteresis and the 300s undo window)
  * journal round-trip via API

Time is fully controlled via monkeypatched autonomy_engine._now, and tool
dispatch via monkeypatched _dispatch_tool — tests never touch the real GUI,
Spotify, or LLM. Action names are unique per test (the session fixture shares
one temp DB across the whole run).
"""

import json
from datetime import datetime, timedelta

import pytest

from services import autonomy_engine as ae

NOON = datetime(2026, 8, 8, 12, 0, 0)          # a Saturday, outside quiet hours


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def noon(monkeypatch):
    monkeypatch.setattr(ae, "_now", lambda: NOON)
    return NOON


@pytest.fixture()
def dispatched(monkeypatch):
    """Stub tool dispatch; records (name, params) calls."""
    calls = []
    monkeypatch.setattr(
        ae, "_dispatch_tool",
        lambda name, params: calls.append((name, params or {})) or "Done.")
    return calls


def _seed_trust(action: str, accepts: int = 0, rejects: int = 0,
                tier: str = "confirm", last_acted=None):
    with ae._lock, ae._db() as conn:
        conn.execute(
            "DELETE FROM action_trust WHERE action_type = ?", (action,))
        conn.execute(
            "INSERT INTO action_trust (action_type, accepts, rejects, tier, last_acted_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (action, accepts, rejects, tier,
             (last_acted or NOON).isoformat(timespec="seconds")))
        conn.commit()


def _seed_habits(action: str, frequency: int):
    # user_action_habits lives in learning_engine's store (a separate file
    # under test isolation — same friday_brain.db in production).
    from services import learning_engine
    with learning_engine._db() as conn:
        conn.execute(
            "DELETE FROM user_action_habits WHERE action_type = ?", (action,))
        conn.execute(
            "INSERT INTO user_action_habits (action_type, hour_of_day, day_of_week, frequency)"
            " VALUES (?, 12, 5, ?)", (action, frequency))
        conn.commit()


def _trust_row(action: str):
    with ae._db() as conn:
        return conn.execute(
            "SELECT * FROM action_trust WHERE action_type = ?", (action,)).fetchone()


# ── Pure trust math ───────────────────────────────────────────────────────────

def test_trust_prior_is_half_for_new_action():
    assert ae.compute_trust(0, 0, None, NOON) == pytest.approx(0.50)


def test_trust_rises_with_accepts():
    assert ae.compute_trust(10, 0, None, NOON) == pytest.approx(11 / 12)


def test_trust_decays_with_time_since_last_action():
    import math
    fresh = ae.compute_trust(10, 0, NOON, NOON)
    month_old = ae.compute_trust(10, 0, NOON - timedelta(days=30), NOON)
    assert month_old == pytest.approx(fresh * math.exp(-0.10 * 30), abs=1e-6)
    assert month_old < fresh / 2  # a month idle erodes most earned trust


def test_undo_penalty_outweighs_accepts():
    # 10 accepts then 3 undos (R+=2 each → R=6): (11)/(10+6+2) = 0.611
    assert ae.compute_trust(10, 6, NOON, NOON) == pytest.approx(11 / 18)


# ── Tier assignment incl. hysteresis ─────────────────────────────────────────

@pytest.mark.parametrize("trust,executions,reversible,current,expected", [
    (0.90, 10, True,  "confirm", "silent"),     # gains silent at ≥ 0.85, N ≥ 10
    (0.90, 9,  True,  "confirm", "announce"),   # sample-size gate: N ≥ 10 hard
    (0.90, 10, False, "confirm", "announce"),   # irreversible → never silent
    (0.83, 10, True,  "silent",  "silent"),     # hysteresis hold (≥ 0.82 keeps)
    (0.83, 10, True,  "confirm", "announce"),   # ...but can't GAIN silent at 0.83
    (0.81, 10, True,  "silent",  "announce"),   # below 0.82 → drops out of silent
    (0.70, 3,  True,  "confirm", "announce"),
    (0.70, 2,  True,  "confirm", "confirm"),    # announce needs N ≥ 3
    (0.50, 0,  True,  "confirm", "confirm"),
    (0.59, 50, True,  "confirm", "confirm"),
])
def test_assign_tier(trust, executions, reversible, current, expected):
    assert ae.assign_tier(trust, executions, reversible, current) == expected


# ── decide() invariants ───────────────────────────────────────────────────────

def test_quiet_hours_force_confirm(monkeypatch):
    monkeypatch.setattr(ae, "_now", lambda: NOON.replace(hour=23, minute=30))
    d = ae.decide("zzz_quiet_open", "open_trading")
    assert d["tier"] == "confirm" and d["blocked_reason"] == "quiet_hours"

    monkeypatch.setattr(ae, "_now", lambda: NOON.replace(hour=6))
    assert ae.decide("zzz_quiet_open", "open_trading")["blocked_reason"] == "quiet_hours"


def test_new_action_decides_confirm(noon):
    d = ae.decide("zzz_brand_new", "open_trading")
    assert d["tier"] == "confirm" and d["trust"] == pytest.approx(0.50)
    assert d["blocked_reason"] is None


def test_high_trust_reversible_action_earns_silent(noon):
    _seed_trust("zzz_silent_trading", accepts=10, tier="announce")
    _seed_habits("zzz_silent_trading", frequency=10)
    d = ae.decide("zzz_silent_trading", "open_trading")
    assert d["tier"] == "silent" and d["trust"] >= ae.SILENT_THRESHOLD
    assert d["executions"] >= 10


def test_external_comm_capped_at_confirm_forever(noon):
    _seed_trust("zzz_email_act", accepts=50, tier="silent")
    _seed_habits("zzz_email_act", frequency=50)
    d = ae.decide("zzz_email_act", "send_email")
    assert d["tier"] == "confirm" and d["blocked_reason"] == "external_comm"


def test_permission_denied_blocks_and_approval_never_consumed(noon, monkeypatch):
    from services import permissions
    monkeypatch.setattr(permissions, "check_permission", lambda cap: "denied")
    assert ae.decide("zzz_shot", "take_screenshot")["blocked_reason"] == "permission_denied"

    monkeypatch.setattr(permissions, "check_permission", lambda cap: "approval_required")
    d = ae.decide("zzz_shot", "take_screenshot")
    assert d["tier"] == "confirm" and d["blocked_reason"] == "permission_approval"

    _seed_habits("zzz_shot2", 12); _seed_trust("zzz_shot2", accepts=12, tier="announce")
    monkeypatch.setattr(permissions, "check_permission", lambda cap: "allowed")
    assert ae.decide("zzz_shot2", "take_screenshot")["tier"] in {"silent", "announce"}


def test_budget_exhaustion_forces_confirm(noon):
    since = NOON - timedelta(minutes=10)
    with ae._lock, ae._db() as conn:
        for i in range(ae.AUTONOMY_BUDGET_PER_CLASS):
            conn.execute(
                "INSERT INTO autonomy_journal"
                " (action_type, tool_name, tier, outcome, executed_at)"
                " VALUES (?, 'play_spotify', 'silent', 'auto_accepted', ?)",
                (f"zzz_budget_{i}", since.isoformat(timespec="seconds")))
        conn.commit()
    d = ae.decide("zzz_budget_next", "play_spotify")   # same 'media' class
    assert d["tier"] == "confirm" and d["blocked_reason"] == "budget_exhausted"
    other = ae.decide("zzz_budget_other", "open_trading")  # different class
    assert other["blocked_reason"] != "budget_exhausted"


# ── run() + journal + undo window ────────────────────────────────────────────

def test_run_confirm_returns_suggestion_without_executing(noon, dispatched):
    out = ae.run("zzz_run_confirm", "open_trading")
    assert out["executed"] is False and out["decision"]["tier"] == "confirm"
    assert "shall i" in out["suggestion"].lower()
    assert dispatched == []


def test_run_silent_executes_and_journals_with_undo_payload(noon, dispatched):
    _seed_trust("zzz_run_silent", accepts=12, tier="silent")
    _seed_habits("zzz_run_silent", frequency=12)
    out = ae.run("zzz_run_silent", "open_trading")
    assert out["executed"] is True and out["undo_available"] is True
    assert dispatched == [("open_trading", {})]

    entries = ae.get_journal(NOON.date().isoformat())
    row = next(e for e in entries if e["id"] == out["journal_id"])
    assert row["tier"] == "silent" and row["outcome"] is None
    assert json.loads(row["undo_payload"])["tool"] == "close_trading"


def test_run_failure_is_journaled_as_failed(noon, monkeypatch):
    _seed_trust("zzz_run_fail", accepts=12, tier="silent")
    _seed_habits("zzz_run_fail", frequency=12)
    monkeypatch.setattr(ae, "_dispatch_tool",
                        lambda n, p: "I hit a problem running open_trading. Please try again.")
    out = ae.run("zzz_run_fail", "open_trading")
    assert out["executed"] is False and out["journal_id"] is not None
    entries = ae.get_journal(NOON.date().isoformat())
    row = next(e for e in entries if e["id"] == out["journal_id"])
    assert row["outcome"] == "failed"


def test_undo_inside_window_reverts_and_penalizes(noon, dispatched):
    _seed_trust("zzz_undo_me", accepts=12, tier="silent")
    _seed_habits("zzz_undo_me", frequency=12)
    out = ae.run("zzz_undo_me", "open_trading")
    res = ae.undo(out["journal_id"])
    assert res["status"] == "ok" and res["undone"] is True
    assert dispatched[-1] == ("close_trading", {})          # compensation ran

    row = _trust_row("zzz_undo_me")
    assert row["rejects"] == 2 and row["last_undo_at"]        # R+2 strong signal
    entries = ae.get_journal(NOON.date().isoformat())
    j = next(e for e in entries if e["id"] == out["journal_id"])
    assert j["undone"] == 1 and j["outcome"] == "undone"


def test_undo_after_window_expires(noon):
    # 'add_todo' is in the 'general' budget class — keeps the trading-class
    # budget untouched for the other tests sharing this session DB.
    old = (NOON - timedelta(seconds=ae.UNDO_WINDOW_SECONDS + 60)).isoformat(timespec="seconds")
    with ae._lock, ae._db() as conn:
        cur = conn.execute(
            "INSERT INTO autonomy_journal (action_type, tool_name, tier, undo_payload,"
            " executed_at) VALUES ('zzz_expired', 'add_todo', 'silent', ?, ?)",
            (json.dumps({"tool": "close_trading", "params": {}}), old))
        jid = cur.lastrowid
        conn.commit()
    res = ae.undo(jid)
    assert res["status"] == "error" and "expired" in res["message"]


def test_undo_unknown_and_double_undo(noon, dispatched):
    assert ae.undo(999999)["status"] == "error"
    _seed_trust("zzz_double", accepts=12, tier="silent")
    _seed_habits("zzz_double", frequency=12)
    out = ae.run("zzz_double", "open_trading")
    assert ae.undo(out["journal_id"])["status"] == "ok"
    assert ae.undo(out["journal_id"])["message"] == "already undone"


def test_silent_success_counts_as_acceptance_after_window(noon, dispatched):
    _seed_trust("zzz_auto_accept", accepts=0, tier="silent")
    _seed_habits("zzz_auto_accept", frequency=12)
    old = (NOON - timedelta(seconds=ae.UNDO_WINDOW_SECONDS + 30)).isoformat(timespec="seconds")
    with ae._lock, ae._db() as conn:
        conn.execute(
            "INSERT INTO autonomy_journal (action_type, tool_name, tier, executed_at)"
            " VALUES ('zzz_auto_accept', 'open_trading', 'silent', ?)", (old,))
        conn.commit()
    finalized = ae.finalize_outcomes()
    assert finalized >= 1  # other tests' stale pending rows may sweep too (order-agnostic)
    row = _trust_row("zzz_auto_accept")
    assert row["accepts"] == 1
    entries = ae.get_journal((NOON - timedelta(seconds=ae.UNDO_WINDOW_SECONDS + 30))
                             .date().isoformat())
    j = next(e for e in entries if e["action_type"] == "zzz_auto_accept")
    assert j["outcome"] == "auto_accepted"


def test_revoke_resets_trust_to_confirm(noon):
    _seed_trust("zzz_revoked", accepts=20, tier="silent")
    res = ae.revoke("zzz_revoked")
    assert res["tier"] == "confirm"
    row = _trust_row("zzz_revoked")
    assert row["accepts"] == 0 and row["rejects"] == 0 and row["tier"] == "confirm"


def test_accepted_suggestions_accumulate_execution_evidence(monkeypatch):
    """Trust must self-accumulate: N grows from accepted suggestions even for
    actions outside learning_engine's curated high-value set (smoke-test bug)."""
    two_pm = NOON.replace(hour=14)  # fresh hour → other tests' journal rows fall
    monkeypatch.setattr(ae, "_now", lambda: two_pm)  # outside the budget window
    _seed_habits("zzz_self_earn", frequency=0)
    for _ in range(3):
        ae.record_outcome("zzz_self_earn", "accepted")
    d = ae.decide("zzz_self_earn", "open_trading")
    assert d["executions"] == 3 and d["tier"] == "announce"   # T=0.80, N=3

    for _ in range(7):
        ae.record_outcome("zzz_self_earn", "accepted")
    d = ae.decide("zzz_self_earn", "open_trading")
    assert d["executions"] == 10 and d["tier"] == "silent"    # T≈0.917, N=10


def test_record_outcome_arithmetic(noon):
    ae.record_outcome("zzz_outcomes", "accepted")
    ae.record_outcome("zzz_outcomes", "accepted")
    ae.record_outcome("zzz_outcomes", "rejected")
    row = _trust_row("zzz_outcomes")
    assert (row["accepts"], row["rejects"]) == (2, 1)
    ae.record_outcome("zzz_outcomes", "undone")
    assert _trust_row("zzz_outcomes")["rejects"] == 3
    assert ae.record_outcome("zzz_outcomes", "nonsense")["status"] == "error"


# ── API round-trip ────────────────────────────────────────────────────────────

def test_status_endpoint_shape(client):
    r = client.get("/api/autonomy/status")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert isinstance(body["actions"], list)
    assert isinstance(body["budget_remaining"], int)
    assert "media" in body["budget"]


def test_journal_endpoint_round_trip(client, noon, dispatched):
    # 'open_app' is in the 'system' budget class (trading budget is spent by
    # the earlier undo-window tests in this file).
    _seed_trust("zzz_api_journal", accepts=12, tier="silent")
    _seed_habits("zzz_api_journal", frequency=12)
    ae.run("zzz_api_journal", "open_app", {"app_name": "Notes"})
    r = client.get(f"/api/autonomy/journal?date={NOON.date().isoformat()}")
    assert r.status_code == 200
    entries = [e for e in r.json()["entries"] if e["action_type"] == "zzz_api_journal"]
    assert entries and entries[0]["tool_name"] == "open_app"
    assert entries[0]["tier"] == "announce"  # open_app is irreversible → announce max


def test_undo_endpoint_irreversible_entry(client, noon):
    with ae._lock, ae._db() as conn:
        cur = conn.execute(
            "INSERT INTO autonomy_journal (action_type, tool_name, tier, executed_at)"
            " VALUES ('zzz_api_undo', 'get_weather', 'announce', ?)",
            (NOON.isoformat(timespec="seconds"),))
        jid = cur.lastrowid
        conn.commit()
    r = client.post("/api/autonomy/undo", json={"journal_id": jid})
    assert r.status_code == 200
    assert r.json()["undone"] is False and "not reversible" in r.json()["message"]


def test_revoke_endpoint_round_trip(client, noon):
    _seed_trust("zzz_api_revoke", accepts=5, tier="announce")
    r = client.post("/api/autonomy/revoke", json={"action_type": "zzz_api_revoke"})
    assert r.status_code == 200
    assert r.json()["tier"] == "confirm"
    assert _trust_row("zzz_api_revoke")["tier"] == "confirm"


def test_remote_caller_blocked(remote_client):
    assert remote_client.get("/api/autonomy/status").status_code == 401
    assert remote_client.get("/api/autonomy/journal").status_code == 401
    assert remote_client.post("/api/autonomy/undo", json={"journal_id": 1}).status_code == 401
    assert remote_client.post(
        "/api/autonomy/revoke", json={"action_type": "x"}).status_code == 401
