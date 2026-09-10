# Development Setup

## Tools Required

```bash
winget install astral-sh.uv
winget install Git.Git
winget install OpenJS.NodeJS.LTS
winget install Oven-sh.Bun
winget install Casey.Just

uv --version
git --version
node --version
bun --version
just --version
```

## Setup

```bash
git clone https://github.com/sandraschi/google-docs-mcp
cd google-docs-mcp
uv sync --extra dev
cp .env.example .env   # fill in GOOGLE_DOCS_MCP_CLIENT_ID / _SECRET, see docs/ONBOARDING.md
```

## Common Tasks

```bash
just serve     # run the MCP server over stdio
just test      # pytest
just lint      # ruff check + ruff format --check (+ biome/tsc when webapp/ exists)
just fmt       # ruff format (auto-fix)
just ci        # everything CI runs, locally
just mcpb-pack # build the .mcpb bundle
```

## Declared doubles

Per `TESTING_GUIDE.md` § Declared doubles — the only test doubles in this repo:

| Kind | Where | Why |
|------|-------|-----|
| `unittest.mock.MagicMock` standing in for `googleapiclient.discovery.Resource` | `tests/conftest.py` (`mock_docs_service`, `mock_drive_service`) | Unit tests never make real network calls or need real Google credentials |
| `configured_env` fixture (fake `GOOGLE_DOCS_MCP_CLIENT_ID`/`_SECRET`) | `tests/conftest.py` | Exercises the "configured" code path without a real OAuth client |
| `not_configured` / `not_authenticated` dialogic errors | `src/google_docs_mcp/oauth.py`, tool modules | Not a test double — this is the real, declared production behavior when OAuth isn't set up yet (see `ONBOARDING_STANDARD.md` § Mock-until-onboarded; this server has no webapp mock UI, only explicit API error responses) |

No hardcoded fake KPIs, no `setTimeout` fake progress, no undeclared mocks anywhere else.

## Code Standards

Follow `mcp-central-docs/standards/TOOL_DESIGN_STANDARDS.md` (portmanteau pattern, docstring
template, dialogic returns) and `mcp-central-docs/standards/STARLETTE_NO_PYDANTIC_STANDARD.md`
(webapp backend: plain Starlette, no Pydantic in the REST layer — Pydantic is still used for
MCP tool parameter schemas via `Annotated[..., Field(...)]`, which is a FastMCP convention, not
a REST-layer decision).

## Onboarding: not N/A

This repo requires onboarding (a third-party account — see `docs/ONBOARDING.md`), so the
`ONBOARDING_STANDARD.md` § Exempt (rare) N/A path does not apply.
