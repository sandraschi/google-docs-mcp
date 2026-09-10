# Onboarding — google-docs-mcp

## What this is for

Lets Claude read and edit your Google Docs, and manage those files in Google Drive
(search, share, comment, trash) — directly, using your own Google account. It is not a
publishing bot: every write happens because you asked for it in the current conversation,
there is no autonomous scheduling or background posting.

## Cost and accounts (money / CC)

| Question | Answer |
|----------|--------|
| Do I need an account? | Yes — any Google account (personal Gmail or Workspace) |
| Free tier? | Yes — Docs/Drive API quotas are generous and free for personal use |
| Credit card required? | No, for the OAuth client and normal personal use |
| Ongoing cost? | Free at personal-use volumes. A Google Cloud **billing account is not required** to create the OAuth client used here — only for APIs that need billing enabled, which Docs/Drive do not |
| Who bills? | N/A (free tier) |

## Prerequisites outside this repo

- A Google account.
- A Google Cloud project with the **Google Docs API** and **Google Drive API** enabled.
- An **OAuth 2.0 Client ID** of type **Desktop app** (not Web application — this server runs
  a local loopback redirect, not a public web server).

## First-timer setup steps

1. Go to [console.cloud.google.com](https://console.cloud.google.com/) and create a project
   (or pick an existing one).
2. **APIs & Services → Library** — search for and **Enable**:
   - Google Docs API
   - Google Drive API
3. **APIs & Services → OAuth consent screen**:
   - User type: **External** (unless you have a Workspace org and want Internal).
   - Fill app name, your email as support contact. Scopes: none required here (the app
     requests them at runtime); add your own Google account under **Test users** if the
     consent screen stays in "Testing" publish status.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Desktop app**.
   - Name it anything (e.g. "google-docs-mcp").
   - Copy the generated **Client ID** and **Client Secret**.
5. Set them as environment variables (in `claude_desktop_config.json`'s `env` block, or a
   local `.env` — see [.env.example](../.env.example)):
   ```json
   "env": {
     "GOOGLE_DOCS_MCP_CLIENT_ID": "xxxxxxxx.apps.googleusercontent.com",
     "GOOGLE_DOCS_MCP_CLIENT_SECRET": "xxxxxxxx"
   }
   ```
6. Restart Claude Desktop, then ask Claude to call `google_docs_auth(operation="start_oauth")`.
   Your browser opens Google's consent screen — sign in, review the requested scopes
   (Docs + Drive), and accept. The token is cached to `data/token.json` (gitignored).

## Pitfalls (read before you click Publish)

- **"This app isn't verified"** warning: normal for a personal OAuth client in Testing
  status. Click **Advanced → Go to google-docs-mcp (unsafe)** — this is your own app, not
  a third party.
- **Testing-mode consent screens expire access after 7 days** unless your Google account is
  added under **Test users**, or you publish the consent screen (no Google review required
  for the scopes this server uses, since they're not "sensitive"/"restricted" in Google's
  classification... but Docs/Drive full-access scopes ARE sensitive and DO trigger a
  verification requirement if you publish to production with >100 users. For personal,
  single-user use, stay in Testing + add yourself as a test user — no review needed).
- **Wrong client type**: if you create a "Web application" OAuth client instead of "Desktop
  app", `start_oauth` will fail with a redirect URI mismatch. Delete it and create a Desktop
  app client instead.
- **`delete_permanently` is irreversible** — it bypasses Drive's trash entirely. Use `trash`
  unless you are certain.
- **Token file is plaintext** at `data/token.json` — same trust model as
  `claude_desktop_config.json` itself. Do not commit it (it's gitignored) or share it.

## Sanity check

- `google_docs_auth(operation="status")` returns `{"configured": true, "authenticated": true, ...}`.
- The Prefab status card (`show_google_docs_status_app`) shows a green "Connected" badge.
- `google_docs(operation="create", title="onboarding-test")` returns a real `document_id` and
  a `docs.google.com` URL that opens in your browser.

## Declared doubles

None in production code paths — every `google_docs`/`google_drive` operation either calls the
real Google API or returns an explicit `{"success": false, "error_type": "not_configured" |
"not_authenticated", ...}` before attempting any network call. The test suite (`tests/`) mocks
`googleapiclient.discovery.Resource` via `unittest.mock.MagicMock` — see
[docs/DEVELOPMENT.md](DEVELOPMENT.md) § Declared doubles.
