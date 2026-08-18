"""tests/test_contextual_brain.py — Phase 4 Contextual Reasoning, Working Memory & Anaphora Test Suite."""

import pytest
from services.brain.engine import respond
from services.brain.context_manager import reset_context, get_context, update_context


@pytest.fixture(autouse=True)
def clean_context():
    """Reset working memory before every test to ensure isolation."""
    reset_context()
    yield
    reset_context()


class TestContextualBrain:
    """Comprehensive test suite for Phase 4 Contextual Brain & Working Memory Engine."""

    # ── A. CAREER CONTEXT & ANAPHORA RESOLUTION ──

    def test_career_active_job_flow(self):
        """1. Setting active job -> Asking salary -> Asking should I apply -> Comparing with JPMorgan"""
        # Step 1: User mentions Java Spring Boot job
        r1 = respond("Friday, analyze this Java Spring Boot job and tell me whether I should apply.")
        assert "zepto" in r1["reply"].lower() or "java" in r1["reply"].lower()
        ctx = get_context()
        assert ctx.current_domain == "CAREER"
        assert ctx.active_job_title is not None

        # Step 2: "What is the salary?" (Anaphoric reference to active job)
        r2 = respond("What is the salary?")
        assert "8–12 lpa" in r2["reply"].lower() or "compensation" in r2["reply"].lower()

        # Step 3: "Should I apply?" (Anaphoric reference to active job)
        r3 = respond("Should I apply?")
        assert "recommend" in r3["reply"].lower() or "match" in r3["reply"].lower()

        # Step 4: "Compare it with the JPMorgan role." (Comparative career reasoning)
        r4 = respond("Compare it with the JPMorgan role.")
        assert "jpmorgan" in r4["reply"].lower()

    # ── B. TRADING CONTEXT & SYMBOL TRACKING ──

    def test_trading_active_symbol_flow(self):
        """2. Active symbol tracking -> Indicator follow-up -> Symbol switch -> Comparison"""
        # Step 1: "Analyze BTC."
        r1 = respond("Analyze BTC.")
        assert "btc" in r1["reply"].lower()
        ctx = get_context()
        assert ctx.active_trading_symbol == "BTC"

        # Step 2: "What's the RSI?" (Anaphoric reference to active symbol BTC)
        r2 = respond("What's the RSI?")
        assert "btc" in r2["reply"].lower()
        assert "rsi" in r2["reply"].lower()

        # Step 3: "What about ETH?" (Switching active trading symbol to ETH)
        r3 = respond("What about ETH?")
        assert "eth" in r3["reply"].lower()
        ctx = get_context()
        assert ctx.active_trading_symbol == "ETH"

        # Step 4: "Compare it with BTC." (Comparative trading reasoning)
        r4 = respond("Compare it with BTC.")
        assert "eth/btc" in r4["reply"].lower() or "btc" in r4["reply"].lower()

    # ── C. CONTEXT SWITCHING & DOMAIN RESET ──

    def test_domain_context_switching(self):
        """3. Trading -> Reset to Career -> Switch back to Trading"""
        # Step 1: Start in Trading
        r1 = respond("Analyze the market.")
        assert "quant technical analysis" in r1["reply"].lower()

        # Step 2: "Forget the market. Analyze this Java job."
        r2 = respond("Forget the market. Analyze this Java job.")
        assert "quant technical analysis" not in r2["reply"].lower()
        assert "java" in r2["reply"].lower() or "zepto" in r2["reply"].lower()

        # Step 3: "Now analyze BTC."
        r3 = respond("Now analyze BTC.")
        assert "btc" in r3["reply"].lower()

    # ── D. AMBIGUITY HANDLING & CLARIFICATION ──

    def test_ambiguity_with_active_job_only(self):
        """4a. 'Analyze this.' with only active job present -> resolves to job."""
        update_context(
            domain="CAREER",
            job_title="Software Development Engineer (Java/Spring Boot)",
            company="Zepto Digital Labs",
            match_score=96,
            trading_symbol=None
        )
        r = respond("Analyze this.")
        assert "zepto" in r["reply"].lower() or "java" in r["reply"].lower()

    def test_ambiguity_with_active_chart_only(self):
        """4b. 'Analyze this.' with only active trading symbol present -> resolves to chart."""
        update_context(
            domain="TRADING",
            trading_symbol="NAS100",
            job_title=None,
            company=None
        )
        r = respond("Analyze this.")
        assert "nas100" in r["reply"].lower() or "quant technical analysis" in r["reply"].lower()

    def test_ambiguity_with_both_active(self):
        """4c. 'Analyze this.' with BOTH active job and chart -> asks clarification."""
        update_context(
            domain="CAREER",
            job_title="Software Development Engineer",
            company="Zepto Digital Labs",
            trading_symbol="BTC"
        )
        r = respond("Analyze this.")
        assert "do you want me to analyze the" in r["reply"].lower()

    # ── E. MEMORY COMMANDS & USER PREFERENCES ──

    def test_memory_preference_lifecycle(self):
        """5. Save salary preference -> Query preference -> Forget preference"""
        # Save preference
        r1 = respond("Remember that I don't want jobs below 5 LPA.")
        assert "5 lpa" in r1["reply"].lower() or "recorded" in r1["reply"].lower()

        # Query preference
        r2 = respond("What is my salary preference?")
        assert "5 lpa" in r2["reply"].lower()

        # Forget preference
        r3 = respond("Forget my salary preference.")
        assert "cleared" in r3["reply"].lower() or "forgotten" in r3["reply"].lower()

    # ── F. MUSIC CONTEXT & ANAPHORA ──

    def test_music_anaphora_flow(self):
        """6. Find song -> Specify version -> 'Play it' -> 'What was that song?'"""
        # Step 1: Find song
        r1 = respond("Find Kesariya.")
        assert "kesariya" in r1["reply"].lower()
        ctx = get_context()
        assert "Kesariya" in ctx.active_song_name

        # Step 2: Clarify version
        r2 = respond("That's the Kannada version.")
        assert "kannada" in r2["reply"].lower()

        # Step 3: "Play it."
        r3 = respond("Play it.")
        assert r3["action"] == "play_specific"
        assert "Kesariya" in r3["target_app"]

        # Step 4: "What was that song?"
        r4 = respond("What was that song?")
        assert "kesariya" in r4["reply"].lower()
