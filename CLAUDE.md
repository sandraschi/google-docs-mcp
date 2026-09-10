# CLAUDE.md — google-docs-mcp

Thin override for Claude Code sessions in this repo. Full fleet rules live at
`D:\Dev\repos\mcp-central-docs\standards\` — read `AGENTS.md` §4.1 before scaffolding
anything new here.

## What this repo is

FastMCP server wrapping Google Docs API v1 + Google Drive API v3. See
[README.md](README.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and
[docs/TOOLS.md](docs/TOOLS.md) before making changes.

## Local commands

```bash
just test   # pytest (mocked Google API, no real credentials needed)
just lint   # ruff check + format --check
just ci     # both
```

## Guardrails specific to this repo

- Never log or print OAuth tokens, client secrets, or the contents of `data/token.json`.
- `delete_permanently` in `google_drive` is destructive and irreversible — it already requires
  `confirm=True` in the tool signature; do not remove that guard or add a way to bypass it.
- Docs API indices shift after every edit — do not cache an `index`/`start_index`/`end_index`
  across two separate tool calls without re-fetching `get_structure` in between.
