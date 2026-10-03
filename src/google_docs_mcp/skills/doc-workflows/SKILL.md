---
name: doc-workflows
description: Twelve reusable doc workflows — summarize, condense, polish, restructure, and extract from Google Docs using google-docs-mcp tools.
---

# Doc workflows — analyze / improve / condense

Each workflow below is a recipe: when to use it, the exact tool calls in
order, and the guardrails. General rules for all of them:

- Read before you write: `google_docs(operation="read_text")` for prose,
  `get_structure` when you need heading/index positions.
- Confirm before any content-replacing step (`replace_all_text`,
  `restore_file`); default to writing a **new** doc or appending unless the
  user said "in place".
- Indices shift after every edit — re-fetch `get_structure` between edits
  in the same turn; prefer `append_text` over guessed `insert_text` indices.
- `trash` is reversible, `delete_permanently` is not (needs `confirm=True`).

## 1. summarize-to-bullets

User wants the gist without opening the doc.
1. `read_text(document_id)` (or `export` as `txt` for very long docs).
2. Write 5-9 bullets: decision/request first, then supporting facts; keep
   names, dates, numbers verbatim.
3. Reply in chat with the bullets; do NOT edit the doc.

## 2. condense-in-place

Shorten a bloated doc to a target length (default 60% of original).
1. `read_text` + `get_structure` to map sections.
2. Cut filler first (repetition, throat-clearing intros), merge duplicate
   paragraphs, shorten sentences — never drop headings, dates, or numbers.
3. Confirm the target % with the user, then apply via 2-4 `replace_all_text`
   calls on exact quoted phrases (re-fetch structure between calls).

## 3. tldr-header

Prepend a 3-line TL;DR box to the top of the doc, leave the body untouched.
1. `read_text` to draft: Purpose / Decision needed / Key facts.
2. `insert_text(document_id, text="TL;DR: ...\n\n", index=1)`.
3. Confirm wording with the user before inserting.

## 4. clarity-pass

Grammar, spelling, and tightening without changing meaning or voice.
1. `read_text` to collect edits as exact quote → replacement pairs.
2. Apply with `replace_all_text(match_case=True)` per pair, largest
   sections first. Split sentences over ~25 words and walls over 5 lines;
   skip legal/quoted text unless explicitly included.
3. Report what changed in one line per fix; never "improve" facts.

## 5. tone-shift

Rewrite toward a requested tone (formal, friendly, executive).
1. Ask which tone + whether in place or a copy (`create` new doc for the
   variant is the default).
2. `read_text`, rewrite section by section preserving all facts/links.
3. Write back with `replace_all_text` (in place) or `create` + `append_text`
   (variant); confirm before replacing.

## 6. outline-rebuild

Impose heading structure on a flat doc.
1. `get_structure` to see what exists; `read_text` for content.
2. Propose the heading outline in chat first (H1/H2 only).
3. On approval: `update_paragraph_style` per range to set
   `named_style_type` (HEADING_1/HEADING_2/NORMAL_TEXT) — re-fetch
   structure between ranges.

## 7. action-items-extract

Pull decisions + owners + due dates into a table at the end.
1. `read_text` (meeting notes, threads, proposals all work).
2. Draft rows: Action | Owner | Due. Mark unknowns as "?" — never invent
   an owner or date.
3. `append_text` a short "## Actions" section, then `insert_table`
   for the rows. Confirm rows in chat first for anything external.

## 8. meeting-notes-cleanup

Turn raw notes into: Attendees / Decisions / Actions / Open questions.
1. `read_text` the raw notes.
2. Rewrite into the four sections, keeping verbatim quotes for decisions.
3. Replace via 2-3 `replace_all_text` calls or `create` a cleaned copy;
   confirm which before writing.

## 9. redundancy-sweep

Find repeated points across sections and merge them.
1. `read_text` + list the duplicates in chat with section names.
2. Keep the strongest occurrence, delete the rest via `delete_range`
   (exact indices from a fresh `get_structure`) or `replace_all_text`
   on the duplicated sentence.
3. One merge per call; re-fetch structure each time.

## 10. pre-export-polish

Make the doc export-clean (PDF/DOCX) before sending it out.
1. `get_structure`: every section needs a heading; no empty headings.
2. Fix styles (`update_paragraph_style`), add `insert_page_break` before
   appendices if asked.
3. `export` to the requested format and check the output opens — Drive
   export caps at ~10 MB; suggest `txt`/`html` split for huge docs.

## 11. revision-changelog

Explain what changed between versions using Drive history.
1. `list_revisions(file_id)` to get the recent revision ids/timestamps.
2. `export` the current version + ask the user which prior version matters
   (Drive API serves content per current doc, not per revision — compare
   against the user's memory or a backed-up copy, never hallucinate a diff).
3. Write the changelog as bullets in chat; `append_text` it to the doc
   only on request.

## 12. comment-review-pack

Leave review feedback as Drive comments instead of editing directly.
1. `read_text` to quote exact phrases needing review.
2. `add_comment(file_id, content)` per point ("Suggest: ..." + reason).
   Prefer comments over direct edits for other people's docs; use
   `resolve_comment` only on threads the user confirms are done.
