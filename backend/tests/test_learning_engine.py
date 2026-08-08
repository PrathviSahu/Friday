"""Regression tests for the Adaptive Self-Learning Engine (services/learning_engine.py).

Covers the soft-correction escalation bug fix:
    penalty_weight was `MIN(penalty_weight - 10.0, -80.0)` — with negative
    penalties MIN() returns the MORE negative value, so a single repeat
    correction jumped straight from -40 to the -80 floor instead of stepping
    down by 10. Correct behavior: MAX(penalty_weight - 10.0, -80.0).
"""

import pytest

from services import learning_engine as le


# ── Soft correction escalation ────────────────────────────────────────────────

def _log_correction_n_times(query: str, target: str, n: int):
    ctx = {"query": query, "target": target}
    for _ in range(n):
        assert le.detect_and_log_correction("no not that", ctx) is True


def test_first_correction_starts_at_minus_40():
    _log_correction_n_times("atlantis", "atlantis (sped up)", 1)
    assert le.get_correction_penalty("atlantis", "atlantis (sped up)") == -40.0


def test_repeat_corrections_escalate_by_ten_not_jump_to_floor():
    """Regression: MIN() bug made the 2nd correction jump -40 → -80."""
    _log_correction_n_times("blinding lights", "blinding lights (remix)", 2)
    assert le.get_correction_penalty("blinding lights", "blinding lights (remix)") == -50.0

    _log_correction_n_times("blinding lights", "blinding lights (remix)", 1)
    assert le.get_correction_penalty("blinding lights", "blinding lights (remix)") == -60.0


def test_penalty_never_goes_below_floor():
    _log_correction_n_times("kesariya", "kesariya (lofi mix)", 10)
    penalty = le.get_correction_penalty("kesariya", "kesariya (lofi mix)")
    assert penalty == -80.0


def test_correction_penalty_matches_substring_candidate():
    """A longer candidate title containing the rejected target is penalized."""
    _log_correction_n_times("night changes", "night changes (slowed)", 1)
    assert le.get_correction_penalty(
        "night changes", "night changes (slowed) — official audio"
    ) == le.get_correction_penalty("night changes", "night changes (slowed)")


def test_unpenalized_candidate_scores_zero():
    assert le.get_correction_penalty("some query", "some clean candidate") == 0.0


@pytest.mark.parametrize("text", [
    "play something else",          # no trigger phrase
    "what is the weather today",
    "nice song friday",
])
def test_neutral_text_is_not_logged_as_correction(text):
    ctx = {"query": "neutral query", "target": "neutral target"}
    assert le.detect_and_log_correction(text, ctx) is False
    assert le.get_correction_penalty("neutral query", "neutral target") == 0.0


def test_correction_skipped_without_context():
    assert le.detect_and_log_correction("no not that", {"query": "", "target": ""}) is False


# ── Habit learning & proactive suggestions ────────────────────────────────────

def test_proactive_suggestion_after_repeated_habit():
    """S_habit = min(1, freq/5) >= 0.70 requires freq >= 4 (with freq >= 3 gate)."""
    # Isolate the current time slot: the suggestion picks the single highest-
    # frequency habit for this hour/day, so clear the whole slot (session DB
    # is shared across test files — autonomy tests seed other habits here).
    from datetime import datetime as _dt
    _now = _dt.now()
    with le._db() as conn:
        conn.execute(
            "DELETE FROM user_action_habits WHERE hour_of_day = ? AND day_of_week = ?",
            (_now.hour, _now.weekday()))
        conn.commit()

    assert le.get_proactive_habit_suggestion() is None  # empty slot → nothing

    for _ in range(3):
        le.log_user_action("weather")
    # freq = 3 -> confidence 0.6 -> below 0.70 threshold
    assert (le.get_proactive_habit_suggestion() or {}).get("action") != "weather"

    le.log_user_action("weather")
    # freq = 4 -> confidence 0.8 -> proactive suggestion fires
    suggestion = le.get_proactive_habit_suggestion()
    assert suggestion is not None
    assert suggestion["action"] == "weather"
    assert suggestion["confidence"] == pytest.approx(0.8)
    assert "weather" in suggestion["prompt"].lower()

    with le._db() as conn:  # cleanup so re-runs stay deterministic
        conn.execute("DELETE FROM user_action_habits WHERE action_type = 'weather'")
        conn.commit()


def test_low_value_actions_are_not_tracked():
    with le._db() as conn:
        conn.execute("DELETE FROM user_action_habits WHERE action_type = 'scroll_reels'")
        conn.commit()
    le.log_user_action("scroll_reels")  # not in HIGH_VALUE_ACTIONS
    with le._db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM user_action_habits WHERE action_type = 'scroll_reels'"
        ).fetchone()
    assert row["c"] == 0


# ── Dynamic pace matching (brevity controller) ────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("play atlantis", "ultra_concise"),
    ("volume up", "ultra_concise"),
    ("how's the market looking for reliance and tata motors today", "balanced"),
    ("explain why the market fell today", "detailed"),       # 'explain' forces detailed
    ("tell me about the new ai regulations announced", "detailed"),
])
def test_brevity_mapping(text, expected):
    assert le.compute_response_brevity(text) == expected
    assert le.compute_response_brevity(text) in le.BREVITY_INSTRUCTIONS


# ── Career profile extraction ─────────────────────────────────────────────────

def test_extract_job_profile_from_text():
    out = le.extract_job_profile_from_text(
        "I am a java developer with 2 years of experience and I know python and react"
    )
    assert out["primary_role"] == "Java Developer"
    assert out["experience_years"] == "2"
    assert "Java" in out["skills"] and "Python" in out["skills"]

    profile = le.get_job_profile()
    assert profile["primary_role"] == "Java Developer"
