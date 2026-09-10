# Using google-docs-mcp — Natural Language Guide

This guide walks through everything a person actually does with google-docs-mcp, told as
conversations and workflows rather than API reference. If you're looking for exact parameter
names, see `docs/TOOLS.md` in the repository or ask Claude to call
`google_docs_mcp_help()`. This document is about *how to think* about using the server —
what to say, what to expect, and what tends to trip people up the first time.

## Getting started: the very first thing to do

Before this server can touch a single document, you need a Google Cloud OAuth client. This
sounds intimidating but is a five-minute, free, one-time setup. Full step-by-step instructions
live in `docs/ONBOARDING.md`, but the short version is: go to Google Cloud Console, create a
project, enable the Google Docs API and Google Drive API, create an OAuth 2.0 client of type
"Desktop app," and copy the client ID and secret into your Claude Desktop configuration as
`GOOGLE_DOCS_MCP_CLIENT_ID` and `GOOGLE_DOCS_MCP_CLIENT_SECRET`.

Once those are set and Claude Desktop has been restarted, the very first thing to say to
Claude is something like:

> "Check my Google Docs connection status."

Claude will call `google_docs_auth(operation="status")` and tell you whether the OAuth client
is configured and whether you're authenticated. If you're configured but not yet
authenticated, say:

> "Connect my Google account."

This triggers `google_docs_auth(operation="start_oauth")`, which opens your default browser to
Google's real sign-in and consent screen. Sign in with whichever Google account owns (or has
access to) the documents you want to work with — if you have multiple Google accounts, this
matters, since Claude will only be able to see and edit documents visible to whichever account
you approve here. Review the requested permissions (they'll mention Google Docs and Google
Drive access) and click Allow. Your browser will show a confirmation page, and Claude will
report back that you're now authenticated. This only needs to happen once per machine, unless
you later revoke access or your refresh token expires from long inactivity.

## Creating your first document

The simplest possible request:

> "Create a new Google Doc called 'Meeting Notes'."

