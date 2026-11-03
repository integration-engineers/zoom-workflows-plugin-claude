---
name: google_sheets_row_classifier
description: Read one exact Google Sheets spreadsheet and tab, evaluate rows against the workflow's explicit criteria, and extract only grounded qualifying rows for a separately gated downstream action. Use when a document, message, email, or record write is allowed only if matching spreadsheet rows actually exist. This capsule is read-only and never performs the downstream side effect itself.
version: 1.0.0
required_tools:
  - zm.connector_mcp.zm_googlesheets.googlesheets_search_spreadsheets
  - zm.connector_mcp.zm_googlesheets.googlesheets_get_sheet_names
  - zm.connector_mcp.zm_googlesheets.googlesheets_values_get
tags:
  - google-sheets
  - spreadsheet
  - rows
  - classifier
  - conditional-automation
---

# Google Sheets Row Classifier

Read and classify rows from exactly one spreadsheet tab before any dependent workflow side effect.

## Scope

This capsule is read-only. It resolves one exact spreadsheet, reads one exact tab, evaluates the
workflow's explicit row criteria, and returns a typed decision plus grounded row data. It never
creates or edits a document, sends a message or email, changes spreadsheet values, or performs any
other external write. A separate downstream DP owns the requested side effect and must be gated on
`matched`.

## Required input

The workflow instruction must provide:

- an exact spreadsheet title, provider id, or URL;
- one exact tab/worksheet name; and
- the complete match rules and requested output fields from the user's request.

Do not substitute a similarly named spreadsheet, another tab, the first search result, a prior-run
identifier, or an inferred provider id. A title must resolve to exactly one live spreadsheet. Zero or
multiple matches, a missing tab, or an unreadable range returns `matched=false`.

## Procedure

1. Resolve the requested spreadsheet from the supplied id/URL or an exact-title search. For a title,
   require exactly one exact match and use only the id returned by that current run.
2. Read the sheet names for that spreadsheet and require one exact match for the requested tab.
3. Read the tab's values. A missing, empty, truncated beyond useful interpretation, or failed read is
   not evidence that a row matches.
4. Evaluate every observed data row against every positive and negative rule in the workflow
   instruction. Preserve column-to-value identity from the returned header and cells.
5. Set `matched=true` only when at least one observed row satisfies every required rule and contains
   every required extraction field. Otherwise set `matched=false` and explain the decisive no-match
   or read failure in `response`.
6. Only for matches, extract the requested fields faithfully from the qualifying rows. Never infer,
   synthesize, color-code, or fabricate a row, owner, severity, date, amount, status, or next step.

## Required outputs

Populate every declared output:

- `response` (string): a concise read/classification result and evidence-backed reason.
- `matched` (boolean): true only when at least one observed row satisfies every requested rule and
  contains every required output field.
- `matched_rows` (string): grounded requested fields from qualifying rows, including the exact
  spreadsheet title/id and tab; an empty string for a no-match or read failure.

Downstream work must branch on `matched isTrue` and bind `matched_rows`. A non-empty `response`, a
plausible row, a guessed id, or a count inferred before a successful values read is not permission to
write.

## Completion receipt

Start the response with the workflow execution receipt required by the planner. In `Checks:`, mark
spreadsheet identity, tab identity, values read, every match criterion, every required extracted
field, `matched`, and the no-write handoff as `OK` or `MISSING`. Do not claim or describe any
downstream write.
