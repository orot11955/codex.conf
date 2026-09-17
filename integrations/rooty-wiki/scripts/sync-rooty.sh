#!/usr/bin/env bash
# Explicit operator sync only. No automatic cron registration, credentials, or LLM.
set -euo pipefail
exec "${ROOTY_WIKI_ADMIN_BIN:-$HOME/.local/bin/rooty-wiki-admin}" sync
