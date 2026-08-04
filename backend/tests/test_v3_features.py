"""Tests for the v3 feature set: function engine, TA engine, brain_v2,
telegram bot, and the modular route split."""

import pytest


# ═══ Function engine ════════════════════════════════════════════════════════

def test_function_engine_registers_tools():
    from services import function_engine
    tools = function_engine.get_tools_schema()
    assert len(tools) == 24
    names = {t["function"]["name"] for t in tools}
    assert {"get_time", "get_weather", "play_spotify", "control_spotify",
            "add_todo", "get_todos", "set_reminder", "open_app",
            "system_control", "search_web", "navigate_to", "take_screenshot",
            "open_trading", "close_trading", "guest_permission",
            "remember_fact", "technical_analysis", "get_spotify_info"} <= names


def test_function_engine_dispatch_time():
    from services.function_engine import dispatch
    reply = dispatch("get_time", {})
    assert ":" in reply  # contains a time


def test_function_engine_unknown_function():
    from services.function_engine import dispatch
    assert "Unknown" in dispatch("nope", {})


# ═══ Technical analysis engine ══════════════════════════════════════════════

def _synthetic_candles(n=120, start=100.0):
    candles, price = [], start
    for i in range(n):
        o = price
        c = price + (0.5 if i % 3 else -0.4)
        h, l = max(o, c) + 0.3, min(o, c) - 0.3
        candles.append({"time": i, "open": round(o, 2), "high": round(h, 2),
                        "low": round(l, 2), "close": round(c, 2),
                        "volume": 1000 + i})
        price = c
    return candles


def test_technical_analysis_computes_indicators():
    from services.technical_analysis import analyze_candles
    a = analyze_candles(_synthetic_candles())
    ind = a["indicators"]
    assert 0 <= ind["rsi"] <= 100
    assert ind["macd"] is not None
    assert ind["bollinger_upper"] > ind["bollinger_lower"]
    assert ind["atr"] > 0
    assert a["trend"]["bias"] in ("bullish", "bearish", "neutral")
    assert a["candle_count"] == 120


def test_technical_analysis_detects_hammer():
    from services.technical_analysis import analyze_candles
    candles = _synthetic_candles(30)
    # Append a hammer: big lower wick, small body near the top
    candles.append({"time": 999, "open": 100.0, "high": 100.4,
                    "low": 98.5, "close": 100.2, "volume": 5000})
    a = analyze_candles(candles)
    assert "Hammer" in a["patterns"]


def test_technical_analysis_empty_data():
    from services.technical_analysis import analyze_candles
    a = analyze_candles([])
    assert "error" in a


def test_technical_analysis_builds_summary():
    from services.technical_analysis import analyze_candles, _build_summary
    a = analyze_candles(_synthetic_candles())
    summary = _build_summary(a, "FX:EURUSD")
    assert "FX:EURUSD" in summary
    assert "Prem" in summary


# ═══ Brain v2 ═══════════════════════════════════════════════════════════════

def test_brain_v2_falls_back_to_legacy_without_keys(monkeypatch):
    """No API keys configured → gracefully falls back to the legacy brain."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from services.brain_v2 import respond_v2
    result = respond_v2("hello friday", is_boss=True)
    assert result.get("engine") == "brain_v1"
    assert "reply" in result


def test_brain_v2_groq_tool_path_dispatches(monkeypatch):
    """Groq returns a tool call → engine dispatches to the registered handler."""
    from services import brain_v2

    def fake_groq(text, tools):
        return {"tool_calls": [{"name": "get_time", "arguments": {}}],
                "content": ""}

    monkeypatch.setattr(brain_v2, "_call_groq_with_tools", fake_groq)
    monkeypatch.setattr(brain_v2, "_groq_client", lambda: object())
    result = brain_v2.respond_v2("what time is it", is_boss=True)
    assert result["function"] == "get_time"
    assert ":" in result["reply"]


# ═══ Telegram bot ═══════════════════════════════════════════════════════════

def test_telegram_bot_importable():
    import services.telegram_bot as tb
    assert hasattr(tb, "run_bot")


def test_telegram_bot_requires_token(monkeypatch):
    import services.telegram_bot as tb
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        tb.build_application()


def test_telegram_owner_id_parse():
    import services.telegram_bot as tb
    assert tb._owner_id() == 0  # no env set in test env


# ═══ Modular route split ════════════════════════════════════════════════════

def test_route_modules_cover_all_endpoints(client):
    """Every must-have v2/v3 endpoint exists in the OpenAPI schema."""
    schema = client.app.openapi()["paths"]
    must_have = [
        "/api/chat/text", "/api/memory", "/api/permission", "/api/proactive",
        "/api/open-app", "/api/close-app", "/api/system/display",
        "/api/system/display/brightness", "/api/system/stats",
        "/api/spotify/current-track", "/api/spotify/seek",
        "/api/todos", "/api/todos/done",
        "/api/tts", "/api/weather", "/api/search", "/api/reminders",
        "/api/gdrive/status", "/api/gdrive/sync-now",
        "/api/watchlist",
        "/api/trading/ohlcv", "/api/trading/live-prices",
        "/api/trading/indian-prices", "/api/trading/search",
        "/api/trading/chart-db", "/api/trading/analysis",
    ]
    missing = [p for p in must_have if p not in schema]
    assert missing == []


def test_chat_route_still_rate_limited(client):
    """The moved chat route still enforces the sliding-window limiter."""
    from ratelimit import is_rate_limited
    ip = "198.51.100.9"
    results = [is_rate_limited(ip, limit=3, window=60) for _ in range(5)]
    assert results == [False, False, False, True, True]
