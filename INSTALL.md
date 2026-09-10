# Installing google-docs-mcp

> **First time?** Complete [docs/ONBOARDING.md](docs/ONBOARDING.md) before expecting live
> Google Docs/Drive calls to work — you need a Google Cloud OAuth client first.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| Claude Desktop | Required host | [download](https://claude.ai/download) |
| Git | Clone repo (Option C/D only) | `winget install Git.Git` |
| Python + uv | Run server (Option C/D only) | `winget install astral-sh.uv` |
| Node.js | mcpb CLI (Option B only) | `winget install OpenJS.NodeJS.LTS` |

> Windows: all installs via [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/)
> macOS: use `brew install` equivalents
> Linux: use your distro package manager

## Option A — Drag and Drop (Recommended)

1. Go to [Releases](https://github.com/sandraschi/google-docs-mcp/releases/latest)
2. Download `google-docs-mcp-{version}.mcpb`
3. Open Claude Desktop → drag the file onto the window
   *Or*: Settings → MCP Servers → Install from file
4. When prompted, enter your `GOOGLE_DOCS_MCP_CLIENT_ID` / `GOOGLE_DOCS_MCP_CLIENT_SECRET`
   (see [docs/ONBOARDING.md](docs/ONBOARDING.md) if you don't have these yet)

## Option B — mcpb CLI

```bash
# Requires Node.js (see Prerequisites)
npx @anthropic-ai/mcpb install https://github.com/sandraschi/google-docs-mcp
```

## Option C — Manual Configuration

1. Clone: `git clone https://github.com/sandraschi/google-docs-mcp`
2. Install deps: `cd google-docs-mcp && uv sync`
3. Add to Claude Desktop config:

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

Config file location:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

4. Restart Claude Desktop

## Option D — Developer Mode

For contributing or running from source with live reload — see
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Verify Installation

After installing and completing [docs/ONBOARDING.md](docs/ONBOARDING.md), open Claude
Desktop and type:

> "Check my Google Docs auth status."

You should see a Prefab card reporting `configured: true, authenticated: true` (or a clear
prompt to run `start_oauth` if you haven't yet).

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues.
