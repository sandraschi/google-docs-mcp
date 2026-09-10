"""One-off generator for assets/prompts/examples.json (3-4-100 rule).

Not part of the package, not shipped in the .mcpb bundle (excluded via
.mcpbignore's `tests/`-style dev-tooling exclusions is unnecessary here since
this lives under scripts/, already excluded by MCPB_PACKAGING_STANDARDS §2.3
"IN: src/" / "OUT: everything else"). Run once, commit the output, discard
re-running unless the tool surface changes.
"""

import json
from pathlib import Path

examples = []


def add(name, description, prompt, tool, arguments):
    examples.append(
        {"name": name, "description": description, "prompt": prompt, "tool": tool, "arguments": arguments}
    )


# --- google_docs_auth (6) ---
add("auth-status-check", "Check OAuth configuration and authentication state",
    "Check my Google Docs connection status.", "google_docs_auth", {"operation": "status"})
add("auth-status-before-task", "Proactively check auth before starting a document task",
    "Before we start, is my Google account connected?", "google_docs_auth", {"operation": "status"})
add("auth-start-oauth", "Begin the OAuth consent flow",
    "Connect my Google account.", "google_docs_auth", {"operation": "start_oauth"})
add("auth-start-oauth-reconnect", "Re-authenticate after a token expired",
    "I think I got signed out — reconnect my Google account.", "google_docs_auth", {"operation": "start_oauth"})
add("auth-revoke", "Revoke the cached OAuth token",
    "Disconnect my Google account from this app.", "google_docs_auth", {"operation": "revoke"})
add("auth-revoke-switch-account", "Revoke access to switch to a different Google account",
    "Sign out of Google so I can connect a different account.", "google_docs_auth", {"operation": "revoke"})

# --- google_docs (13 operations, 2-3 examples each) ---
add("docs-create-basic", "Create a new blank Google Doc",
    "Create a new Google Doc called 'Meeting Notes'.", "google_docs",
    {"operation": "create", "title": "Meeting Notes"})
add("docs-create-report", "Create a doc for a status report",
    "Make a new doc titled 'Weekly Status — Week 37'.", "google_docs",
    {"operation": "create", "title": "Weekly Status — Week 37"})
add("docs-get-raw", "Fetch the raw Docs API document structure",
    "Show me the raw document JSON for document 1AbCdEfGhIjK.", "google_docs",
    {"operation": "get", "document_id": "1AbCdEfGhIjK"})
add("docs-read-text-basic", "Read the plain text content of a document",
    "What does my 'Meeting Notes' doc currently say?", "google_docs",
    {"operation": "read_text", "document_id": "1AbCdEfGhIjK"})
add("docs-read-text-summary", "Read a document to summarize it",
    "Read my 'Project Plan' doc and summarize the key points.", "google_docs",
    {"operation": "read_text", "document_id": "1PlanDocId"})
add("docs-get-structure-basic", "Get the heading/paragraph outline of a document",
    "Show me the outline of my 'Project Plan' doc.", "google_docs",
    {"operation": "get_structure", "document_id": "1PlanDocId"})
add("docs-get-structure-before-edit", "Get structure to find an edit target",
    "Find where the 'Timeline' heading is in my 'Project Plan' doc.", "google_docs",
    {"operation": "get_structure", "document_id": "1PlanDocId"})
add("docs-insert-text-at-index", "Insert text at a known index",
    "Insert 'Draft v2 — ' at the very start of document 1AbCdEfGhIjK.", "google_docs",
    {"operation": "insert_text", "document_id": "1AbCdEfGhIjK", "text": "Draft v2 — ", "index": 1})
add("docs-append-text-basic", "Append text to the end of a document",
    "Add a line about the budget approval to the end of my 'Meeting Notes' doc.", "google_docs",
    {"operation": "append_text", "document_id": "1AbCdEfGhIjK", "text": "\nBudget approved by finance."})
add("docs-append-text-bullet", "Append a bullet-style line to a document",
    "Add another highlight bullet to my status report about the design review being complete.",
    "google_docs", {"operation": "append_text", "document_id": "1StatusDocId",
                     "text": "\n- Design review complete"})
