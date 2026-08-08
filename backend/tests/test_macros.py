"""Tests for the Phase 2.4 Voice Macro & Workflow Composer.

Acceptance per next_phase_2_architecture.md §7:
  * create–run–delete a 3-step macro by voice (tool handler path)
  * a failing step halts the chain and reports which step failed

Dispatch is stubbed via monkeypatched macros._dispatch (never touches the
real GUI/Spotify/LLM). Organic-tier paths pin both clocks (macros + autonomy).
"""

from datetime import datetime

import pytest

from services import macros
from services import autonomy_engine as ae

NOON = datetime(2026, 8, 10, 12, 0, 0)   # Monday, outside quiet hours


@pytest.fixture(autouse=True)
def _clean_macros():
    with macros._db() as conn:
        conn.execute("DELETE FROM voice_macros")
        conn.execute("DELETE FROM macro_runs")
        conn.commit()
    yield


@pytest.fixture()
def dispatched(monkeypatch):
    """Stub BOTH dispatch paths: forced runs use macros._dispatch, organic
    (announce/silent) runs route through autonomy_engine's dispatcher."""
    calls = []
    monkeypatch.setattr(
        macros, "_dispatch",
        lambda tool, params: calls.append((tool, params or {})) or f"{tool} done.")
    monkeypatch.setattr(
        ae, "_dispatch_tool",
        lambda name, params: calls.append((name, params or {})) or f"{name} done.")
    return calls


@pytest.fixture()
def noon_both_clocks(monkeypatch):
    monkeypatch.setattr(macros, "_now", lambda: NOON)
    monkeypatch.setattr(ae, "_now", lambda: NOON)


def _seed_silent_step(action: str):
    """Make one tool/action organically silent-tier (reversible + trusted)."""
    import services.learning_engine as le
    with le._db() as conn:
        conn.execute("INSERT OR REPLACE INTO user_action_habits"
                     " (action_type, hour_of_day, day_of_week, frequency)"
                     " VALUES (?, 12, 0, 12)", (action,))
        conn.commit()
    with ae._lock, ae._db() as conn:
        conn.execute("INSERT OR REPLACE INTO action_trust"
                     " (action_type, accepts, rejects, tier, last_acted_at)"
                     " VALUES (?, 12, 0, 'silent', ?)",
                     (action, NOON.isoformat(timespec="seconds")))
        conn.commit()


# ── Creation & validation ─────────────────────────────────────────────────────

def test_create_and_get_macro():
    r = macros.create_macro("start my morning",
                            [{"tool": "open_trading"}, {"tool": "get_weather"}])
    assert r["status"] == "ok" and r["trigger_phrase"] == "start my morning"
    got = macros.get_macro(r["id"])
    assert got["enabled"] is True and len(got["steps"]) == 2


def test_trigger_normalization_exact_match():
    macros.create_macro("Start My Morning!", [{"tool": "get_weather"}])
    assert macros.get_macro_by_trigger("start my morning") is not None
    assert macros.get_macro_by_trigger("  START   MY MORNING? ") is not None
    assert macros.get_macro_by_trigger("start my morning please") is None  # exact only


@pytest.mark.parametrize("steps,err", [
    ([], "at least one step"),
    ([{"tool": "totally_fake_tool"}], "unknown tool"),
    ([{"tool": "create_macro"}], "cannot be used inside a macro"),
    ([{"tool": "guest_permission"}], "cannot be used inside a macro"),
    ([{"params": {}}], "missing a tool name"),
    ([{"tool": "get_weather", "params": "oops"}], "params must be an object"),
    ([{"tool": "get_weather"}] * 9, "at most 8 steps"),
])
def test_step_validation_errors(steps, err):
    with pytest.raises(macros.MacroError, match=err):
        macros.create_macro("zz validation test", steps)


def test_duplicate_trigger_rejected():
    macros.create_macro("zz unique", [{"tool": "get_weather"}])
    with pytest.raises(macros.MacroError, match="already exists"):
        macros.create_macro("zz unique", [{"tool": "get_weather"}])


def test_llm_shorthand_string_steps_coerced():
    r = macros.create_macro("zz shorthand", ["get_weather", "get_time"])
    assert [s["tool"] for s in r["steps"]] == ["get_weather", "get_time"]