Claude calls `google_docs(operation="create", title="Meeting Notes")`, which returns both a
document id (an internal identifier you'll rarely need to see directly) and a real,
clickable `https://docs.google.com/document/d/.../edit` link. Claude will typically show you
that link so you can open the document in your browser and watch it fill in as you continue
the conversation.

A slightly richer request:

> "Create a doc called 'Q3 Retro' with a heading and three bullet points about what went well,
> what didn't, and what we'll change next quarter."

This takes a few tool calls under the hood: `create`, then `append_text` for the heading text,
then `update_paragraph_style` to make that first line an actual Heading 1 (not just bold
text — a real Google Docs heading style, the same as clicking the paragraph style dropdown in
the Docs UI), then more `append_text` calls for the bullet content. You don't need to know or
specify any of this — just describe the document you want and let Claude sequence the calls.

## Editing an existing document

If you don't already know a document's id, just describe it:

> "Find my 'Meeting Notes' doc and add a line about the budget approval."

Claude searches Drive by name/content (`google_drive(operation="search", query="Meeting
Notes")`), picks the matching file, and then appends your requested text
(`google_docs(operation="append_text", ...)`). If multiple documents match, Claude should ask
which one you mean rather than guessing.

Adding to the end of a document is the easiest and safest kind of edit — `append_text`
automatically finds the true end of the document, so there's no risk of it landing in the
wrong place even if the document has been edited elsewhere since you last looked at it.

Editing in the *middle* of a document — inserting a paragraph between two existing ones,
fixing a specific sentence, restyling a particular heading — requires Claude to first look at
the document's structure to find the right position:

> "In my 'Project Plan' doc, change the second heading from 'Timeline' to 'Timeline & Milestones'."

Claude will call `get_structure` to find where "Timeline" starts and ends, then either
`replace_all_text` (simplest, if the text is unique in the document) or a targeted
`delete_range` + `insert_text` pair using the exact indices from the structure call.

## Find and replace across a whole document

This is one of the most useful bulk operations, and it's a single tool call regardless of how
many times the text appears:

> "In my 'Contract Template' doc, replace every instance of '[CLIENT NAME]' with 'Acme Corp'."

> "Fix the typo — I keep writing 'recieve' instead of 'receive' throughout the whole document."

> "Replace all the '{{date}}' placeholders in my invoice template with today's date."

Each of these becomes a single `replace_all_text` call. Claude will tell you how many
occurrences were actually changed, so you can sanity-check that the count matches what you
expected (if you expected 5 placeholder replacements and it reports 0, the exact text probably
doesn't match — case sensitivity or extra whitespace are common culprits).

## Formatting and styling

> "Make the first paragraph bold and centered."

> "Turn 'Introduction' into a Heading 2."

> "Make the word 'URGENT' in my email draft red and bold."

Each of these maps to `update_text_style` (bold, italic, underline, font size, foreground
color by hex) or `update_paragraph_style` (alignment, heading level). Claude needs to know the
exact character range to style, which it gets from `get_structure` or by finding the text via
`read_text` first. If your instruction is ambiguous about exactly which text to style ("make
it bold" when there are three candidate paragraphs), Claude should ask which one you mean
rather than guessing and styling the wrong thing.

## Working with tables

> "Add a 3x4 table to the end of my 'Budget' doc for listing expense categories."

This calls `insert_table` with rows=3, columns=4. Tables start empty — if you also want
content in specific cells, say so explicitly ("...and put 'Category', 'Budgeted', 'Actual',
'Variance' as the header row") and Claude will follow up with additional edits to populate
those cells, re-checking the document structure first since inserting the table shifted
everything after it.

## Organizing files in Drive

> "List the Google Docs I've edited most recently."

> "Search my Drive for anything mentioning 'quarterly budget'."

> "Move my 'Draft Proposal' doc into my 'Client X' folder."

> "Make a new folder called 'Archive 2026' and put last year's reports in it."

> "Rename 'Untitled document' to 'Vendor Agreement — DRAFT'."

These are all `google_drive` operations — `list_files`, `search`, `move`, `create_folder`,
`rename` respectively. Search and list are paginated; if you have a lot of matching
documents, Claude will show you the first batch (25 by default) and can fetch more if you ask
for "the next page" or "show me more."

## Sharing documents

> "Share my 'Proposal' doc with sandra@example.com so she can comment."

> "Give teammate@example.com edit access to the 'Team Roadmap' doc."

> "Who currently has access to my 'Salary Review' doc?"

Sharing maps to `google_drive(operation="share", ...)` with a role of `reader`, `commenter`,
or `writer`. Claude should always confirm the role before sharing with `writer` access, since
that lets the recipient actually change the document. "Who has access" maps to
`list_permissions`, useful for auditing who can see a sensitive document before you forget
you shared it with someone months ago.

## Deleting things — the safe way and the permanent way

> "Delete my old 'Scratch Notes' doc."

By default, this should move the file to trash — fully reversible, exactly like deleting a
file on your computer normally works (it goes to the Recycle Bin / Trash, not gone forever).
If you actually want it gone permanently, with no way to recover it, say so explicitly:

> "Permanently delete my old 'Scratch Notes' doc — I don't need to recover it, ever."

Only this explicit, unambiguous phrasing should trigger `delete_permanently`, and even then
Claude has to pass `confirm=True` as a deliberate extra step — the tool itself refuses to run
without it, specifically to prevent an assistant from ever destroying a document by
misreading an ambiguous "delete this" as "delete this forever."

If you change your mind about a trashed document:

> "Actually, restore that 'Scratch Notes' doc I just trashed."

That's `untrash` — instant, no data lost.

## Comments and collaboration

> "What comments are on my 'Draft Proposal' doc?"

> "Add a comment on my 'Budget' doc saying the Q2 numbers need a second look."

> "Reply to that comment thread from Sarah saying I've updated the figures."

> "Mark that comment as resolved."

These map to `list_comments`, `add_comment`, `reply_comment`, and `resolve_comment`
respectively. Resolving a comment through this server behaves exactly like clicking the
checkmark in the Google Docs comment sidebar — the thread is marked resolved, not deleted, so
the history remains visible if anyone reopens it later.

## Checking document revision history

> "Show me the recent revision history for my 'Contract' doc."

Useful when you want to know when a document last changed, or by roughly how much, before
diving into a detailed diff (which this server doesn't do directly — Google's own revision
history UI, reachable from the document's File menu, is the tool for detailed version
comparison; this server surfaces the list so you know a revision exists and roughly when).

## Advanced: raw batchUpdate for anything not covered above

If you ask for something the named operations don't directly support — nested bullet lists
with specific indentation levels, a header or footer, an inline image inserted from a URL, a
named range for later reference, or Google Docs' "suggesting" (track-changes) edit mode —
Claude can construct a raw `batch_update` call using Google's own Docs API request format.
This is a power-user escape hatch; you don't need to know the JSON shape yourself, just
describe what you want in enough detail:

> "Add a footer to my 'Report' doc that says 'Confidential — Internal Use Only' on every page."

> "Insert this image [URL] right after the introduction paragraph."

> "Make my edit suggestions instead of direct changes, like Google Docs' 'Suggesting' mode."

Claude will look up the appropriate Docs API request shape for these and issue it via
`batch_update`.

## Common things that go wrong, and what they mean

**"Not configured" on every request** — the Google Cloud OAuth client hasn't been set up yet,
or the environment variables aren't reaching the server. Walk through `docs/ONBOARDING.md`
from the start; there's no way around this step, since Google requires every application
(including this one) to have its own registered OAuth client.

**"Not authenticated" after previously working fine** — your cached sign-in expired, most
often from weeks of inactivity, or you revoked access from your Google Account's own
"Third-party apps" settings page. Just say "connect my Google account again" and go through
the browser consent screen once more.

**"This app isn't verified" warning during sign-in** — completely normal and expected for a
personal OAuth client that hasn't gone through Google's (optional, paid-tier-adjacent)
verification process. This is *your own* Google Cloud project, not a third party's; click
"Advanced" and then "Go to google-docs-mcp (unsafe)" to proceed. "Unsafe" here just means
"unverified by Google," not "actually dangerous" — you created this client yourself.

**A document isn't found even though you can see it in Drive** — double-check you didn't
paste a full URL as the document id. Google Docs URLs look like
`https://docs.google.com/document/d/1AbCdEfG.../edit`; the id is only the segment between
`/d/` and `/edit`. It's usually easier to just ask Claude to search by name instead of copying
ids manually.

**Edits landing in the wrong place** — this happens if two edits to the same document are
made using indices computed before an earlier edit already shifted everything. If you notice
misplaced content after a multi-step editing request, ask Claude to re-check the document
structure and fix the specific paragraph — it's a straightforward, recoverable fix, not
data loss (nothing outside the intended edit range is touched).

**Sharing with the wrong role** — if you accidentally granted "writer" instead of "reader,"
just ask Claude to check current permissions and revoke or downgrade the specific grant; Drive
sharing changes are immediate but always fully reversible by removing or re-adding the
permission.

## A note on privacy and trust

Every single tool call this server makes is a direct request from your own machine to
Google's servers, authenticated as *you*, using credentials only you control (an OAuth token
cached in a local file that never leaves your machine and is never sent anywhere except
directly to Google's own token-refresh endpoint). Nothing about your document content, your
Drive structure, or your account passes through any server operated by the people who built
this MCP server. If you revoke access (from Google's Account settings, or by asking Claude to
run `google_docs_auth(operation="revoke")`), the local cached token is deleted and no further
access is possible until you sign in again.

## Quick reference: what to say for common tasks

- "What's my Google Docs connection status?" → check auth
- "Connect my Google account" → start OAuth
- "Create a doc called X" → new document
- "Find my X doc" / "Search my Drive for X" → locate a document
- "What does my X doc currently say?" → read content
- "Add [text] to the end of my X doc" → append
- "Replace every X with Y in my Z doc" → find/replace
- "Make [text] bold/italic/a heading" → style
- "Add a table to my X doc" → insert table
- "Share my X doc with [email] as [role]" → grant access
- "Who can see my X doc?" → list permissions
- "Delete my X doc" (reversible) vs "permanently delete" (irreversible, requires explicit
  confirmation) → trash vs delete_permanently
- "What comments are on my X doc?" / "Comment on my X doc" / "Resolve that comment" →
  comment thread management
- "Show recent changes to my X doc" → revision history

This server rewards being specific about *which* document you mean and *what* change you
want, but it's built to handle ordinary, conversational requests — you're describing an
outcome, not writing code, and Claude handles the translation into the exact sequence of API
calls needed to get there.

## A worked example: building a document from nothing

It helps to see a full, realistic conversation end to end. Suppose you're preparing a weekly
status report and you want Claude to build the whole thing:

> "Create a Google Doc called 'Weekly Status — Week 37'. Give it a Title-styled heading with
> the same name, then three Heading 2 sections: 'Highlights', 'Blockers', and 'Next Week'.
> Under Highlights, put three bullet points about the API migration finishing, the new
> onboarding flow shipping, and the support backlog dropping below 10 tickets. Leave the other
> two sections with a single placeholder line each saying 'TBD'."

Behind the scenes, this single request becomes roughly a dozen tool calls: `create`, then a
sequence of `append_text` and `update_paragraph_style` calls building up the title and each
heading, interleaved with the bullet and placeholder text. You don't see or need to manage any
of this — you see the finished document, and Claude reports back with the direct link. If any
individual step fails (say, a transient rate limit), Claude should tell you specifically what
succeeded and what didn't, rather than silently leaving a half-built document and reporting
success.

A natural follow-up in the same conversation:

> "Actually, change 'Blockers' to 'Risks & Blockers', and add a fourth Highlights bullet about
> the design review being complete."

Since the document already exists, Claude re-reads its current structure (indices have
changed since the original creation, because of everything already inserted), locates the
'Blockers' heading and the Highlights section, and applies the two edits. This is the normal
rhythm of working with this server: build, review, refine — each refinement re-anchors itself
against the document's *current* state rather than assuming yesterday's indices are still
valid.

## Multi-document workflows

Some requests naturally span more than one document or more than one Drive operation chained
together:

> "Find every doc in my 'Contracts' folder that still has '[DRAFT]' in the title, and list
> them for me."

This is `list_files` scoped to a folder, with the results filtered or described based on the
title text — Claude reads the returned file list and picks out the ones matching your
criteria, since Drive's own query language is limited to what Google exposes (name contains,
mimeType, parent folder, trashed status, full-text content) and doesn't support arbitrary
substring matching on title in one query the way you might phrase it conversationally.

> "Copy my 'Contract Template' doc, name the copy 'Acme Corp Agreement', and put it in the
> 'Contracts' folder."

This chains `copy` (with both a new name and a target folder) in one call — no need to copy
first and then separately move and rename.

> "I have three drafts — 'Proposal v1', 'Proposal v2', and 'Proposal v3' — archive the first
> two by moving them to an 'Old Drafts' folder, and leave v3 where it is."

This is a `create_folder` (if 'Old Drafts' doesn't already exist) followed by two `move`
calls. Claude should confirm which folder it created or found before moving anything, if
there's any ambiguity about whether 'Old Drafts' already exists elsewhere in your Drive.

## Using the webapp dashboard alongside chat

This server ships with an optional local webapp (started via `start.bat`, or automatically if
you're running the desktop app build) that mirrors and extends what you can do through chat
alone:

- The **Dashboard** page shows your connection status and tool count at a glance, with a
  prominent red "Complete onboarding" button if you haven't connected your Google account yet.
- The **Documents** page lets you search your Drive visually and click straight through to any
  document in your browser — useful when you want to browse rather than describe what you're
  looking for.
- The **Tools** page shows every tool this server exposes, with each portmanteau's full list of
  operations expandable — a good reference if you're curious what's possible beyond what's
  described here.
- The **Skills** page renders this server's built-in usage skill (the same guidance an
  assistant reads to know how to drive the tools correctly) as readable, formatted text.
- The **Chat** page lets you talk to a locally-running LLM (Ollama or LM Studio, if you have
  either installed) with this server's own usage guidance pre-loaded as context — handy for
  quick questions about the tool surface without needing Claude Desktop open, though it does
  not itself have live access to your documents the way Claude does through the actual MCP
  tool calls.
- **Settings** is where you connect or disconnect your Google account, and where you pick
  which local LLM engine and model the Chat page should use.
- **Help** and **Logs** are reference and diagnostic pages — Help summarizes architecture,
  ports, and common fixes; Logs shows the server's own recent log lines, useful when
  troubleshooting a connection issue.

None of the webapp is required to use this server through Claude Desktop — it's a convenience
layer for browsing, diagnostics, and a lightweight chat surface, not a replacement for the
actual MCP tool integration.

## Frequently asked questions

**Can this server read documents I haven't explicitly shared with myself?** No — it can only
see and act on documents visible to whichever Google account completed the OAuth consent
screen, exactly the same access any other application using your Google sign-in would have.
It cannot see documents belonging to other people unless they've shared those documents with
your account.

**Does this work with Google Sheets or Slides?** No — this server is scoped specifically to
Google Docs (content) and the subset of Google Drive operations relevant to managing Docs
files (search, sharing, trash, comments, revisions). Sheets and Slides have their own separate
Google APIs and are outside this server's scope.

**What happens if I revoke access from my Google Account settings page directly, instead of
through this server?** The next tool call will fail with `not_authenticated`, exactly as if
you'd called `revoke` yourself — Claude will prompt you to reconnect, and the browser consent
flow will run again.

**Is there a limit to how many documents or how much text I can work with?** Google's own API
quotas apply (generous for personal use, documented at Google Cloud Console under each API's
Quotas tab), and very large documents may take Claude multiple `get_structure` calls to fully
map out if they contain thousands of paragraphs, but there's no limit imposed by this server
itself beyond what Google's APIs allow.

**Can multiple people use this server against the same Google account at the same time?**
Each installation of this server caches one OAuth token for one Google account at a time. If
you want to switch which account is connected, revoke and reconnect with the other account's
credentials during the browser consent step.

**What if I want to edit a document that's currently open and being edited live by someone
else?** Google Docs handles concurrent editing natively (the same way two people can have a
document open in their browsers simultaneously); API-driven edits from this server merge into
the document the same way a third browser tab's edits would. In rare cases of truly
simultaneous conflicting edits to the exact same character range, Google's API may return a
conflict error, which this server surfaces as `error_type: "conflict"` — simply retrying the
specific edit after checking the document's current state resolves this.

**Does creating a document through this server notify anyone?** No — creating, editing, and
organizing your own documents is silent, exactly like using the Google Docs web UI yourself.
Only `share` sends a notification, and only if `send_notification` is left at its default of
true (you can set it false if you want to grant access without emailing the recipient).

## Working with very large documents

For documents running into hundreds of paragraphs — long reports, legal contracts, book
manuscripts — `get_structure` returns an outline entry for every non-empty paragraph, which
can be a lot of data in one response. A few practical habits help here: ask for a specific
section rather than the whole outline when you know roughly where you're working ("show me
the structure around the 'Termination Clause' heading" rather than "show me the whole
document's structure"); use `replace_all_text` for anything that's a genuine find-and-replace
across the whole document rather than manually locating every occurrence via structure calls;
and when making several edits to a large document in one sitting, prefer batching related
edits into a single `batch_update` call over a long sequence of separate `insert_text` calls,
since a single batched call computes all its internal indices relative to one consistent
document snapshot rather than needing a fresh structure re-fetch between every step.

## Working with templates and boilerplate

A common pattern is keeping one canonical template document and generating new documents from
it for each use:

> "Copy my 'Client Proposal Template' doc, name it 'Proposal — Acme Corp', and replace every
> '[CLIENT]' with 'Acme Corp' and every '[DATE]' with today's date."

This chains `copy` (producing an independent new document, not a live link back to the
template) with one or more `replace_all_text` calls against the new copy — the original
template is never modified. This pattern scales well: the same request phrased for a
different client just needs the name and placeholder values changed, and Claude can repeat it
for a whole batch of clients in one conversation if you list them all up front.

## Tips for getting the best results

Be specific about which document you mean whenever more than one document could plausibly
match a vague description — "my report" is ambiguous if you have several; "my Q3 report" or
"the doc titled Weekly Status" is not. When an edit depends on the document's exact current
wording (a find-and-replace, or styling a specific sentence), it's fine to just describe the
target in plain language ("the paragraph that starts with 'In summary'") — Claude will read
the document first to locate it precisely rather than guessing at indices. When you want
several related changes made together, say so in one request rather than one change per
message — this lets Claude plan the full sequence up front (including re-fetching structure
between edits where needed) rather than treating each change as an isolated, context-free
task. And when in doubt about whether an action is reversible — trash versus permanent
deletion, reader versus writer sharing — ask, or let Claude ask you; the tools are designed so
that the safe, reversible choice is always the default unless you explicitly ask for the
irreversible one.