add("docs-delete-range-basic", "Delete a specific character range",
    "Delete the outdated sentence between index 120 and 210 in document 1AbCdEfGhIjK.",
    "google_docs", {"operation": "delete_range", "document_id": "1AbCdEfGhIjK",
                     "start_index": 120, "end_index": 210})
add("docs-replace-all-text-placeholder", "Replace a template placeholder across the whole document",
    "Replace every '[CLIENT NAME]' with 'Acme Corp' in my 'Contract Template' doc.", "google_docs",
    {"operation": "replace_all_text", "document_id": "1ContractDocId",
     "find_text": "[CLIENT NAME]", "replace_text": "Acme Corp"})
add("docs-replace-all-text-typo", "Fix a repeated typo throughout a document",
    "Fix every 'recieve' to 'receive' in my report.", "google_docs",
    {"operation": "replace_all_text", "document_id": "1ReportDocId",
     "find_text": "recieve", "replace_text": "receive"})
add("docs-replace-all-text-case-sensitive", "Case-sensitive find and replace",
    "Replace only the exact capitalized 'TODO' markers with 'DONE' in my checklist doc, case sensitive.",
    "google_docs", {"operation": "replace_all_text", "document_id": "1ChecklistDocId",
                     "find_text": "TODO", "replace_text": "DONE", "match_case": True})
add("docs-insert-page-break", "Insert a page break",
    "Add a page break right before the 'Appendix' section in my report.", "google_docs",
    {"operation": "insert_page_break", "document_id": "1ReportDocId", "index": 4200})
add("docs-insert-table-basic", "Insert a table for structured data",
    "Add a 3 by 4 table to the end of my 'Budget' doc for expense categories.", "google_docs",
    {"operation": "insert_table", "document_id": "1BudgetDocId", "rows": 3, "columns": 4, "index": 1500})
add("docs-update-paragraph-style-heading", "Turn a paragraph into a heading",
    "Turn the 'Introduction' paragraph into a Heading 2.", "google_docs",
    {"operation": "update_paragraph_style", "document_id": "1DocId", "start_index": 1,
     "end_index": 13, "named_style_type": "HEADING_2"})
add("docs-update-paragraph-style-center", "Center-align a paragraph",
    "Center the title paragraph in my flyer doc.", "google_docs",
    {"operation": "update_paragraph_style", "document_id": "1FlyerDocId", "start_index": 1,
     "end_index": 40, "alignment": "CENTER"})
add("docs-update-text-style-bold", "Make specific text bold",
    "Make the first paragraph of my cover letter bold.", "google_docs",
    {"operation": "update_text_style", "document_id": "1CoverLetterId", "start_index": 1,
     "end_index": 180, "bold": True})
add("docs-update-text-style-color", "Change text color to highlight urgency",
    "Make the word URGENT in my email draft red and bold.", "google_docs",
    {"operation": "update_text_style", "document_id": "1EmailDraftId", "start_index": 55,
     "end_index": 61, "bold": True, "foreground_color": "FF0000"})
add("docs-update-text-style-italic-underline", "Apply italic and underline together",
    "Make the case citation in my legal memo italic and underlined.", "google_docs",
    {"operation": "update_text_style", "document_id": "1MemoDocId", "start_index": 900,
     "end_index": 950, "italic": True, "underline": True})
add("docs-batch-update-footer", "Use the raw batch_update escape hatch for a footer",
    "Add a footer saying 'Confidential — Internal Use Only' to every page of my report.",
    "google_docs", {"operation": "batch_update", "document_id": "1ReportDocId",
                     "requests": [{"createFooter": {"type": "DEFAULT"}}]})
add("docs-batch-update-suggested-edit", "Use raw batch_update for a Docs API feature without a named operation",
    "Insert this correction as a tracked suggestion, not a direct edit.", "google_docs",
    {"operation": "batch_update", "document_id": "1DraftDocId",
     "requests": [{"insertText": {"location": {"index": 300}, "text": "revised wording"}}]})

