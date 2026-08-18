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

    # ── G. 15 NATURAL CONVERSATION STRESS TESTS (PHASE 4.5) ──

    def test_15_natural_conversation_stress_suite(self):
        """Runs the 15 exact natural human conversational stress tests."""

        # 1. "Find me a good Java job." -> "What about the salary?"
        r1_1 = respond("Find me a good Java job.")
        assert "zepto" in r1_1["reply"].lower() or "java" in r1_1["reply"].lower()
        r1_2 = respond("What about the salary?")
        assert "8–12 lpa" in r1_2["reply"].lower()

        # 2. "Should I apply?"
        r2 = respond("Should I apply?")
        assert "recommend" in r2["reply"].lower()

        # 3. "No, the other one."
        r3 = respond("No, the other one.")
        assert "jpmorgan" in r3["reply"].lower() or "alternative" in r3["reply"].lower()

        # 4. "Check BTC." -> "What about RSI?"
        r4_1 = respond("Check BTC.")
        assert "btc" in r4_1["reply"].lower()
        r4_2 = respond("What about RSI?")
        assert "btc" in r4_2["reply"].lower()
        assert "rsi" in r4_2["reply"].lower()

        # 5. "Actually forget BTC, check ETH."
        r5 = respond("Actually forget BTC, check ETH.")
        assert "eth" in r5["reply"].lower()

        # 6. "Compare that with the one before."
        r6 = respond("Compare that with the one before.")
        assert "eth/btc" in r6["reply"].lower() or "btc" in r6["reply"].lower()

        # 7. "Forget trading. Let's look at jobs."
        r7 = respond("Forget trading. Let's look at jobs.")
        assert get_context().current_domain == "CAREER"

        # 8. "Okay, now go back to BTC."
        r8 = respond("Okay, now go back to BTC.")
        assert "btc" in r8["reply"].lower()

        # 9. Ambiguity with both active: "Check this."
        update_context(domain="CAREER", job_title="SDE", company="ZDL", trading_symbol="BTC")
        r9 = respond("Check this.")
        assert "do you want me to analyze the" in r9["reply"].lower()

        # 10. "Remember I don't want jobs below 6 LPA." -> "Show me jobs."
        r10_1 = respond("Remember I don't want jobs below 6 LPA.")
        assert "6 lpa" in r10_1["reply"].lower() or "recorded" in r10_1["reply"].lower()
        r10_2 = respond("Show me jobs.")
        assert "6 lpa" in r10_2["reply"].lower()

        # 11. "Forget my salary preference." -> "Show me jobs."
        r11_1 = respond("Forget my salary preference.")
        assert "cleared" in r11_1["reply"].lower()
        r11_2 = respond("Show me jobs.")
        assert "6 lpa" not in r11_2["reply"].lower()

        # 12. "Find Kesariya." -> "No, the Kannada one." -> "Play it."
        r12_1 = respond("Find Kesariya.")
        assert "kesariya" in r12_1["reply"].lower()
        r12_2 = respond("No, the Kannada one.")
        assert "kannada" in r12_2["reply"].lower()
        r12_3 = respond("Play it.")
        assert r12_3["action"] == "play_specific"
        assert "kannada" in r12_3["target_app"].lower()

        # 13. "What was that song?"
        r13 = respond("What was that song?")
        assert "kannada" in r13["reply"].lower()

        # 14. "Bro, that first job looked better. Why?"
        r14 = respond("Bro, that first job looked better. Why?")
        assert "zepto" in r14["reply"].lower() or "96%" in r14["reply"].lower()

        # 15. "Actually never mind, go back to the one from JPMorgan."
        r15 = respond("Actually never mind, go back to the one from JPMorgan.")
        assert "jpmorgan" in r15["reply"].lower()
