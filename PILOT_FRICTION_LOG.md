# 📋 F.R.I.D.A.Y. v2.0 — Phase 7.1 Pilot Friction Log

**Pilot Period:** August 19 – August 25, 2026  
**Primary Goal:** Capture organic edge-cases, voice barge-in hiccups, context misses, and latency friction from natural daily assistant usage.

---

## 🎯 Severity Guidelines

| Severity | Definition | Action Rule |
| :--- | :--- | :--- |
| **P0** | **Critical Safety / Wrong External Action** | Immediate stop & fix |
| **P1** | **Major Usability Failure** (e.g. broken intent, lost context, failed barge-in) | High-priority batch in Phase 7.3 |
| **P2** | **Moderate Friction / Latency Stutter** (e.g. slow TTS chunking, awkward phrasing) | Batch for Phase 7.3 |
| **P3** | **Minor / Cosmetic Polish** (e.g. UI spacing, badge alignment) | Batch for Phase 7.3 |

---

## 📝 High-Fidelity Friction Log Template

```text
DATE / TIME:
COMMAND:
INPUT: [Voice / Text / UI Click]
EXPECTED:
ACTUAL:
DOMAIN: [Voice / Career / Email / Calendar / Trading / Memory / UI / Fast-Path]
LATENCY:
SEVERITY: [P0 / P1 / P2 / P3]
REPRODUCIBLE: [Yes / No / Intermittent]
SCREENSHOT / LOG REF: [Optional]
NOTES / CONTEXT:
```

---

### Example Entry:
```text
DATE / TIME: 2026-08-19 09:30 AM
COMMAND: "What is the salary for the second role?"
INPUT: Voice
EXPECTED: Returns salary for Job #2 from the active Career OS search
ACTUAL: Asked to specify the company name again
DOMAIN: Career OS / Context Memory
LATENCY: ~1.8s
SEVERITY: P1
REPRODUCIBLE: Yes
SCREENSHOT / LOG REF: None
NOTES / CONTEXT: Anaphora resolution dropped active entity when switching from search list to detail query.
```

---

## 📅 Daily Pilot Log (August 19, 2026):

### Entry #1: Resume Upload Section Partitioning
- **Command / Action:** Uploaded PDF/text resume in Career OS ➔ Resume Manager
- **Expected:** AI divides content cleanly across 7 sections (Summary, Skills, Experience, Education, Projects, Achievements, Certifications)
- **Actual:** All content collapsed into "Professional Summary"
- **Root Cause:** LLM output string check `isinstance(parsed_json, dict)` returned False, falling back to regex parser with unmapped headers.
- **Resolution:** ✅ `FIXED` — Added JSON string deserialization and `_format_section` formatter for clean markdown output across all 7 sections.

### Entry #2: Spontaneous Music Playback
- **Command / Action:** Spoke sentences with words like "playwright", "play around with X", "can you help"
- **Expected:** Processed as AI brain conversation or code discussion
- **Actual:** Triggered Spotify desktop playback
- **Root Cause:** Fast-path regex `\bplay\b\s+(.*)` and phonetic alias `"help away"` captured generic conversational English.
- **Resolution:** ✅ `FIXED` — Added non-music guards (`NON_MUSIC_PLAY_PATTERNS`), question intent bypass, and removed loose alias `"help away"`.

### Entry #3: WhatsApp Search Client Fast-Path Hijack
- **Command / Action:** Spoke *"open WhatsApp and search Vishal"*
- **Expected:** Opens WhatsApp and searches for contact "Vishal"
- **Actual:** Frontend fast-path intercepted `"whatsapp and search vishal"` as a macOS app name to launch.
- **Resolution:** ✅ `FIXED` — Restricted client-side `open_app` shortcut to simple single-app names (rejected phrases with conjunctions/search keywords), routing compound actions to the AI brain.

### Entry #4: WhatsApp Desktop Search & Chat Typing
- **Command / Action:** Spoke *"search Vishal on WhatsApp"*, *"open chat with Vishal and type where are you"*
- **Expected:** Opens chat with contact and types message
- **Actual:** Search bar accumulated text (`vishalvishal`) or typed app name `"whatsapp"`.
- **Resolution:** ✅ `FIXED` — Implemented clean-slate AppleScript automation (`Cmd+F` ➔ `Cmd+A` ➔ `Delete` ➔ contact ➔ `Down Arrow` ➔ `Return` ➔ type message). Added app-name safeguard and instant sending (`"send it"`).