# --- google_drive (18 operations, 2-3 examples each) ---
add("drive-list-files-basic", "List recent Google Docs files",
    "List the Google Docs I've edited most recently.", "google_drive",
    {"operation": "list_files", "limit": 10})
add("drive-list-files-folder", "List files inside a specific folder",
    "Show me everything in my 'Contracts' folder.", "google_drive",
    {"operation": "list_files", "folder_id": "1ContractsFolderId", "limit": 25})
add("drive-list-files-page2", "Continue a paginated file listing",
    "Show me the next page of those results.", "google_drive",
    {"operation": "list_files", "limit": 25, "cursor": "CAAaBBQCEB0"})
add("drive-search-basic", "Full-text search across Drive",
    "Search my Drive for anything mentioning 'quarterly budget'.", "google_drive",
    {"operation": "search", "query": "quarterly budget"})
add("drive-search-scoped-folder", "Search within a specific folder",
    "Search my 'Contracts' folder for drafts still marked '[DRAFT]'.", "google_drive",
    {"operation": "search", "query": "[DRAFT]", "folder_id": "1ContractsFolderId"})
add("drive-get-metadata-basic", "Get a file's metadata",
    "When was my 'Budget' doc last modified, and who owns it?", "google_drive",
    {"operation": "get_metadata", "file_id": "1BudgetDocId"})
add("drive-create-folder-basic", "Create a new Drive folder",
    "Make a new folder called 'Archive 2026'.", "google_drive",
    {"operation": "create_folder", "name": "Archive 2026"})
add("drive-create-folder-nested", "Create a folder inside an existing folder",
    "Create a 'Q1' subfolder inside my 'Reports' folder.", "google_drive",
    {"operation": "create_folder", "name": "Q1", "folder_id": "1ReportsFolderId"})
add("drive-copy-basic", "Copy a document with a new name",
    "Copy my 'Client Proposal Template' and name the copy 'Proposal — Acme Corp'.", "google_drive",
    {"operation": "copy", "file_id": "1TemplateDocId", "name": "Proposal — Acme Corp"})
add("drive-copy-to-folder", "Copy a document into a specific folder",
    "Duplicate my template into the 'Contracts' folder as 'Acme Agreement'.", "google_drive",
    {"operation": "copy", "file_id": "1TemplateDocId", "name": "Acme Agreement",
     "folder_id": "1ContractsFolderId"})
add("drive-move-basic", "Move a file into a different folder",
    "Move my 'Draft Proposal' doc into my 'Client X' folder.", "google_drive",
    {"operation": "move", "file_id": "1DraftProposalId", "new_parent_id": "1ClientXFolderId"})
add("drive-rename-basic", "Rename a file",
    "Rename 'Untitled document' to 'Vendor Agreement — DRAFT'.", "google_drive",
    {"operation": "rename", "file_id": "1UntitledDocId", "name": "Vendor Agreement — DRAFT"})
add("drive-trash-basic", "Move a file to trash (reversible)",
    "Delete my old 'Scratch Notes' doc.", "google_drive",
    {"operation": "trash", "file_id": "1ScratchNotesId"})
add("drive-untrash-basic", "Restore a file from trash",
    "Actually, restore that 'Scratch Notes' doc I just trashed.", "google_drive",
    {"operation": "untrash", "file_id": "1ScratchNotesId"})
add("drive-delete-permanently-confirmed", "Permanently delete a file with explicit confirmation",
    "Permanently delete my old 'Scratch Notes' doc — I don't need to recover it, ever.",
    "google_drive", {"operation": "delete_permanently", "file_id": "1ScratchNotesId", "confirm": True})
add("drive-share-reader", "Share a document as read-only",
    "Share my 'Proposal' doc with sandra@example.com as a viewer.", "google_drive",
    {"operation": "share", "file_id": "1ProposalDocId", "email": "sandra@example.com", "role": "reader"})
add("drive-share-commenter", "Share a document with comment access",
    "Share my 'Proposal' doc with sandra@example.com so she can comment.", "google_drive",
    {"operation": "share", "file_id": "1ProposalDocId", "email": "sandra@example.com", "role": "commenter"})
