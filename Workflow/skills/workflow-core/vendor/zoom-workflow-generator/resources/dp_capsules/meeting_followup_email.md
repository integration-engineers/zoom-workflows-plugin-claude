---
name: meeting_followup_email
description: "Send or draft a conventional post-meeting recap email with grounded recipients and factual decisions, action items, and next steps. Use only when the requested product is the recap email itself; do not use for a decision log, design review, interview/hiring report, coaching brief, engagement plan, onboarding pack, allocation report, campaign analysis, or risk monitor."
version: "3.0"
required_tools:
  - zm.meeting.meeting.get_meeting_summary
  - zm.connector_mcp.zm_gmail.gmail_send_email
  - zm.connector_mcp.zm_gmail.gmail_create_draft
---

# Meeting Follow-up Email

Create one factual HTML recap email and perform exactly the delivery action requested by the
workflow task prompt.

## Scope gate

Use this capsule only for a conventional post-meeting follow-up email. Do not reinterpret a request
for a decision log, technical/design/RFC analysis, interview feedback, hiring debrief, coaching
brief, joint engagement plan, onboarding pack, meeting-allocation report, campaign recap, or deal
risk report as a generic follow-up email.

## Grounded inputs

1. Treat the workflow task prompt and its bound trigger/upstream objects as authoritative.
2. If those inputs already contain usable meeting content, summary, decisions, or action items, use
   them directly. Do **not** call `get_meeting_summary` merely to re-fetch or verify supplied content.
3. Call `get_meeting_summary` only when the supplied input lacks usable recap content and carries a
   real meeting ID/UUID that the tool accepts.
4. If no usable content is available after that bounded lookup, make no Gmail call. Return
   `delivery_succeeded=false` and explain the missing data in `response`.
5. Never invent an attendee, email address, decision, owner, deadline, commitment, or next step.

## Recipient authority

The task prompt must explicitly ground the recipient as one of these:

- a concrete email address or named recipient whose address is present in trusted meeting data;
- the current user (for example "email me" or "send to the requester");
- the host or organizer, when explicitly requested and grounded in meeting data; or
- the meeting participants/attendees, when explicitly requested and their addresses are grounded.

Do not silently substitute the current user, host, attendees, stakeholders, or any inferred group for
an omitted recipient. Do not guess an address from a name or company. When the prompt does not ground
a recipient, make no Gmail call and return `delivery_succeeded=false`; planner clarification should
normally prevent this state.

## Compose the recap

- Match the language of the meeting content unless the prompt requests another language.
- Use a concise subject tied to the meeting title or purpose.
- Include only grounded sections that add value: thanks/context, key outcomes or decisions, action
  items with owners and deadlines, open questions, and next steps.
- Omit empty sections. Mark an unknown owner or date as unknown only when the underlying action item
  is grounded; do not create placeholder commitments.
- For a send action, the body must be valid, self-contained HTML. Use `<p>`, headings,
  `<ul>/<li>`, and a compact table when several action items exist. Do not send Markdown or plain
  text as an HTML body.
- For a draft action, use concise readable text because the real `gmail_create_draft` schema accepts
  `body` but has no HTML flag. Do not pass unsupported parameters.

## Perform exactly one requested Gmail action

- If the task asks to draft, prepare a draft, save as draft, or not send yet, call only
  `gmail_create_draft` with its real `to`, `cc`, `bcc`, `subject`, `body`, and optional `threadId`
  fields.
- If the task asks to send, call only `gmail_send_email`.
- Never call both tools for one execution.
- A `gmail_send_email` call must set `is_html` to the JSON boolean `true` and pass the HTML string as
  `body`. `gmail_create_draft` does not accept `is_html`; never add it to that call.
- Do not claim success from generated content alone. `delivery_succeeded=true` only when the chosen
  Gmail tool confirms the requested action. A tool error, missing recipient, missing content, or
  skipped call sets it to false.

## Required outputs

Populate every declared output:

- `response` (string): concise factual execution summary, including why delivery was skipped/failed.
- `delivery_succeeded` (boolean): true only after confirmed send/draft success.
- `delivery_metadata` (string): confirmed message/draft identifier or recipient/subject details;
  otherwise an empty string.

Downstream nodes must use `delivery_succeeded`, not prose in `response`, as the success signal.
