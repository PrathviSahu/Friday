# F.R.I.D.A.Y. — Deep Code Analysis & Bug Fix Report

**Date:** 2026-08-18 · **Branch:** `arena/01a013d7-friday` (base `3c69cd8`)
**Scope analyzed:** full backend (`backend/`, ~23k LOC Python, 195 API routes), full frontend (`friday-ui/`, ~19.5k LOC React/Vite), deployment manifests (`docker-compose.yml`, `render.yaml`, Dockerfiles, nginx, Vercel config), scripts.

## Verification baseline

| Check | Result |
|---|---|
| Backend syntax compile (`compileall`) | ✅ clean |
| Backend test suite (`pytest`) | ✅ **323 passed** (was 321 — 2 new regression tests added) |
| Backend production boot (`uvicorn --no-proxy-headers`) | ✅ `/` + gated endpoints respond |
| Frontend production build (`vite build`) | ✅ clean (1 pre-existing chunk-size warning) |
| Frontend lint (`oxlint`) | ✅ 0 errors, 45 benign warnings (1 real bug fixed) |
| Frontend tests (`vitest`) | ✅ 16 passed |
| Frontend↔backend route cross-check (195 backend routes vs all UI calls) | ✅ 100% aligned |
| Remote-caller auth sweep (28 personal-data endpoints) | ✅ all 401 without token, 200 with token |
| Docker-style proxy-spoof test (`X-Forwarded-For: 127.0.0.1`) | ✅ spoof rejected (401) with fix |

---

## 🔴 Critical — fixed

### 1. Owner-auth bypass in the Docker/Render deployment (`backend/Dockerfile`)
The backend `Dockerfile` CMD ran:

```
uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
```

Uvicorn's **default** `proxy-headers` mode rewrites `request.client` from the client-supplied `X-Forwarded-For` / `X-Real-IP` headers. `backend/auth.py` and `app.py` both explicitly document that the server **must** run with `--no-proxy-headers`, and the frontend nginx (`nginx.conf`) forwards `X-Forwarded-For` — so any remote attacker could send `X-Forwarded-For: 127.0.0.1` and be treated as the owner: full access to todos/memories/career profile, machine-control endpoints, and your Groq/Gemini credits.

**Verified:** with `--no-proxy-headers`, a non-loopback client sending the spoofed header gets **401** without the token, **200** with it.

**Fix:** added `--no-proxy-headers` to the Dockerfile CMD (applies to both `docker-compose` and `render.yaml`). A comment warns never to remove it.

### 2. `render.yaml` hardcoded `FRIDAY_MODE: demo` — public unauthenticated instance
`FRIDAY_MODE=demo` makes `is_boss_request()` return `True` for **every** request. Anyone who finds the Render URL got full owner access (read your data, burn your API credits). **Fix:** `FRIDAY_MODE` is no longer silently set; it's now a commented-out opt-in with a loud warning. The generated `FRIDAY_API_TOKEN` now actually gates the API.

## 🟠 High — fixed

### 3. ~28 personal-data endpoints had no authentication
Only *writes* were gated; the reads were wide open. A remote caller with no token could read:

`/api/todos`, `/api/reminders`, `/api/knowledge` (+search/projects), `/api/timeline` (+summary), `/api/goals`, `/api/learning` (+streak), `/api/life-memory` (+search), `/api/notifications`, `/api/briefing`, `/api/proactive`, `/api/watchlist`, `/api/spotify/current-track`, `/api/system/stats`, `/api/system/display`, `/api/trading/chart-db` (saved chart drawings), `/api/gdrive/status`, `/api/permissions`, `/api/agents`, `/api/agent/route`, plus cost-bearing `POST /api/tts` and `POST /api/search`.

**Fix:** added `Depends(require_boss)` to all of them (trading GETs and weather too — the UI always carries the token, so zero functional impact; loopback/dev and docker healthcheck still work). Added 2 regression tests covering the full list.

### 4. Hardcoded stale Render URL in the frontend (`friday-ui/src/api/config.js`)
`API_BASE_URL` fell back to `https://friday-api-wy2b.onrender.com` for *any* non-localhost host — that's the original author's personal service name. Your deployment's backend lives at a different URL, so **every** API call would 404/break. **Fix:** removed the hardcoded fallback — resolution is now `VITE_API_BASE_URL` → `VITE_API_URL` → relative (`''`, proxied by Vite/nginx). Documented in the file.

### 5. Service-worker presence pushes can't authenticate (`public/sw.js`)
The SW's `fetch('/api/presence/pending')` and `/api/presence/decision` run in the worker scope, outside the page's `window.fetch` token wrapper → **401 in Docker/Render**, so approve/deny notifications silently never worked. **Fix:** the page now forwards the baked-in token to the SW via `postMessage` (`services/presencePush.js`), and the SW attaches `X-FRIDAY-Token` to its fetches (`authedFetch`).

