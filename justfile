set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

# Run the MCP server over stdio
serve:
    uv run google-docs-mcp

# Run pytest
test:
    uv run pytest -q

# ruff check + ruff format --check (+ webapp biome/tsc when webapp/ exists)
lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/

# ruff format (auto-fix)
fmt:
    uv run ruff format src/ tests/
    uv run ruff check --fix src/ tests/

# Everything CI runs, locally
ci: lint test

# Build the .mcpb bundle (wipe+recopy src/ -> mcpb/src/ first)
mcpb-pack:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/mcpb-pack.ps1

# Build the Tauri/NSIS desktop installer
build-native:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File native/build.ps1

# Playwright e2e smoke suite (start backend+frontend with `start.ps1` first)
e2e:
    cd webapp; bunx playwright test