add("drive-share-writer", "Share a document with edit access",
    "Give teammate@example.com edit access to the 'Team Roadmap' doc.", "google_drive",
    {"operation": "share", "file_id": "1RoadmapDocId", "email": "teammate@example.com", "role": "writer"})
add("drive-share-no-notification", "Share without sending an email notification",
    "Share this doc with alex@example.com as a reader but don't email them about it.",
    "google_drive", {"operation": "share", "file_id": "1DocId", "email": "alex@example.com",
                      "role": "reader", "send_notification": False})
add("drive-list-permissions-basic", "List who has access to a file",
    "Who currently has access to my 'Salary Review' doc?", "google_drive",
    {"operation": "list_permissions", "file_id": "1SalaryReviewId"})
add("drive-revoke-permission-basic", "Revoke a specific person's access",
    "Remove teammate@example.com's access to my 'Team Roadmap' doc.", "google_drive",
    {"operation": "revoke_permission", "file_id": "1RoadmapDocId", "permission_id": "perm123"})
add("drive-list-revisions-basic", "List a document's revision history",
    "Show me the recent revision history for my 'Contract' doc.", "google_drive",
    {"operation": "list_revisions", "file_id": "1ContractDocId", "limit": 10})
add("drive-list-comments-basic", "List comment threads on a document",
    "What comments are on my 'Draft Proposal' doc?", "google_drive",
    {"operation": "list_comments", "file_id": "1DraftProposalId", "limit": 25})
add("drive-add-comment-basic", "Add a new comment to a document",
    "Add a comment on my 'Budget' doc saying the Q2 numbers need a second look.", "google_drive",
    {"operation": "add_comment", "file_id": "1BudgetDocId", "content": "Q2 numbers need a second look."})
add("drive-reply-comment-basic", "Reply within an existing comment thread",
    "Reply to that comment thread from Sarah saying I've updated the figures.", "google_drive",
    {"operation": "reply_comment", "file_id": "1BudgetDocId", "comment_id": "AAAABBBB",
     "content": "Updated the figures — please take another look."})
add("drive-resolve-comment-basic", "Mark a comment thread resolved",
    "Mark that comment thread as resolved.", "google_drive",
    {"operation": "resolve_comment", "file_id": "1BudgetDocId", "comment_id": "AAAABBBB"})
add("drive-list-files-docs-only-false", "List all Drive file types, not just Google Docs",
    "Show me everything in my 'Assets' folder, not just Google Docs.", "google_drive",
    {"operation": "list_files", "folder_id": "1AssetsFolderId", "docs_only": False})

# --- multi-step chained examples (realistic combined workflows) ---
add("workflow-search-then-append", "Search for a doc by name then edit it",
    "Find my 'Meeting Notes' doc and add a line about the budget approval.", "google_drive",
    {"operation": "search", "query": "Meeting Notes"})
add("workflow-template-copy-and-fill", "Copy a template and fill in placeholders",
    "Copy my 'Client Proposal Template', name it 'Proposal — Acme Corp', and replace every "
    "'[CLIENT]' with 'Acme Corp'.", "google_drive",
    {"operation": "copy", "file_id": "1TemplateDocId", "name": "Proposal — Acme Corp"})
add("workflow-archive-old-drafts", "Create an archive folder and move old drafts into it",
    "Archive 'Proposal v1' and 'Proposal v2' by moving them into a new 'Old Drafts' folder.",
    "google_drive", {"operation": "create_folder", "name": "Old Drafts"})
add("workflow-status-report-heading", "Style a newly appended line as a heading",
    "Add a 'Risks & Blockers' section heading to my status report.", "google_docs",
    {"operation": "append_text", "document_id": "1StatusDocId", "text": "\nRisks & Blockers"})

# --- help / status (4) ---
add("help-basic", "Get the static tool reference",
    "What tools does this Google Docs server have?", "google_docs_mcp_help", {})
add("help-typical-flow", "Ask for the recommended usage sequence",
    "What's the typical workflow for using this server for the first time?",
    "google_docs_mcp_help", {})
add("status-app-basic", "Show the rich Prefab status card",
    "Show me a status card for my Google Docs connection.", "show_google_docs_status_app", {})
