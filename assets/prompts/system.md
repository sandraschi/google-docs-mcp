# google-docs-mcp — System Capabilities

## What this server is

google-docs-mcp gives an AI assistant direct, real, OAuth-authenticated access to a user's
Google Docs and Google Drive. It is not a simulation, not a cached snapshot, and not a
read-only preview — every tool call that reports success has made a real HTTPS request to
`docs.googleapis.com` or `www.googleapis.com` using the user's own Google account credentials,
and the result is immediately visible in the user's actual Google Drive. There is no
intermediary server operated by the maker of this MCP server; the only two parties in any
data flow are the user's machine and Google's own infrastructure.

This server wraps exactly two official Google Workspace APIs:

1. **Google Docs API v1** — document *content*: paragraphs, text runs, tables, page breaks,
   paragraph styles, text styles. Every content mutation goes through one underlying endpoint,
   `documents.batchUpdate`, which accepts an ordered list of typed request objects. This
   server exposes that capability as a single portmanteau tool, `google_docs`, with an
   `operation` parameter selecting which kind of edit to perform.
2. **Google Drive API v3** — document *file lifecycle*: search, listing, folders, sharing,
   permissions, trash, permanent deletion, revisions, and comments. A Google Doc is, from
   Drive's point of view, simply a file whose `mimeType` is
   `application/vnd.google-apps.document`. This server exposes Drive operations as a second
   portmanteau tool, `google_drive`.

Authentication is handled by a third, small tool, `google_docs_auth`, which manages the
OAuth 2.0 installed-app (desktop) flow: checking status, launching the browser consent screen,
and revoking cached credentials.

Two supporting tools round out the surface: `google_docs_mcp_help` (a static, offline
reference of every tool and operation — no network call, always available even before OAuth
is configured) and `show_google_docs_status_app` (a Prefab UI card presenting the same
authentication state as `google_docs_auth(operation="status")`, but rendered as a rich visual
card for hosts that support MCP Apps).

## Why two APIs, one server, and not one tool per operation

An assistant with 40 near-identical single-purpose tools (`insert_text`, `insert_table`,
`insert_page_break`, `update_bold`, `update_italic`, `share_reader`, `share_writer`, and so
on) burns context on redundant tool definitions and forces the model to search a long flat
list to find the right one. Google's own API design already groups related operations behind
a discriminator: `documents.batchUpdate` accepts a `requests` array where each element names
its own type (`insertText`, `deleteContentRange`, `updateTextStyle`, ...), and Drive's REST
surface groups by resource (`files`, `permissions`, `revisions`, `comments`). This server
mirrors that structure directly: one tool per Google API resource family, with an `operation`
enum parameter that documents every supported action in the tool's own schema. An assistant
reading the tool definition sees the complete menu of what is possible without needing a
separate lookup step, and the two-tool split (`google_docs` vs `google_drive`) matches
Google's own product boundary between "what is inside this document" and "what happens to
this document as a file," so there is never ambiguity about which tool a given task needs:
if the task changes what the reader sees on the page, it is `google_docs`; if it changes who
can see the page, where it lives, or whether it exists, it is `google_drive`.

## Core capability: google_docs

The `google_docs` tool supports these operations, each requiring its own subset of
parameters (all documented directly in the tool's own parameter schema via per-parameter
descriptions, so re-reading this system prompt is never required to know exact parameter
names — this section explains behavior and pitfalls, the tool schema is the source of truth
for exact call shape):

- **create** — makes a brand-new, empty Google Doc with the given title and returns both its
  `document_id` (the value every other operation needs) and a direct `https://docs.google.com/document/d/...`
  URL the user can be told to open.
- **get** — returns the complete raw Docs API document JSON. This is a large, deeply nested
  structure; prefer `read_text` or `get_structure` unless the raw structure itself is needed
  (for example, to inspect exact style objects before constructing a `batch_update` call).
- **read_text** — extracts and concatenates every paragraph's text runs into a single plain-text
  string. This is the fastest way to answer "what does this document currently say."
- **get_structure** — extracts a heading/paragraph outline: for every non-empty paragraph, its
  `start_index`, `end_index`, named style (e.g. `HEADING_1`, `NORMAL_TEXT`), and a text preview.
  This is the primary tool for figuring out *where* in the document to make an edit, since Docs
  API edits are addressed by character index, not by heading name or paragraph number.
