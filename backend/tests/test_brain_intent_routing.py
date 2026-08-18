"""tests/test_brain_intent_routing.py — Regression tests for Career vs Trading intent routing."""

import pytest
from services.brain.engine import respond


class TestBrainIntentRouting:
    """Test suite ensuring generic 'analyze' queries never hijack career intent into trading."""

    # ── CAREER INTENT TEST CASES ──

    def test_career_spring_boot_job_analysis(self, monkeypatch):
        """1. 'Friday, analyze this Java Spring Boot job and tell me whether I should apply.' -> Career"""
        res = respond("Friday, analyze this Java Spring Boot job and tell me whether I should apply.")
        reply = res.get("reply", "").lower()
        # Must not mention quant/bullish EMA chart market structure
        assert "bullish market structure" not in reply
        assert "20-period ema" not in reply
        assert "quant technical analysis" not in reply

    def test_career_resume_analysis(self):
        """2. 'Analyze my resume.' -> Career / Resume analysis (NOT Trading)"""
        res = respond("Analyze my resume.")
        reply = res.get("reply", "").lower()
        assert "bullish market structure" not in reply
        assert "quant technical analysis" not in reply

    def test_career_job_description_analysis(self):
        """3. 'Analyze this job description.' -> Career / Job analysis (NOT Trading)"""
        res = respond("Analyze this job description.")
        reply = res.get("reply", "").lower()
        assert "bullish market structure" not in reply
        assert "quant technical analysis" not in reply

    def test_career_should_apply_role(self):
        """4. 'Should I apply for this software engineer role?' -> Career"""
        res = respond("Should I apply for this software engineer role?")
        reply = res.get("reply", "").lower()
        assert "bullish market structure" not in reply
        assert "quant technical analysis" not in reply

    def test_career_goals_inquiry(self):
        """5. 'What do you know about my career goals?' -> Career"""
        res = respond("What do you know about my career goals?")
        reply = res.get("reply", "").lower()
        assert "bullish market structure" not in reply
        assert "quant technical analysis" not in reply

    # ── TRADING INTENT TEST CASES ──

    def test_trading_current_market_structure(self):
        """6. 'Friday, analyze the current market and tell me the market structure.' -> Trading"""
        res = respond("Friday, analyze the current market and tell me the market structure.")
        reply = res.get("reply", "").lower()
        assert "quant technical analysis" in reply or "market structure" in reply

    def test_trading_chart_analysis(self):
        """7. 'Analyze this chart.' -> Trading"""
        res = respond("Analyze this chart.")
        reply = res.get("reply", "").lower()
        assert "quant technical analysis" in reply or "market structure" in reply

    def test_trading_btc_analysis(self):
        """8. 'Analyze BTC.' -> Trading"""
        res = respond("Analyze BTC.")
        reply = res.get("reply", "").lower()
        assert "btc" in reply or "market structure" in reply

    def test_trading_rsi_and_trend(self):
        """9. 'What's the RSI and trend?' -> Trading"""
        res = respond("What's the RSI and trend?")
        reply = res.get("reply", "").lower()
        assert "rsi" in reply or "market structure" in reply

    def test_trading_nifty_analysis(self):
        """10. 'Analyze NIFTY.' -> Trading"""
        res = respond("Analyze NIFTY.")
        reply = res.get("reply", "").lower()
        assert "nifty" in reply or "market structure" in reply

    # ── CONTEXT SWITCHING TEST CASES ──

    def test_context_switch_sequence(self):
        """11 -> 12 -> 13 Sequence: Trading -> Career -> Trading"""
        # 11. "Analyze the market."
        r11 = respond("Analyze the market.")
        assert "quant technical analysis" in r11.get("reply", "").lower()

        # 12. "Forget the market. Analyze this Java job."
        r12 = respond("Forget the market. Analyze this Java job.")
        reply12 = r12.get("reply", "").lower()
        assert "bullish market structure" not in reply12
        assert "quant technical analysis" not in reply12

        # 13. "Now analyze BTC."
        r13 = respond("Now analyze BTC.")
        assert "btc" in r13.get("reply", "").lower() or "quant technical analysis" in r13.get("reply", "").lower()
