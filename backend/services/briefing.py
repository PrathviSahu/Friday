"""briefing.py — Smart Daily Briefing (v3.1).

Aggregates everything FRIDAY already knows into a single morning / on-demand
briefing: weather, tasks, reminders, career pipeline, job matches, market
summary, and unread notifications. Used by GET /api/briefing and by the
'briefing' automation action.
"""

from datetime import datetime


def generate_daily_briefing() -> dict:
    """Build the full briefing as structured sections + a spoken summary."""
    from services.weather import get_weather
    from services.todos import get_todos
    from services.reminders import get_active_reminders
    from services.career_db import get_dashboard_stats, get_jobs
    from services.notifications import get_notifications, unread_count
    from services.market_data import fetch_live_market_prices

    sections = []

    # 1. Weather
    try:
        w = get_weather() or {}
        sections.append({
            "title": "Weather",
            "lines": [f"{w.get('city', 'your area')}: {w.get('condition', '—')}, "
                      f"{w.get('temperature', '--')}°C, feels like {w.get('feels_like', '--')}°C"],
        })
    except Exception:
        sections.append({"title": "Weather", "lines": ["Weather unavailable."]})

    # 2. Tasks
    todos = get_todos() or []
    pending = [t for t in todos if not t.get("done")]
    sections.append({
        "title": "Tasks",
        "lines": ([f"{i + 1}. {t['text']}" for i, t in enumerate(pending[:5])]
                  if pending else ["All caught up — no pending tasks."]),
    })

    # 3. Reminders / timers
    reminders = get_active_reminders() or []
    sections.append({
        "title": "Reminders",
        "lines": ([f"• {r.get('message')}" for r in reminders[:5]]
                  if reminders else ["No active reminders."]),
    })

    # 4. Career pipeline
    career_line = "Career data unavailable."
    try:
        stats = get_dashboard_stats() or {}
        jobs = get_jobs(min_score=70) or []
        sections.append({
            "title": "Career",
            "lines": [
                f"Applications in pipeline: {stats.get('application_count', 0)} "
                f"({stats.get('applied_count', 0)} applied, {stats.get('interview_count', 0)} interviews).",
                f"High-match jobs tracked: {len(jobs)} (score ≥ 70).",
            ],
        })
        career_line = f"{stats.get('application_count', 0)} applications in your pipeline."
    except Exception:
        sections.append({"title": "Career", "lines": [career_line]})

    # 5. Market summary
    try:
        prices = fetch_live_market_prices() or {}
        picks = []
        for key in ("FX:EURUSD", "OANDA:XAUUSD", "OANDA:NAS100USD", "BINANCE:BTCUSDT"):
            item = prices.get(key)
            if item:
                picks.append(f"{item.get('name', key)} {item.get('price', '—')} "
                             f"({item.get('changePct', '—')})")
        sections.append({
            "title": "Markets",
            "lines": picks if picks else ["Market feed unavailable."],
        })
    except Exception:
        sections.append({"title": "Markets", "lines": ["Market feed unavailable."]})

    # 6. Notifications
    unread = unread_count()
    recent = get_notifications(limit=3)
    sections.append({
        "title": "Notifications",
        "lines": ([f"• {n['title']}: {n['body'][:80]}" for n in recent]
                  + ([f"+{unread - len(recent)} more unread" if unread > len(recent) else None]
                     if unread else [])) if recent
        else [f"{unread} unread" if unread else "Inbox zero — nothing waiting."],
    })

    # Spoken summary
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
    spoken = (
        f"{greeting}, Boss. "
        f"{len(pending)} tasks pending. "
        f"{unread} notifications. "
        f"{career_line}"
    )

    return {
        "generated_at": datetime.now().isoformat(),
        "greeting": f"{greeting}, Boss.",
        "sections": sections,
        "spoken_summary": spoken,
    }