# ── Execution: forced (owner-approved) path ──────────────────────────────────

def test_forced_run_executes_steps_sequentially(dispatched):
    m = macros.create_macro("zz run force",
                            [{"tool": "open_trading"},
                             {"tool": "get_weather"},
                             {"tool": "play_spotify", "params": {"query": "lofi"}}])
    r = macros.run_macro(macro_id=m["id"], force=True)
    assert r["executed"] is True and r["steps_ok"] == 3 and r["steps_failed"] == 0
    assert [c[0] for c in dispatched] == ["open_trading", "get_weather", "play_spotify"]
    assert dispatched[2][1] == {"query": "lofi"}

    runs = macros.list_macros()[0]["recent_runs"]
    assert runs[0]["steps_ok"] == 3 and runs[0]["steps_failed"] == 0


def test_failing_step_halts_chain_and_reports(dispatched, monkeypatch):
    calls = []

    def flaky(tool, params):
        calls.append(tool)
        return "I hit a problem running get_weather. Please try again." \
            if tool == "get_weather" else f"{tool} done."

    monkeypatch.setattr(macros, "_dispatch", flaky)
    m = macros.create_macro("zz halt test",
                            [{"tool": "open_trading"}, {"tool": "get_weather"},
                             {"tool": "play_spotify"}])
    r = macros.run_macro(macro_id=m["id"], force=True)
    assert r["executed"] is False and r["failed_step"] == {"index": 2, "tool": "get_weather"}
    assert calls == ["open_trading", "get_weather"]      # step 3 never ran
    assert "stopped at step 2" in r["reply"]
    assert macros.list_macros()[0]["recent_runs"][0]["steps_failed"] == 1


# ── Trust interplay ───────────────────────────────────────────────────────────

def test_confirm_tier_macro_returns_suggestion(dispatched, noon_both_clocks):
    """One confirm-tier step makes the whole macro ask-first (min-tier rule)."""
    m = macros.create_macro("zz confirm gate",
                            [{"tool": "open_trading"}, {"tool": "get_weather"}])
    r = macros.run_macro(macro_id=m["id"])
    assert r["executed"] is False and r["tier"] == "confirm"
    assert r["suggestion"] == "Prem, shall I run 'zz confirm gate'?"
    assert dispatched == []                                   # nothing executed


def test_silent_macro_runs_organically_and_grows_trust(dispatched, noon_both_clocks):
    _seed_silent_step("open_trading")   # reversible, trusted → silent
    _seed_silent_step("play_spotify")   # reversible, trusted → silent
    m = macros.create_macro("zz silent run", [{"tool": "open_trading"},
                                              {"tool": "play_spotify"}])
    r = macros.run_macro(macro_id=m["id"])
    assert r["executed"] is True and r["tier"] == "silent"
    assert [c[0] for c in dispatched] == ["open_trading", "play_spotify"]
    row = ae.decide("macro:zz silent run", "open_trading", now=NOON)
    assert row["trust"] > 0.5                               # accepted outcome fed back


def test_min_tier_inheritance_mixed_steps(dispatched, noon_both_clocks):
    _seed_silent_step("open_trading")                       # silent step...
    m = macros.create_macro("zz mixed tiers",
                            [{"tool": "open_trading"}, {"tool": "get_weather"}])
    r = macros.run_macro(macro_id=m["id"])                  # ...+ confirm step
    assert r["executed"] is False and r["tier"] == "confirm"


# ── Deletion ──────────────────────────────────────────────────────────────────

def test_delete_by_id_and_trigger():
    a = macros.create_macro("zz del one", [{"tool": "get_weather"}])
    assert macros.delete_macro(macro_id=a["id"])["status"] == "ok"
    assert macros.get_macro(a["id"]) is None

    macros.create_macro("zz del two", [{"tool": "get_weather"}])
    assert macros.delete_macro(trigger="ZZ DEL TWO!")["status"] == "ok"
    assert macros.delete_macro(trigger="zz del two")["status"] == "error"