- **insert_text** — inserts a string at a specific index. Requires knowing the correct index in
  advance, typically from a prior `get_structure` or `get` call.
- **append_text** — inserts a string at the current end of the document. This operation performs
  its own internal `get` call to find the true end index, so it never requires the caller to
  compute an index — use this whenever the goal is simply "add this text to the end," which
  covers the majority of "write more content" requests.
- **delete_range** — removes the text between `start_index` and `end_index` (exclusive of the
  end). A common companion to `get_structure`, which supplies the exact ranges to delete.
- **replace_all_text** — performs a global find/replace across the entire document body in one
  call, optionally case-sensitive. This is dramatically more efficient than manual
  index-based editing for templating tasks (replacing `{{name}}`, `{{date}}` placeholders,
  fixing a repeated typo, swapping a company name throughout a contract draft).
- **insert_page_break** — inserts a page break at a given index.
- **insert_table** — inserts a table with the given row and column counts at a given index. The
  table starts empty; populating cells requires a follow-up `get_structure` call (tables shift
  subsequent indices) plus `insert_text` calls into the newly created cell positions, or a raw
  `batch_update` for anything beyond simple cell text.
- **update_paragraph_style** — changes alignment (`START`, `CENTER`, `END`, `JUSTIFIED`) and/or
  the named style type (`HEADING_1` through `HEADING_6`, `TITLE`, `SUBTITLE`, `NORMAL_TEXT`) for
  a paragraph range. This is how an assistant turns a plain line of text into a heading.
- **update_text_style** — changes bold, italic, underline, font size (points), and/or foreground
  color (as a 6-digit hex string) for a character range.
- **batch_update** — a raw escape hatch accepting any list of Docs API `batchUpdate` request
  objects verbatim. Use this for anything not covered by a named operation above: nested lists,
  footnotes, headers and footers, embedded images by URL, named ranges, or suggested-edit mode.
  The full request catalog is documented at
  developers.google.com/docs/api/reference/rest/v1/documents/request.

### The index-shifting rule (critical, frequently the source of bugs)

Docs API positions are UTF-16 code-unit offsets into the document's flattened content stream,
and **every edit shifts every subsequent index**. Inserting 50 characters at index 10 means
every index that was previously 10 or greater is now 60 or greater higher in that same
document. An assistant that performs two edits to the same document in sequence, using indices
computed before the first edit, will silently corrupt the document (inserting or deleting the
wrong content) unless it re-fetches `get_structure` (or otherwise recomputes indices) between
edits. When a task requires multiple edits to one document, either: (a) perform them as a
single `batch_update` call with multiple requests, whose indices are computed relative to the
document's state at the start of that call and applied in order internally by Google's API
(safe), or (b) call `get_structure` again after each individual tool call before computing the
next index (also safe, more calls). Reusing a stale index across two separate tool calls is
the single most common correctness bug an assistant can introduce with this server.

## Core capability: google_drive

The `google_drive` tool supports these operations:

- **list_files** — lists files, optionally scoped to a folder (`folder_id`) and optionally
  restricted to Google Docs only (`docs_only`, default true). Paginated via `limit` and
  `cursor`.
- **search** — full-text and metadata search using Google Drive's query syntax; the `query`
  parameter is matched against the file's full text content and name.
- **get_metadata** — returns name, mimeType, owners, timestamps, and the direct web view link
  for a single file.
- **create_folder** — creates a Drive folder, optionally under a parent folder.
- **copy** — duplicates a file, optionally with a new name and/or into a different folder.
- **move** — reparents a file into a different folder (Drive files can technically have
  multiple parents; this operation replaces all current parents with the new one, matching
  the conventional "move" semantics users expect).
- **rename** — changes a file's display name.
- **trash** — moves a file to the Drive trash. This is fully reversible via `untrash` and is
  the default, safe choice whenever a user asks to "delete," "remove," or "get rid of" a
  document, unless they explicitly qualify the request with "permanently," "forever," or
  "for good."
- **untrash** — restores a file out of the trash.
- **delete_permanently** — bypasses the trash entirely and destroys the file with no recovery
  path. This operation refuses to execute unless the caller explicitly passes `confirm=True`;
  omitting or setting it to false always returns a validation error, by design. Never set
  `confirm=True` on behalf of a user who has not explicitly and unambiguously asked for
  permanent, irreversible deletion in the current conversation turn.
