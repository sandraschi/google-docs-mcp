"""Mechanical check for the fleet's 3-4-100 MCPB prompt rule.

Run from the repo root: `uv run python scripts/verify_3_4_100.py`
Exits non-zero (and prints which floor failed) if any threshold is unmet.
"""

import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys_path = repo_root / "assets" / "prompts" / "system.md"
user_path = repo_root / "assets" / "prompts" / "user.md"
examples_path = repo_root / "assets" / "prompts" / "examples.json"

sys_words = len(sys_path.read_text(encoding="utf-8").split())
user_words = len(user_path.read_text(encoding="utf-8").split())
examples = len(json.loads(examples_path.read_text(encoding="utf-8")))

print(f"system={sys_words} (need >=3000) user={user_words} (need >=4000) examples={examples} (need >=100)")

if sys_words < 3000 or user_words < 4000 or examples < 100:
    print("3-4-100 FAIL")
    sys.exit(1)

print("3-4-100 PASS")