add("status-app-after-connect", "Check the status card right after connecting",
    "I just connected my Google account — show me the updated status.",
    "show_google_docs_status_app", {})

# --- additional phrasings and edge cases to reach the 100+ floor ---
add("auth-status-webapp-context", "Check auth status from a webapp Settings context",
    "Is my Google account connected right now?", "google_docs_auth", {"operation": "status"})
add("auth-start-oauth-first-time", "First-time OAuth for a brand new install",
    "This is my first time using this — connect it to my Google account.", "google_docs_auth",
    {"operation": "start_oauth"})
add("auth-revoke-security-concern", "Revoke access after a security concern",
    "I think my laptop was compromised — disconnect Google access immediately.",
    "google_docs_auth", {"operation": "revoke"})

add("docs-create-empty-scratch", "Create a quick scratch document",
    "Make a quick throwaway doc called 'Scratch'.", "google_docs",
    {"operation": "create", "title": "Scratch"})
add("docs-create-agenda", "Create a meeting agenda document",
    "Create a doc called 'Team Sync Agenda — 2026-09-10'.", "google_docs",
    {"operation": "create", "title": "Team Sync Agenda — 2026-09-10"})
add("docs-read-text-check-placeholder", "Read a document to check for leftover placeholders",
    "Check my 'Acme Agreement' doc for any placeholder text I forgot to fill in.", "google_docs",
    {"operation": "read_text", "document_id": "1AcmeAgreementId"})
add("docs-get-structure-count-headings", "Use structure to count sections in a document",
    "How many sections does my 'Annual Report' doc have?", "google_docs",
    {"operation": "get_structure", "document_id": "1AnnualReportId"})
add("docs-insert-text-mid-document", "Insert a clarifying sentence mid-document",
    "Insert a clarifying sentence right after the second paragraph in my memo.", "google_docs",
    {"operation": "insert_text", "document_id": "1MemoDocId", "text": "This applies retroactively.",
     "index": 640})
add("docs-append-text-signature", "Append a signature block to a letter",
    "Add a signature block to the end of my cover letter.", "google_docs",
    {"operation": "append_text", "document_id": "1CoverLetterId",
     "text": "\n\nSincerely,\nSandra Schipal"})
add("docs-delete-range-outdated-clause", "Delete an outdated contract clause",
    "Remove the outdated non-compete clause from my contract, it's between index 3400 and 3900.",
    "google_docs", {"operation": "delete_range", "document_id": "1ContractDocId",
                     "start_index": 3400, "end_index": 3900})
add("docs-replace-all-text-date-placeholder", "Replace a date placeholder with today's date",
    "Replace all the '{{date}}' placeholders in my invoice template with today's date.",
    "google_docs", {"operation": "replace_all_text", "document_id": "1InvoiceDocId",
                     "find_text": "{{date}}", "replace_text": "2026-09-10"})
add("docs-replace-all-text-company-rename", "Swap a company name throughout a document",
    "Our company renamed — replace every 'Initech' with 'Acme Corp' in my policy doc.",
    "google_docs", {"operation": "replace_all_text", "document_id": "1PolicyDocId",
                     "find_text": "Initech", "replace_text": "Acme Corp"})
add("docs-insert-page-break-before-appendix", "Insert a page break before an appendix section",
    "Put a page break right before my Appendix section.", "google_docs",
    {"operation": "insert_page_break", "document_id": "1ReportDocId", "index": 5200})
add("docs-insert-table-expense-tracker", "Insert a table for an expense tracker",
    "Add a 5 by 3 table to track expenses at the end of my finance doc.", "google_docs",
    {"operation": "insert_table", "document_id": "1FinanceDocId", "rows": 5, "columns": 3,
     "index": 800})
add("docs-update-paragraph-style-title", "Style a paragraph as the document Title",
    "Make the very first line of my doc the actual document Title style, not just bold.",
    "google_docs", {"operation": "update_paragraph_style", "document_id": "1DocId",
                     "start_index": 1, "end_index": 20, "named_style_type": "TITLE"})