## 🟡 Medium — fixed

### 6. Career "Connect account" crashes with an unhandled 500 (`backend/services/platform_session.py`)
`launch_real_browser_login()` launched Playwright **outside** its try/except. In the default Docker image (`INSTALL_BROWSERS=0`, no Chromium) or on a headless server, clicking Connect returned a raw 500. **Fix:** full try/except wrapping, a headless-Linux guard with a human-readable message ("run FRIDAY on your own machine to connect accounts"), and graceful `{status:"error"}` responses — never a 500.

### 7. SW notification icon 404 (`public/icon-192.png`)
`sw.js` referenced `/icon-192.png`, which didn't exist. **Fix:** added `public/icon-192.png` (from the existing Tauri 256px icon).

### 8. Duplicate `border` key (`friday-ui/src/UI/Career/modules/Opportunities.jsx`)
A style object set `border: 'none'` then re-set `border` conditionally; the first was dead (second wins). Removed the dead key.

---

## ✅ Verified healthy (deep-dive results)

- **API surface is consistent:** all 195 backend routes vs every frontend call — 100% matched (only real param-name check: `/api/company/intel` takes `name`, and it's only used by the function engine, which passes it correctly).
- **Tests are meaningful:** 321 pre-existing tests (auth gates, honest account-verify, TTS relative URL, upload caps, rate limiter, vault encryption, TA math, brain_v2 dispatch, permission enforcement, presence, macros, autonomy) all pass.
- **Auth model is sound after fixes:** loopback = owner; otherwise `X-FRIDAY-Token` required; `is_boss` no longer client-controlled; uvicorn no longer trusts proxy headers.
- **Career router** is fully gated at router level (`dependencies=[Depends(require_boss)]`) and rate-limited on AI endpoints.
- **TTS returns relative `/temp_audio/…` URLs** (works across dev proxy / Docker nginx / Tauri).
- **Vault crypto is correct** (PBKDF2-250k + AES-GCM-256, sentinel validation, no plaintext passphrase persistence).
- **SQL discipline:** parameterized queries + allowlist for dynamic columns; WAL mode + busy_timeout on SQLite; JSON stores are the only un-locked ones (todos/reminders/spotify cache) — pre-existing, low-risk.
- **Background tasks** (market pollers, gdrive sync, automation runner, temp-audio cleanup) are lifespan-managed with stop events — no import-time zombie threads.
- **Frontend:** error boundary at root, lazy-loaded widgets, WebAuthn fingerprint flow, proper mobile mic handling, gesture-unlocked AudioContext for TTS.

## ⚠️ Remaining observations (not fixed — your call)

1. **Public-data GETs gated now** — after redeploy, the Docker `healthcheck` still works (it hits `/api/system/stats` from loopback). No action needed.
2. **Render + separate frontend:** after redeploying the backend, build the frontend with `VITE_FRIDAY_TOKEN` set to the same value as the backend's `FRIDAY_API_TOKEN` (Render generates one) and `VITE_API_BASE_URL` pointing at your Render URL. In pure Docker this is automatic.
3. **`weather` defaults to Nashik, India** when IP geolocation fails (author's home city) — set `WEATHER_CITY` if you want your own (check `services/weather.py` for the env hook; it currently reads `city_query` only via the `get_weather()` call — worth wiring to an env var if weather matters to you).
4. **Frontend `localStorage` reads** in `Opportunities.jsx`, `useOrbState.jsx`, `useFingerprint.js`, `SlidingDashboard.jsx`, `secureVault.js` are not wrapped in try/catch (works in normal browsers; can throw in hardened/private contexts).
5. **`LockScreen.jsx` lint noise** (unused destructured vars `audioEnabled`, `enableAudioFromGesture`, `scale`) — cosmetic.
6. **Presence push still needs `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`** in the backend env to actually send pushes — without them the SW subscription is skipped (by design, silent).

## Redeploy checklist (do this to ship the fixes)

```bash
# Docker
cp .env.example .env            # fill FRIDAY_API_TOKEN + API keys
docker compose up -d --build    # rebuild both images (token + proxy-header fix)

# Render (backend)
git push; trigger deploy        # new image includes --no-proxy-headers + gated routes
# → set GROQ/GEMINI keys + FRIDAY_API_TOKEN in dashboard (FRIDAY_MODE unset!)

# Vercel / static frontend
# Build env:  VITE_FRIDAY_TOKEN=<same as backend token>
#             VITE_API_BASE_URL=https://<your-backend-url>
```

After redeploy, re-run: `cd backend && python -m pytest tests/` (323 tests) and open the UI — the dashboard, chat, trading, career and all panels keep working because every call already sends the token.
