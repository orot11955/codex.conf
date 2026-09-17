#!/usr/bin/env python3
"""Source-tree adapter; both installers use the same canonical wiki core."""
from pathlib import Path
_core = Path(__file__).resolve().parents[3] / 'skills/shared-wiki/scripts/wiki.py'
exec(compile(_core.read_bytes(), str(_core), 'exec'), globals())
