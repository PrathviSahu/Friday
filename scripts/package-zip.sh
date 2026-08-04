#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  package-zip.sh — Build a CLEAN source ZIP of F.R.I.D.A.Y.
#
#  Why: zipping the working folder drags in node_modules/,
#  .venv/, dist/, __pycache__ etc. (a reviewer once counted
#  59,000 files). `git archive` exports only TRACKED source
#  files, so the ZIP is tiny and safe to share.
#
#  Usage:  ./scripts/package-zip.sh
#  Output: FRIDAY-<branch>-<shortsha>.zip in the repo root.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BRANCH="$(git rev-parse --abbrev-ref HEAD | tr '/' '-')"
SHORT_SHA="$(git rev-parse --short HEAD)"
OUT="FRIDAY-${BRANCH}-${SHORT_SHA}.zip"

echo "  📦 Packaging clean source ZIP (tracked files only)…"
git archive --format=zip -o "$OUT" HEAD

COUNT="$(git ls-files | wc -l | tr -d ' ')"
SIZE="$(du -h "$OUT" | cut -f1)"

echo "  ✅ $OUT"
echo "     • $COUNT tracked files · $SIZE"
echo "     • No node_modules / venv / dist / __pycache__"
echo "     • Unzip anywhere, then:  docker compose up -d --build"
