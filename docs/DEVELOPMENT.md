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

## Deliberate deviations from WEBAPP_SOTA_STANDARDS.md (declared, not silent)

- **No Inbox page.** The catch-them-all gate lists Inbox as "mandatory when the product has
  inbound events." This server has no inbound events in the webhook/push-notification sense.

- **Webhooks: deliberately not implemented (declared exception, not a gap).** Drive API v3
  does support push notifications (`files.watch`/`changes.watch`) that AGENTS.md §4.1 item 2
  would otherwise require shipping in the same pass as any inbound-event capability. Not
  implemented here because `files.watch` requires a **publicly reachable HTTPS callback URL**
  registered with Google — there is no such endpoint for a local desktop app with no public
  server, and standing one up (ngrok/Cloudflare Tunnel or similar) would be a materially
  different, much heavier product than "a local Google Docs companion app." Instead,
  `google_docs_sync` implements **polling** reconciliation on a background interval (min 60s) —
  see `sync_engine.py`'s module docstring for the full tradeoff. This is a real background job
  (an `asyncio.create_task` loop in the Starlette backend's lifespan), just not a webhook-driven
  one. If this server ever grows a public-facing deployment mode, `files.watch` becomes viable
  and worth revisiting — tracked as a real follow-up, not a page this webapp is missing today.
- **No MOCK-badged sample data on Dashboard/Documents.** `ONBOARDING_STANDARD.md` asks for
  "Joe Mocky"-style sample content so an unconfigured webapp isn't a blank desert. This repo
  instead shows the explicit, honest empty/error state (`error_type: "not_configured"` /
  `"not_authenticated"`, surfaced as amber warning banners) per `TESTING_GUIDE.md` § Declared
  doubles ("Empty list when unconfigured... not fabricated rows"). For a personal-productivity
  tool like this one, a real error message pointing at Settings felt more useful and less
  confusing than fake documents named after fictional people — but this is a judgment call,
  not a standards reading; revisit if user feedback says otherwise.
