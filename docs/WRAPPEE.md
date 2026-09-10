# Wrapped APIs — Google Docs & Google Drive

This server wraps two official Google Workspace APIs directly — there is no intermediary
service, and no ambiguity with a similarly-named product (unlike e.g. Overte/Vircadia).

## Google Docs API

- **Official docs**: https://developers.google.com/docs/api
- **What it covers**: document content — paragraphs, text runs, tables, styles, structural
  edits — all via one `documents.batchUpdate` endpoint taking typed request objects.
- **What it does NOT cover**: file metadata, sharing, comments, trash. That's Drive API.
- **Console**: https://console.cloud.google.com/apis/library/docs.googleapis.com
- **Status page**: https://www.google.com/appsstatus/dashboard/ (Google Workspace status)
- **Community / support**: https://stackoverflow.com/questions/tagged/google-docs-api and the
  Google Workspace Developer forum (https://developers.google.com/workspace/support).

## Google Drive API (v3)

- **Official docs**: https://developers.google.com/drive/api/guides/about-sdk
- **What it covers**: files as objects — listing, search, folders, permissions/sharing,
  revisions, comments, trash/delete.
- **Console**: https://console.cloud.google.com/apis/library/drive.googleapis.com
- **Community / support**: same Workspace developer forum as above.

## Quotas (personal use)

Both APIs have generous default quotas for personal OAuth clients (thousands of requests per
minute per project). You will not hit them through normal Claude Desktop usage; heavy
scripted loops might — see `docs/TROUBLESHOOTING.md` § Rate limited.

## Why two APIs, one MCP server

Google split "document content" (Docs API) from "file object" (Drive API) at the product
level decades before either had a public API — a Google Doc IS a Drive file with a special
mimeType. This repo mirrors that split as two portmanteau tools (`google_docs`, `google_drive`)
rather than papering over it, so the tool surface matches Google's own API boundary and its
documentation.
