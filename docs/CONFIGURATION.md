# Configuration

## Environment Variables

| Variable | Default | Description |
|----------|---------|--------------|
| `GOOGLE_DOCS_MCP_CLIENT_ID` | *(none)* | OAuth 2.0 Desktop app client ID from Google Cloud Console. Required for any live API call. Most people never set this — see "Where OAuth credentials actually live" below. |
| `GOOGLE_DOCS_MCP_CLIENT_SECRET` | *(none)* | OAuth client secret paired with the above. |
| `GOOGLE_DOCS_MCP_DATA_DIR` | *(see below)* | Overrides the whole data directory (token, saved OAuth client, sync state) in one go. |
| `GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH` | `<data dir>/oauth_client.json` | Where the Settings-page/onboarding-wizard-saved OAuth client id/secret is written. |
| `GOOGLE_DOCS_MCP_TOKEN_PATH` | `<data dir>/token.json` | Where the cached OAuth token is written. Gitignored. |
| `GOOGLE_DOCS_MCP_SYNC_CONFIG_PATH` | `<data dir>/sync_config.json` | Local-folder-sync configuration (see `google_docs_sync` in docs/TOOLS.md). |
| `GOOGLE_DOCS_MCP_SYNC_MANIFEST_PATH` | `<data dir>/sync_manifest.json` | Local-folder-sync's per-doc tracking manifest. |
| `GOOGLE_DOCS_MCP_OAUTH_PORT` | `0` (OS picks) | Fixed local port for the OAuth loopback redirect. Only set this if your firewall requires a stable port. |
| `GOOGLE_DOCS_MCP_HOST` | `127.0.0.1` | Bind host for the optional webapp backend. |
| `GOOGLE_DOCS_MCP_PORT` | `11972` | Bind port for the webapp backend (frontend is the adjacent `11973`). Registered in `mcp-central-docs/operations/WEBAPP_PORTS.md`. |
| `GOOGLE_DOCS_MCP_PREFAB_APPS` | `1` | Set to `0` to skip registering Prefab App (`app=True`) tools — useful for headless CI. |
| `SERVER_API_URL` | `http://127.0.0.1:11972` | Reserved for a future HTTP-daemon + stdio-proxy pattern; unused today (see docs/ARCHITECTURE.md). |

## Where OAuth credentials actually live (not env vars, for most people)

You do **not** need to set `GOOGLE_DOCS_MCP_CLIENT_ID`/`_SECRET` or edit any config file by
hand. The **Settings page** in the webapp (and the Onboarding wizard) has a form to paste your
Client ID and Secret directly — it saves them to `oauth_client.json` in the app's data
directory. Env vars are only for people who already manage `claude_desktop_config.json` by
hand; when both are set, env vars win.

**"Data directory" resolves differently depending on how you're running this:**

| Running as | Data directory |
|---|---|
| `uv run google-docs-mcp` (dev, or Claude Desktop's stdio launch) | `<repo>/data/` |
| The packaged Tauri desktop app | `%LOCALAPPDATA%\com.sandraschi.google-docs-mcp\data\` |

The desktop-app case matters: a naive `<repo>/data` default would resolve inside PyInstaller's
per-launch temp extraction folder, which is deleted when the app closes — every saved OAuth
client and every auth token would vanish on the next launch. `data_dir()` in `config.py`
detects the frozen build (`sys.frozen`) and switches to the `%LOCALAPPDATA%` path instead,
matching where the Rust side already writes its own logs.

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