def test_delete_removes_run_history(dispatched):
    m = macros.create_macro("zz del history", [{"tool": "get_weather"}])
    macros.run_macro(macro_id=m["id"], force=True)
    assert macros.list_macros()[0]["recent_runs"]
    macros.delete_macro(macro_id=m["id"])
    with macros._db() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM macro_runs").fetchone()["c"]
    assert n == 0


# ── Voice tool handlers ──────────────────────────────────────────────────────

def test_voice_create_run_delete_flow(dispatched, noon_both_clocks):
    """Full voice journey: create by tool → run by phrase → delete by tool."""
    reply = macros.handle_create_macro({
        "trigger": "evening wind down",
        "steps": [{"tool": "play_spotify", "params": {"query": "lofi"}},
                  {"tool": "get_weather"}, {"tool": "get_time"}],
    })
    assert "saved with 3 steps" in reply
    _seed_silent_step("play_spotify")                        # make chain announce+
    _seed_silent_step("get_weather") if False else None      # (others stay confirm)
    # confirm-tier → suggestion, not execution
    out = macros.match_and_maybe_run("evening wind down")
    assert out["action"] == "macro_confirm" and "shall i run" in out["reply"].lower()

    forced = macros.run_macro(trigger="evening wind down", force=True)
    assert forced["executed"] is True and forced["steps_ok"] == 3

    gone = macros.handle_delete_macro({"trigger": "evening wind down"})
    assert "deleted" in gone
    assert macros.get_macro_by_trigger("evening wind down") is None


def test_voice_create_rejects_bad_tool():
    reply = macros.handle_create_macro({"trigger": "zz bad", "steps": [{"tool": "nope"}]})
    assert "couldn't save" in reply and "unknown tool" in reply


def test_non_trigger_phrase_falls_through_to_brain():
    assert macros.match_and_maybe_run("what is the weather like today") is None


# ── API round-trip ────────────────────────────────────────────────────────────

def test_api_create_list_run_delete(client, dispatched):
    r = client.post("/api/macros", json={
        "trigger_phrase": "api macro test",
        "steps": [{"tool": "get_weather"}, {"tool": "get_time"}]})
    assert r.status_code == 201
    macro_id = r.json()["id"]

    listed = client.get("/api/macros").json()["macros"]
    assert any(m["trigger_phrase"] == "api macro test" for m in listed)

    run = client.post(f"/api/macros/{macro_id}/run", json={"force": True})
    assert run.status_code == 200 and run.json()["executed"] is True

    assert client.delete(f"/api/macros/{macro_id}").status_code == 200
    assert client.delete(f"/api/macros/{macro_id}").status_code == 404


def test_api_validation_errors(client):
    assert client.post("/api/macros", json={
        "trigger_phrase": "zz api dup", "steps": [{"tool": "get_weather"}]}).status_code == 201
    dup = client.post("/api/macros", json={
        "trigger_phrase": "zz api dup", "steps": [{"tool": "get_weather"}]})
    assert dup.status_code == 409
    bad = client.post("/api/macros", json={
        "trigger_phrase": "zz api bad", "steps": [{"tool": "fake_tool"}]})
    assert bad.status_code == 400


def test_api_run_missing_macro(client):
    assert client.post("/api/macros/99999/run", json={}).status_code == 404


def test_api_remote_blocked(remote_client):
    assert remote_client.post(
        "/api/macros", json={"trigger_phrase": "x", "steps": []}).status_code == 401
    assert remote_client.get("/api/macros").status_code == 401
    assert remote_client.delete("/api/macros/1").status_code == 401
    assert remote_client.post("/api/macros/1/run", json={}).status_code == 401


# ── Chat fast path (0ms, before any LLM call) ────────────────────────────────

def test_chat_fast_path_intercepts_trigger(client, dispatched, noon_both_clocks):
    macros.create_macro("fast path check", [{"tool": "get_weather"}])
    r = client.post("/api/chat/text", json={"text": "fast path check"})
    assert r.status_code == 200
    body = r.json()
    # confirm-tier macro → suggestion reply (never reached an LLM — no keys set)
    assert body["action"] == "macro_confirm"
    assert "shall i run 'fast path check'" in body["reply"].lower()


def test_chat_fast_path_ignores_non_trigger(client):
    r = client.post("/api/chat/text", json={"text": "hello friday"})
    assert r.status_code == 200 and r.json()["action"] != "macro"
