# AGENTS.md — google-docs-mcp

Thin override. Canonical fleet standards: `D:\Dev\repos\mcp-central-docs\standards\AGENTS.md`.

## Repo-specific notes

- No local database — Google Docs/Drive are the source of truth. Do not add SQLite/LanceDB
  here without updating `docs/ARCHITECTURE.md`'s "no HTTP-daemon+proxy" rationale.
- OAuth token cache: `data/token.json` (gitignored). Never commit it, never log its contents.
- Ports: backend `11972`, frontend `11973` — registered in
  `mcp-central-docs/operations/WEBAPP_PORTS.md`.
- Backend framework: Starlette (no Pydantic in the REST layer) per
  `STARLETTE_NO_PYDANTIC_STANDARD.md` — this repo's REST surface is small (webapp glue only).
