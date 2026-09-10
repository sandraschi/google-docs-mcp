"""Assert the packaged entry point resolves ONLY from mcpb/src, not site-packages.

A successful import from an editable-installed site-packages copy is a false
pass (see MCPB_PACKAGING_STANDARDS.md §2.5 required check 1). Usage:
`uv run python scripts/verify_mcpb_import.py <stage_src_dir> <package_name>`
"""

import sys
from pathlib import Path

stage_src = Path(sys.argv[1]).resolve()
package_name = sys.argv[2]

# Only the staged src dir on the path — nothing from the project's own venv.
sys.path.insert(0, str(stage_src))

module = __import__(package_name)
origin = Path(module.__file__).resolve()

if stage_src not in origin.parents:
    print(f"FAIL: import resolved outside stage: {origin}")
    sys.exit(1)

print(f"import OK: {origin}")
