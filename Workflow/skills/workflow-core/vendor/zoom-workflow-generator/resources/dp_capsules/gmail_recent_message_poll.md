---
name: gmail_recent_message_poll
description: "Read-only one-hour polling fallback for a Gmail event request that has no supported trigger. Fetches recent inbox messages, applies the user's event criteria, and emits a typed match result for a separately gated downstream step. Use only immediately after the Custom schedule trigger; never send, draft, label, archive, delete, or otherwise modify mail."
version: "1.0"
tags:
  - gmail
  - polling
  - recent messages
  - read only
  - workflow_planner
required_tools:
  - zm.connector_mcp.zm_gmail.gmail_fetch_emails
---

# Gmail Recent-Message Poll

## Purpose and boundary

This capsule replaces an unavailable Gmail receive event with a bounded read on each hourly
schedule. It is a detector only. It never performs the user's downstream delivery or write.

- Run only after `zm.system.scheduler.trigger.scheduler` configured to repeat every one hour.
- Treat the DP execution instant as the end of a half-open window: `[run time - 60 minutes, run
  time)`. Use the provider's received/message timestamp, never a date mentioned in the message body.
- Inspect the authenticated user's inbox. If the request says simply "when Gmail is received", every
  inbox message in the window is eligible. Apply sender, subject, content, unread, attachment, or
  other filters only when the accumulated user request states them.
- The only allowed connector operation is `gmail_fetch_emails`. Do not send, draft, reply, label,
  archive, move, or delete messages.

## Procedure

1. Fetch recent inbox mail with explicit non-empty parameters. Use a Gmail query broad enough to
   cover the full preceding hour and request enough results to avoid the connector's one-result
   default. Paginate when a page token exists until the results are older than the window or there
   are no more results.
2. Filter the observations to the exact half-open 60-minute window. Discard messages whose received
   timestamp is missing or cannot be parsed; do not infer it from ordering.
3. Apply only the user's stated matching criteria. Deduplicate results within this run by provider
   message id.
4. Emit `matched=true` only when at least one observed message survives both the time window and the
   requested criteria. Otherwise emit `matched=false` and an empty `matched_items` value.
5. Put only grounded fields needed by downstream work in `matched_items`, including each provider
   message id and received timestamp. Preserve sender, subject, content, and attachment facts only
   when the request needs them. Never invent a link, sender, timestamp, or body field.

## Failure and output contract

- Authorization failure, connector failure, an incomplete search window, or unparseable timestamps
  are not matches. Set `matched=false`, make no write, and explain the read failure compactly in
  `response`.
- `matched_items` is a compact machine-readable string containing the qualifying messages. It must
  be empty when `matched=false`.
- A downstream operation must be behind a deterministic `matched isTrue` condition and must bind
  `matched_items`. A no-match run ends without a downstream side effect.
