#!/usr/bin/env bash
# Production deploy: builds the Flutter web app against the deployed Render
# API and pushes it to Vercel's production alias (shaala-os.vercel.app).
#
# This is manual by design. Vercel's GitHub auto-deploy has no Flutter SDK
# and no generated code (.freezed.dart/.g.dart and apps/admin/build/ are
# gitignored), so a git-triggered build finds nothing to build and silently
# ships an empty deployment marked "READY" -- see vercel.json's
# ignoreCommand, which turns that auto-deploy into a no-op, and PROGRESS.md
# (Phase 6) for how this was discovered.
#
# Run from the repo root after `make verify` passes.
#
# Uses --project explicitly rather than relying on a `.vercel/project.json`
# link file inside build/web: that directory is deleted and recreated by
# every `flutter build web`, so a link left there gets wiped each time --
# which is exactly how an earlier deploy silently created a stray second
# Vercel project instead of updating shaala-os.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT/apps/admin"

flutter pub get
dart run build_runner build --delete-conflicting-outputs
flutter build web --release \
  --dart-define=API_BASE_URL=https://shaala-os-api.onrender.com \
  --dart-define=WS_BASE_URL=wss://shaala-os-api.onrender.com

vercel deploy --prod --yes --project shaala-os --scope arunish-rajputs-projects \
  "$REPO_ROOT/apps/admin/build/web"
