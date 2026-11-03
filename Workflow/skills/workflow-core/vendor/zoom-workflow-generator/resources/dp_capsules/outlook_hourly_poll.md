---
name: outlook_hourly_poll
description: "Read-only one-hour polling fallback for an Outlook event request that has no supported trigger, such as a new email arriving in Outlook. Lists recent inbox messages, applies the user's event criteria, and emits a typed match result for a separately gated downstream step. Use only after the Custom schedule trigger; never send, reply, forward, draft, move, flag, categorize, mark read, or delete mail."
version: "1.0"
tags:
  - outlook
  - polling
  - recent messages
  - read only
  - workflow_planner
required_tools:
  - zm.connector_mcp.zm_outlook.outlook_list_messages
  - zm.connector_mcp.zm_outlook.outlook_get_message
---

# Outlook Recent-Message Poll

## Purpose and boundary

This capsule replaces an unavailable Outlook receive event with a bounded read on each hourly
schedule. It is a detector only. It never performs the user's downstream delivery or write.

- Run only after `zm.system.scheduler.trigger.scheduler` configured to repeat every one hour.
- Treat the DP execution instant as the end of a half-open window: `[run time - 60 minutes, run
  time)`. Use the provider's received timestamp (`receivedDateTime`), never a date mentioned in the
  message body. Take the run time from the epoch milliseconds of the current-time context, which are
  UTC, and write the window in UTC; never convert the displayed local clock through its zone
  abbreviation, which can name more than one zone.
- Inspect the authenticated user's Outlook inbox. If the request says simply "when an email arrives
  in Outlook", every inbox message in the window is eligible. Apply sender, subject, content,
  importance, unread, attachment, or other filters only when the accumulated user request states
  them. Do not read Sent Items, Drafts, Deleted Items, or Junk Email unless the request names them.
- The only allowed connector operations are `outlook_list_messages` and `outlook_get_message`. Do
  not send, reply, forward, draft, move, copy, flag, categorize, mark read, or delete messages.

## Procedure

1. List recent inbox mail with explicit non-empty parameters: filter on `receivedDateTime` at or
   after the window start, order by `receivedDateTime` descending, select only the fields the request
   needs plus the message id and received timestamp, and request enough results to cover the whole
   hour instead of the connector default. Follow the next-page link or skip offset until the results
   are older than the window or there are no more results.
2. Filter the observations to the exact half-open 60-minute window. Discard messages whose received
   timestamp is missing or cannot be parsed; do not infer it from ordering.
3. Apply only the user's stated matching criteria. Call `outlook_get_message` for one message only
   when a stated criterion or the downstream step needs body content the list result omits.
   Deduplicate results within this run by provider message id.
4. Emit `matched=true` only when at least one observed message survives both the time window and the
   requested criteria. Otherwise emit `matched=false` and an empty `matched_items` value.
5. Put only grounded fields needed by downstream work in `matched_items`, including each provider
   message id and received timestamp. Preserve sender, subject, preview, content, and attachment facts
   only when the request needs them. Never invent a link, sender, timestamp, or body field.

## Failure and output contract

- Authorization failure, connector failure, an incomplete listing window, or unparseable timestamps
  are not matches. Set `matched=false`, make no write, and explain the read failure compactly in
  `response`.
- `matched_items` is a compact machine-readable string containing the qualifying messages. It must
  be empty when `matched=false`.
- A downstream operation must be behind a deterministic `matched isTrue` condition and must bind
  `matched_items`. A no-match run ends without a downstream side effect.