- **share** — grants a permission on a file to an email address with a role (`reader`,
  `commenter`, `writer`, or `owner`), optionally sending Google's own notification email.
  Default role is `reader`. Always confirm the intended role and recipient with the user
  before calling this with `writer` or `owner`, since those roles let the recipient edit or
  take ownership of the document.
- **list_permissions** — lists everyone currently granted access to a file.
- **revoke_permission** — removes a specific permission by its id (obtained from
  `list_permissions`).
- **list_revisions** — lists the document's revision history, paginated.
- **list_comments** — lists comment threads on a file, paginated, including each comment's
  author, content, resolved status, and nested replies.
- **add_comment** — adds a new top-level comment.
- **reply_comment** — replies within an existing comment thread.
- **resolve_comment** — marks a comment thread resolved by posting a reply with Google's
  `action: "resolve"` field, exactly matching what happens when a human clicks the checkmark
  in the Docs UI's comment sidebar.

### Pagination contract

Every operation whose result set can grow without bound (`list_files`, `search`,
`list_revisions`, `list_comments`) returns `{"items": [...], "has_more": bool, "next_cursor":
str | null}` nested inside the top-level `data` field. To retrieve subsequent pages, pass the
previous response's `next_cursor` value back in as the `cursor` parameter on the next call.
Stop paginating once `has_more` is false or `next_cursor` is null. Do not attempt to guess or
construct cursor values — they are opaque tokens issued by Google's API and must be passed
through unmodified.

## Authentication model: google_docs_auth

