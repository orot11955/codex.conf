#!/usr/bin/env bash
# Operator/OS scheduler utility; no LLM. Does not enumerate other hosts or publish.
set -euo pipefail
exec "${ROOTY_WIKI_BIN:-$HOME/.local/bin/rooty-wiki}" pending "$@"
