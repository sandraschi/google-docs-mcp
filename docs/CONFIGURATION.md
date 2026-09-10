# Configuration

## Environment Variables

| Variable | Default | Description |
|----------|---------|--------------|
| `GOOGLE_DOCS_MCP_CLIENT_ID` | *(none)* | OAuth 2.0 Desktop app client ID from Google Cloud Console. Required for any live API call. |
| `GOOGLE_DOCS_MCP_CLIENT_SECRET` | *(none)* | OAuth client secret paired with the above. |
| `GOOGLE_DOCS_MCP_TOKEN_PATH` | `<repo>/data/token.json` | Where the cached OAuth token is written. Gitignored. |
| `GOOGLE_DOCS_MCP_OAUTH_PORT` | `0` (OS picks) | Fixed local port for the OAuth loopback redirect. Only set this if your firewall requires a stable port. |
| `GOOGLE_DOCS_MCP_HOST` | `127.0.0.1` | Bind host for the optional webapp backend. |
| `GOOGLE_DOCS_MCP_PORT` | `11972` | Bind port for the webapp backend (frontend is the adjacent `11973`). Registered in `mcp-central-docs/operations/WEBAPP_PORTS.md`. |
| `GOOGLE_DOCS_MCP_PREFAB_APPS` | `1` | Set to `0` to skip registering Prefab App (`app=True`) tools — useful for headless CI. |
| `SERVER_API_URL` | `http://127.0.0.1:11972` | Reserved for a future HTTP-daemon + stdio-proxy pattern; unused today (see docs/ARCHITECTURE.md). |

## Setting Variables

In `claude_desktop_config.json`:

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

For local development, copy [.env.example](../.env.example) to `.env` and fill in the two
OAuth values — `start.ps1` loads it automatically.