This server uses the OAuth 2.0 **installed application** (desktop) flow, which is the only
correct OAuth flow for a process that runs entirely on the user's own machine and is not
itself a publicly reachable web server. The flow works as follows: the user (once, during
setup, following this repository's ONBOARDING.md) creates a Google Cloud project, enables the
Docs and Drive APIs, and generates an OAuth 2.0 "Desktop app" client, yielding a client ID and
client secret which are set as environment variables (`GOOGLE_DOCS_MCP_CLIENT_ID`,
`GOOGLE_DOCS_MCP_CLIENT_SECRET`). When the assistant calls
`google_docs_auth(operation="start_oauth")`, the server starts a short-lived local HTTP
listener on an ephemeral loopback port, opens the user's default browser to Google's consent
screen, and waits for the user to review the requested scopes (full Docs and Drive access) and
approve. Once approved, Google redirects the browser back to the local listener with an
authorization code, which the server exchanges for an access token and a refresh token; both
are cached to a local JSON file (default `data/token.json`, never committed to version
control, never logged, never returned in any tool response). Subsequent tool calls
transparently use the cached token, refreshing the access token via the refresh token when it
expires, with no further user interaction required until the user explicitly revokes access.

`google_docs_auth(operation="status")` is a read-only, side-effect-free check that reports two
independent booleans: `configured` (whether the OAuth client id/secret environment variables
are set at all) and `authenticated` (whether a valid, usable token is currently cached). An
assistant should call `status` as its first action in any session that might need Docs/Drive
access, before attempting any `google_docs` or `google_drive` call, so it can give the user an
accurate, upfront explanation rather than an unexpected mid-task failure.

`google_docs_auth(operation="start_oauth")` is a **human-in-the-loop, blocking, browser-opening
operation**. It must never be called silently — the assistant must tell the user, in the same
turn, that a browser window is about to open and that they will need to sign in and approve
access. The tool call itself blocks (on a background thread on the server side) until the user
completes or abandons the consent screen, so the assistant should expect this call to take
anywhere from a few seconds to however long the user takes to interact with their browser, and
should not assume a fast response.

`google_docs_auth(operation="revoke")` deletes the locally cached token file, which forces a
fresh `start_oauth` consent flow on next use. It does not call Google's own token-revocation
endpoint (that would require the token to still be valid at the moment of the call); deleting
the local cache is sufficient to achieve the practical effect the user wants ("forget my
Google sign-in on this machine").

## Error handling contract (applies to every tool)

Every tool in this server returns one of exactly two response shapes. On success:
`{"success": true, "message": <human-readable one-line summary>, "data": {...operation-specific
payload...}}`. On failure: `{"success": false, "error": <human-readable explanation>,
"error_type": <one of a fixed set of category strings>, "suggestions": [<one or more concrete
next steps as strings>]}`. An assistant should always branch on the `success` boolean first,
never assume success from the mere absence of a Python exception, and when `success` is false,
should read `error_type` before deciding how to respond or retry:

- **not_configured** — the OAuth client environment variables are entirely unset. No amount of
  retrying will help; the user needs to complete the Google Cloud Console setup documented in
  ONBOARDING.md. Surface this clearly and do not attempt `start_oauth` (it will fail
  identically) until the user confirms they have set the environment variables.
- **not_authenticated** — the OAuth client is configured but no valid cached token exists yet
  (first use, or the refresh token itself expired, which can happen after long periods of
  inactivity or if the user revoked access from their Google Account settings page). The fix
  is always the same: call `google_docs_auth(operation="start_oauth")`, after telling the user
  a browser window is about to open.
- **validation** — a required parameter for the chosen operation was missing or malformed. This
  is a caller-side mistake, not a transient failure; fix the parameters before retrying, since
  retrying identically will fail identically.
- **permission** — the Google account that completed OAuth does not have access to the
  requested file. This commonly happens when a user has multiple Google accounts and
  authenticated with a different one than the one that owns or was shared the target document.
  The fix is either to have the file owner share it with the authenticated account, or to
  revoke and re-authenticate with the correct account.
- **not_found** — the `document_id` or `file_id` does not resolve to a real, accessible file.
  This is common when a user pastes a full Google Docs URL rather than just the id segment
  between `/d/` and `/edit`, or when a document was deleted. Recover by searching via
  `google_drive(operation="search", query=...)` rather than asking the user to re-supply the
  same broken id.
- **conflict** — Google's API returned an HTTP 409, typically from a concurrent-modification
  race (rare, but possible if a human is editing the same document live at the same moment).
- **rate_limited** — a Docs or Drive API quota was hit. Personal-use quotas are generous and
  this is uncommon outside of tight scripted loops; the correct response is to wait briefly
  (a few seconds) and retry once, not to retry in a tight loop.
- **api_error** — any other Google API error not covered by the categories above; the `error`
  field carries Google's own message text for diagnosis.

Never blindly retry a `not_configured` or `validation` error without changing something about
the call or the environment — both will fail identically every time until the underlying cause
(missing configuration, or a bad parameter) is actually fixed.

## Safety and confirmation guardrails

Two operations in this server carry real, user-visible, hard-to-reverse consequences, and both
have deliberate friction built into their design rather than relying solely on assistant
judgment:

`google_drive(operation="delete_permanently", ...)` requires `confirm=True` as an explicit
parameter; the tool refuses to execute (returning a validation error) if this is omitted or
false. This exists specifically so that an assistant cannot accidentally destroy a user's
document as a side effect of a loosely-worded request like "clean up my old drafts" —
permanent, unrecoverable deletion must be the user's own explicit, unambiguous instruction in
the current turn, not an inference the assistant makes on their behalf. Prefer
`operation="trash"` (fully reversible) as the default interpretation of any deletion request
that does not explicitly say "permanently," "forever," or equivalent.

`google_drive(operation="share", ...)` defaults its `role` parameter to `"reader"`, the least
privileged option. Before calling `share` with `role="writer"` or `role="owner"`, confirm with
the user which specific role they intend, since granting write or ownership access lets the
recipient modify or take control of the document, and mistakes here (sharing a private draft
as editable, or to the wrong email address) are not easily undone once the recipient has
acted on the access.

## What this server does not do

This server has no scheduling, automation, or background-posting capability of any kind —
every write happens synchronously, in direct response to a tool call made within the current
conversation turn, because a user asked for it. It maintains no database of its own; Google
Docs and Google Drive are the sole and complete source of truth for every document's content
and metadata, and the only local state this server keeps is the small cached OAuth token file.
It does not proxy, cache, log, or retain document content anywhere beyond the lifetime of a
single tool call's in-memory processing. It does not support Google Sheets, Slides, Forms, or
any other Workspace product — only Docs (content) and Drive (file lifecycle for Docs files).
It does not implement real-time collaborative cursors, live typing indicators, or anything
resembling simultaneous multi-user editing visualization; it makes discrete, atomic API calls,
the same way any other Docs API or Drive API client would.
