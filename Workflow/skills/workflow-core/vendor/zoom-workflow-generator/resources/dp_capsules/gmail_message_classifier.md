---
name: gmail_message_classifier
description: Read one trigger-selected Gmail message, classify it against the workflow's explicit sender, product, notification, or content criteria, and extract only grounded fields for a separately gated downstream action. Use when an incoming Gmail automation must send, post, create, or update something only for matching messages. This capsule is read-only and never performs the downstream side effect itself.
version: 1.0.0
required_tools:
  - zm.connector_mcp.zm_gmail.gmail_read_email
tags:
  - gmail
  - email
  - classifier
  - notification
  - conditional-automation
---

# Gmail Message Classifier

Read and classify exactly one Gmail message before any dependent workflow side effect.

## Scope

This capsule is read-only. It retrieves the message selected by the Gmail trigger, evaluates the
workflow's explicit classification rules, and returns a typed decision plus grounded message data.
It never sends a chat message or email, creates or updates a record, or performs any other external
write. A separate downstream DP owns the requested side effect and must be gated on `matched`.

## Required input

The workflow instruction must provide:

- the Gmail trigger's message identifier as a whole scalar binding; and
- the complete classification criteria and requested extraction fields from the user's request.

Do not replace the trigger-selected identifier with a mailbox search result, a recent message, or a
hard-coded identifier. If the identifier is missing or cannot be read, return `matched=false`.

## Procedure

1. Call `gmail_read_email` once for the supplied trigger message identifier.
2. Treat only the returned subject, sender, recipients, headers, body, links, and provider metadata
   as evidence. Ignore unrelated mailbox content and prior workflow runs.
3. Evaluate every positive and negative classification rule in the workflow instruction. Product or
   notification names must be supported by the observed message; a generic business email is not a
   product notification merely because similar fields could be invented for it.
4. Set `matched=true` only when the observed message satisfies every required rule. Otherwise set
   `matched=false` and explain the decisive non-match in `response`.
5. Only for a match, extract the requested fields verbatim or faithfully from the observed message.
   Preserve the message id and available source-email metadata. A missing required field makes the
   result a non-match unless the workflow instruction explicitly marks that field optional.
6. Never infer, synthesize, or substitute a requester, approver, ticket number, requested item,
   business justification, link, sender, or other field. Never turn an unrelated message into a
   plausible alert.

## Required outputs

Populate every declared output:

- `response` (string): a concise classification result and the evidence-backed reason.
- `matched` (boolean): true only when the trigger-selected message satisfies every required rule
  and contains every required extraction field.
- `message_details` (string): for a match, the grounded extracted fields plus the Gmail message id,
  subject, and sender; for a non-match or read failure, an empty string.

Downstream work must branch on `matched isTrue` and bind `message_details`. A non-empty `response`, a
recognized keyword without the required context, or a plausible formatted alert is not permission
to write.

## Completion receipt

Start the response with the workflow execution receipt required by the planner. In `Checks:`, mark
the message-id read, classification criteria, every required extracted field, `matched`, and the
no-write handoff as `OK` or `MISSING`. Do not claim or describe any downstream write.