add("docs-update-paragraph-style-justify", "Justify a paragraph's alignment",
    "Justify the body paragraph in my newsletter.", "google_docs",
    {"operation": "update_paragraph_style", "document_id": "1NewsletterId", "start_index": 200,
     "end_index": 900, "alignment": "JUSTIFIED"})
add("docs-update-text-style-font-size", "Increase font size for emphasis",
    "Make the section heading bigger, like 18 point font.", "google_docs",
    {"operation": "update_text_style", "document_id": "1DocId", "start_index": 1,
     "end_index": 25, "font_size": 18})
add("docs-update-text-style-remove-bold", "Remove bold formatting from a range",
    "Un-bold that whole first paragraph, it was a mistake.", "google_docs",
    {"operation": "update_text_style", "document_id": "1DocId", "start_index": 1,
     "end_index": 180, "bold": False})
add("docs-batch-update-nested-list", "Use batch_update for a nested bullet list",
    "Add a nested sub-bullet under the second bullet point in my outline.", "google_docs",
    {"operation": "batch_update", "document_id": "1OutlineDocId",
     "requests": [{"insertText": {"location": {"index": 260}, "text": "\n\tSub-point detail"}}]})

add("drive-list-files-limit-large", "List a larger page of recent files",
    "Show me my last 50 edited documents.", "google_drive", {"operation": "list_files", "limit": 50})
add("drive-search-full-text-clause", "Search for documents containing a specific clause",
    "Which of my contracts mention a 'non-compete clause'?", "google_drive",
    {"operation": "search", "query": "non-compete clause"})
add("drive-get-metadata-owner-check", "Check who owns a shared document",
    "Who owns the 'Team Roadmap' doc?", "google_drive",
    {"operation": "get_metadata", "file_id": "1RoadmapDocId"})
add("drive-create-folder-year-archive", "Create a yearly archive folder",
    "Set up a new 'Archive 2025' folder for last year's documents.", "google_drive",
    {"operation": "create_folder", "name": "Archive 2025"})
add("drive-copy-blank-template-batch", "Copy a template for a new client engagement",
    "Duplicate my blank SOW template for a new client called 'Beta Industries'.", "google_drive",
    {"operation": "copy", "file_id": "1SowTemplateId", "name": "SOW — Beta Industries"})
add("drive-move-to-client-folder", "Move a finished proposal into a client-specific folder",
    "Move 'Beta Industries Proposal' into the 'Beta Industries' client folder.", "google_drive",
    {"operation": "move", "file_id": "1BetaProposalId", "new_parent_id": "1BetaFolderId"})
add("drive-rename-add-status-suffix", "Rename a document to reflect its current status",
    "Rename 'Vendor Agreement' to 'Vendor Agreement — SIGNED'.", "google_drive",
    {"operation": "rename", "file_id": "1VendorAgreementId", "name": "Vendor Agreement — SIGNED"})
add("drive-trash-cleanup-batch", "Trash an old duplicate document",
    "Get rid of the duplicate 'Notes (1)' doc, I don't need it.", "google_drive",
    {"operation": "trash", "file_id": "1NotesDupId"})
add("drive-untrash-accidental-delete", "Recover an accidentally deleted document",
    "Oops, I didn't mean to delete that — bring back 'Notes (1)'.", "google_drive",
    {"operation": "untrash", "file_id": "1NotesDupId"})
add("drive-delete-permanently-old-drafts-batch", "Permanently purge an old, explicitly unneeded draft",
    "That 'Old Draft v0' file is garbage, permanently delete it, I'm sure.", "google_drive",
    {"operation": "delete_permanently", "file_id": "1OldDraftV0Id", "confirm": True})
add("drive-share-multiple-context-writer", "Grant edit access for active collaboration",
    "Give my co-founder edit access to the 'Pitch Deck Notes' doc — jamie@example.com.",
    "google_drive", {"operation": "share", "file_id": "1PitchNotesId", "email": "jamie@example.com",
                      "role": "writer"})
add("drive-list-permissions-audit", "Audit access before sharing a sensitive document externally",
    "Before I send this externally, who already has access to this doc?", "google_drive",
    {"operation": "list_permissions", "file_id": "1SensitiveDocId"})
