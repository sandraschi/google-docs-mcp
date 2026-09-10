# google-docs-mcp

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://biomejs.dev"><img src="https://img.shields.io/badge/Linted_with-Biome-60a5fa?style=flat-square&logo=biome&logoColor=white" alt="Biome"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.4.4-7c5cfc?style=flat-square" alt="FastMCP"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square" alt="MIT"></a>
</p>

Real Google Docs editing and Google Drive file management for Claude — create, read, and edit
document content, browse/backup/restore whole folders, keep a local folder synced two-way with
Drive, and convert to formats Drive's own export can't produce, all through MCP tool calls.

## What this wraps

Wraps the official **Google Docs API v1** (document content) and **Google Drive API v3** (file
lifecycle: listing, sharing, trash, comments). Both are Google Workspace APIs — you sign in with
your own Google account via OAuth; nothing is bundled or proxied through a third party. See
[docs/WRAPPEE.md](docs/WRAPPEE.md) for API docs, quota info, and Google's own status page.

## What You Can Do

**How it runs**: a local stdio MCP server (spawned by Claude Desktop) plus an optional webapp
dashboard. All Google API calls happen directly from your machine using OAuth credentials you
control — no data passes through a fleet-operated server.

| Direction | Artifacts | Notes |
|-----------|-----------|-------|
| **Hands-in** | Doc titles/text, find/replace pairs, style directives, Drive queries | Natural-language prompts → tool calls |
| **Hands-out** | New/edited Google Docs, sharing links, comment threads | Live in the user's own Google Drive |

- Create, read, and edit Google Docs content (text, styles, tables, page breaks)
- Full find/replace and raw `batchUpdate` escape hatch for anything not wrapped explicitly
- Search, list, move, copy, rename, trash, and permanently delete Drive files
- Browse Drive folder structure with breadcrumbs, back up a whole folder to local files, and
  restore an existing doc's content from a local backup copy
- Export to PDF/DOCX/ODT/TXT/HTML/RTF natively, or bridge to a sibling libreoffice-mcp server
  for formats Drive's own export can't produce (legacy `.doc`, flat-XML `.fodt`)
- Keep a local folder two-way synced with a Drive folder on a polling interval — like OneDrive
  Desktop, with conflicts always preserved (never silently overwritten)
- Share documents and manage permissions by email + role
- Read, add, reply to, and resolve Drive comment threads
- Paginated listing for files, revisions, comments, and folder contents (cursor-based)
- Optional webapp dashboard: folder browser, backup/restore panel, sync configuration/status,
  onboarding wizard, and an in-chat Prefab UI status card for OAuth/sync/folder state

## Quick Install

```bash
git clone https://github.com/sandraschi/google-docs-mcp
cd google-docs-mcp
uv sync
```

Add to `claude_desktop_config.json` (see [INSTALL.md](INSTALL.md) for all options):

```json
{
  "mcpServers": {
    "google-docs-mcp": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\google-docs-mcp", "run", "google-docs-mcp"],
      "env": {
        "GOOGLE_DOCS_MCP_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_DOCS_MCP_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

**First time?** Complete [docs/ONBOARDING.md](docs/ONBOARDING.md) to create the Google Cloud
OAuth client before expecting live calls to work.

## Example Prompts

- "Create a Google Doc called 'Q3 Retro' and add a heading and three bullet points."
- "Find my 'Meeting Notes' doc and replace every '{{date}}' with today's date."
- "Share the 'Budget 2026' doc with sandra@example.com as a commenter."
- "List the last 10 documents I edited in Drive."
- "Back up everything in my 'Contracts' folder to C:/Backups/Contracts as Word docs."
- "Sync my 'Reports' Drive folder to a local folder and check every 10 minutes."
- "Convert my 'Old Contract' doc to legacy .doc format for a client who needs that."

## Documentation

| Doc | Contents |
|-----|----------|
| [Installation](INSTALL.md) | All install methods, prerequisites |
| [Onboarding](docs/ONBOARDING.md) | Google Cloud OAuth client setup, cost, pitfalls |
| [Wrapped APIs](docs/WRAPPEE.md) | Google Docs/Drive API links, quotas, status |
| [Architecture](docs/ARCHITECTURE.md) | System architecture, data flow, ports |
| [Configuration](docs/CONFIGURATION.md) | Env vars, config options |
| [Tool Reference](docs/TOOLS.md) | All available tools |
| [Development](docs/DEVELOPMENT.md) | Contributing, local setup |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues |

## Requirements

- Claude Desktop (or any MCP-compatible host)
- A Google account (free tier is sufficient — see [docs/ONBOARDING.md](docs/ONBOARDING.md))
- Python 3.11+ (installed automatically by `uv` if missing)

## License

MIT — see [LICENSE](LICENSE).
