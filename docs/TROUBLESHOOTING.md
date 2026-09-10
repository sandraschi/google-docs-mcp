# Troubleshooting

## Server doesn't appear in Claude Desktop
**Cause**: Config JSON is malformed.
**Fix**: Validate at jsonlint.com, check for trailing commas.

## "command not found: uv"
**Cause**: uv not installed or not in PATH.
**Fix**: `winget install astral-sh.uv` then restart your terminal.

## Every tool call returns `error_type: "not_configured"`
**Cause**: `GOOGLE_DOCS_MCP_CLIENT_ID` / `GOOGLE_DOCS_MCP_CLIENT_SECRET` are not set (and no
`data/oauth_client.json` from the onboarding wizard either).
**Fix**: Follow `docs/ONBOARDING.md` to create a Google Cloud OAuth client (Desktop app
type), then either set both env vars in `claude_desktop_config.json`, **or** open the webapp's
Onboarding page (`/onboarding`) and paste the client id/secret into the Connect step.

## Every tool call returns `error_type: "not_authenticated"`
**Cause**: OAuth client is configured but no valid token is cached yet (or it expired and
has no refresh token).
**Fix**: Call `google_docs_auth(operation="start_oauth")` and complete the browser consent.

## `start_oauth` opens the browser but nothing happens after consenting
**Cause**: Usually a firewall blocking the loopback redirect, or a stale browser tab from a
previous attempt.
**Fix**: Close other `start_oauth` browser tabs, retry. If a firewall is involved, set a fixed
`GOOGLE_DOCS_MCP_OAUTH_PORT` and allow that port through the firewall.

## "This app isn't verified" warning during consent
**Cause**: Normal for a personal OAuth client in "Testing" publish status.
**Fix**: Click **Advanced → Go to google-docs-mcp (unsafe)**. This is your own Cloud project,
not a third party — see `docs/ONBOARDING.md` § Pitfalls.

## `error_type: "permission"` on a document you know exists
**Cause**: The signed-in Google account (the one that completed `start_oauth`) doesn't have
access to that file.
**Fix**: Confirm which Google account you authenticated with (`google_docs_auth(operation="status")`
doesn't show the email — check the consent screen you approved). Ask the file owner to share it
with that account.

## `error_type: "not_found"` with a document_id you copied from a URL
**Cause**: Google Docs URLs are `https://docs.google.com/document/d/<ID>/edit` — make sure you
copied only the `<ID>` segment, not the whole URL or trailing `/edit`.
**Fix**: Use `google_drive(operation="search", query="...")` to find the correct id instead of
hand-copying from a URL.

## Wrong OAuth client type ("redirect_uri_mismatch")
**Cause**: The Google Cloud OAuth client was created as "Web application" instead of "Desktop app".
**Fix**: Delete it in Cloud Console → Credentials, create a new **Desktop app** client, update
your env vars.

## Rate limited (`error_type: "rate_limited"`)
**Cause**: Docs/Drive API per-minute quota hit (rare at personal-use volumes, common if
scripting many calls in a tight loop).
**Fix**: Wait a few seconds and retry. Check quotas at Cloud Console → APIs & Services →
Google Docs API / Google Drive API → Quotas.