add("drive-revoke-permission-offboarding", "Revoke a former employee's access",
    "Remove access for our old contractor, contractor@example.com, from all... well, start with "
    "the 'Vendor List' doc.", "google_drive",
    {"operation": "revoke_permission", "file_id": "1VendorListId", "permission_id": "perm456"})
add("drive-list-revisions-audit-trail", "Check revision history for an audit trail",
    "I need to know when the 'Compliance Policy' doc last changed for an audit.", "google_drive",
    {"operation": "list_revisions", "file_id": "1CompliancePolicyId", "limit": 20})
add("drive-list-comments-before-finalizing", "Check open comments before finalizing a document",
    "Are there any unresolved comments on my 'Final Draft' before I send it out?", "google_drive",
    {"operation": "list_comments", "file_id": "1FinalDraftId", "limit": 50})
add("drive-add-comment-review-note", "Leave a review note for a collaborator",
    "Leave a comment on the pricing section saying it needs legal review.", "google_drive",
    {"operation": "add_comment", "file_id": "1PricingDocId", "content": "Needs legal review before finalizing."})
add("drive-reply-comment-clarification", "Reply to a comment asking for clarification",
    "Reply to that comment asking what specific concern they have.", "google_drive",
    {"operation": "reply_comment", "file_id": "1PricingDocId", "comment_id": "CCCCDDDD",
     "content": "Can you clarify which line item concerns you?"})
add("drive-resolve-comment-after-fix", "Resolve a comment after addressing the feedback",
    "I fixed that issue, resolve the comment about the pricing typo.", "google_drive",
    {"operation": "resolve_comment", "file_id": "1PricingDocId", "comment_id": "EEEEFFFF"})
add("drive-search-not-docs-only", "Search across all Drive file types for an attachment",
    "Search my whole Drive, not just Docs, for anything called 'logo'.", "google_drive",
    {"operation": "search", "query": "logo", "docs_only": False})

add("workflow-onboarding-first-doc", "First document created right after onboarding completes",
    "Now that I'm connected, create a test doc to make sure everything works.", "google_docs",
    {"operation": "create", "title": "onboarding-test"})
add("workflow-weekly-report-build", "Build a full weekly report from a structured request",
    "Create a Weekly Status doc with Highlights, Blockers, and Next Week sections.",
    "google_docs", {"operation": "create", "title": "Weekly Status — Week 37"})
add("workflow-contract-redline-cycle", "Read a contract, then apply a redline edit",
    "Read my draft contract and tell me if the payment terms section needs updating.",
    "google_docs", {"operation": "read_text", "document_id": "1ContractDraftId"})
add("workflow-share-after-review", "Share a document only after confirming it's ready",
    "Once I confirm the doc looks good, share it with the client as a viewer.", "google_drive",
    {"operation": "share", "file_id": "1ClientReadyDocId", "email": "client@example.com",
     "role": "reader"})
add("workflow-cleanup-trash-review", "Review trash candidates before bulk cleanup",
    "Show me my recent docs so I can decide which old ones to trash.", "google_drive",
    {"operation": "list_files", "limit": 30})
add("workflow-comment-triage", "Triage all open comments across a document before a deadline",
    "List every unresolved comment on my 'Board Deck' before tomorrow's meeting.", "google_drive",
    {"operation": "list_comments", "file_id": "1BoardDeckId", "limit": 100})

add("help-error-types", "Ask what an error_type means",
    "What does 'not_authenticated' mean when a tool call fails?", "google_docs_mcp_help", {})
add("help-pagination", "Ask how pagination works for list operations",
    "How do I get the next page of search results?", "google_docs_mcp_help", {})
add("status-app-troubleshooting", "Use the status card to troubleshoot a failed tool call",
    "My last request failed — show me the connection status card to see what's wrong.",
    "show_google_docs_status_app", {})

out_path = Path(__file__).resolve().parents[1] / "assets" / "prompts" / "examples.json"
out_path.write_text(json.dumps(examples, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {len(examples)} examples to {out_path}")
