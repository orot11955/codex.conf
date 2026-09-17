#!/usr/bin/env sh
# Existing install.sh entry point, backed by one implementation.
set -eu
BASE=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
if [ "$#" -eq 0 ]; then set -- install; fi
exec "${PYTHON_BIN:-python3}" "$BASE/scripts/agentctl.py" "$@"
