---
name: send-email
description: Draft or send email on the user's behalf via an available Gmail or Outlook-style mail tool. Use when a workflow must create exactly one draft or deliver exactly one email, preserve To/CC/BCC semantics, choose the provider's real HTML flag for sends, and compose an email-safe body. The requested draft/send action is authoritative and mutually exclusive.
version: "1.0"
required_tools:
---

# Draft or Send Email

Create a draft or deliver an email on the user's behalf, exactly as requested by the saved workflow
task. In a workflow run, rely on the platform's normal connector authorization and risk/HITL policy;
do not add a second conversational confirmation. A recipient must be explicit in the saved task or
grounded in trusted trigger/upstream data. If it is missing or ambiguous at execution time, make no
mail write; do not substitute the requester, host, attendees, stakeholders, or a guessed address.

The task's requested delivery action is a hard mode switch:

- **draft** means create one saved draft and do not send it;
- **send** means send one email and do not create a draft.

Never reinterpret one mode as the other, and never call both kinds of tool.

## Pipeline

**1. Parse the instruction** into:
- `to` — required, ≥ 1 recipient
- `cc`, `bcc` — optional, 0..N each
- `subject` — required (derive a concise factual subject from trusted body/context when omitted)
- `body` — the content in whatever format (plain text, Markdown, or HTML)
- `attachments` — file paths, if any
- `reply_to` — only if explicitly requested

If recipients are missing or ambiguous, stop without a mail write and return `delivery_succeeded=false`;
planner clarification should normally prevent this state. Do not invent recipients, sender identity,
or content. A subject may be derived from grounded body/context.

When the task says the recipient is the **current user**, resolve the authenticated current user's
email and use only that address. Do not replace it with `meeting.host_email`, the organizer,
attendees, or stakeholders merely because those fields are present in trigger data. A clarification
answer naming the current user is explicit recipient authority.

**2. Compose the body as HTML.** Email always renders better as HTML than plain text for non-trivial content. Map the input:

- **Plain text** → wrap in the shell (see §Compose), paragraphs for each blank-line-separated block, detect an obvious title (short first line) and promote it to a header if present
- **Markdown** → render in-place (`#` headings, lists, tables, `>` blockquotes, code, links) as email-safe HTML
- **HTML** → preserve the user's content, only wrap in the shell and strip unsafe bits (see §Compose → strip list)

Framing text you generate (preheader, generated labels) should match the detected language of the body. Never translate the user's own copy.

**3. Find the requested mail tool.** Inspect the available tool schemas and use the matching family:

For Gmail, use `gmail_create_draft` only for `draft`, and use `gmail_send_email` only for `send`.
The draft tool accepts `to`, `cc`, `bcc`, `subject`, `body`, and optional `threadId`; do not pass
`is_html` to it. The send tool accepts the provider's HTML flag as described below.

| Tool family | Send function name | HTML flag | Recipients |
|---|---|---|---|
| Gmail (MCP / Google API) | `send_email`, `send_message`, `gmail_send` | `isHtml: true` or pass body as `html_body` field | arrays usually; `to[]`, `cc[]`, `bcc[]` |
| Microsoft Graph / Outlook | `sendMail`, `send_mail` | body is `{ contentType: "HTML", content: "…" }` | objects: `{ emailAddress: { address, name } }` in a list |
| SendGrid | `mail_send`, `sendgrid_send` | `content: [{ type: "text/html", value: "…" }]` | array of `{ email, name }` |
| Mailgun | `messages_send` | use `html` field (not `text`) | comma-separated strings in `to`, `cc`, `bcc` |
| Generic SMTP | `smtp_send` / `send_mail` | usually `subtype: "html"` or `content_type: "text/html"` | strings or arrays |

**If the tool schema is unclear, inspect it first** (read the parameters description) rather than guessing. A wrong HTML flag means recipients see raw markup.

If no matching mail tool exists, tell the user which tool they'd need to install and stop. Do not simulate a draft or send.

**4. Validate before the mail write.** Resolve and validate the following fields internally:

```
To:       alice@example.com, bob@example.com
CC:       carol@example.com
BCC:      (2 recipients, hidden)
Subject:  Q2 numbers are in
Body:     [short preview, or "saved to /tmp/email-preview.html, 320 lines"]
Attach:   slides.pdf (2.1 MB)
```

In interactive use, preview and ask before sending unless the user pre-authorized it. In unattended
workflow execution, do not pause for a duplicate chat confirmation; platform-owned approval/HITL
still applies. A draft request does not authorize a send.

**5. Perform exactly the requested mail write.** Call the tool with:

- **HTML flag ON** under whatever name the send tool uses. If you send HTML without the flag, the recipient sees `<!DOCTYPE html>…` as text. Do not pass an HTML flag to Gmail draft creation.
- **Recipients distributed correctly.** `to`, `cc`, `bcc` are semantically distinct — don't silently merge. Pass arrays when the tool accepts arrays; use strings only when that's the tool's convention.
- **Subject trimmed**, never empty.
- **Attachments**: verify file paths exist before sending; match the tool's attachment schema (filepath vs base64 vs URL).

**6. Report back.** Show the tool's response — message ID, provider URL, status. If it failed, show the error and offer to retry or adjust. Don't claim success you can't verify.

## Compose (inline essentials)

**Shell** — every email is this one self-contained HTML doc (no external CSS / JS / fonts):

```html
<!DOCTYPE html>
<html lang="[language]" dir="[direction]">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="color-scheme" content="light">
    <title>[subject]</title>
    <style>
      body{margin:0;padding:0;background:#F7F9FA;}
      table{border-collapse:collapse;}
      img{border:0;display:block;max-width:100%;height:auto;}
      a{color:#0E72ED;text-decoration:none;}
    </style>
  </head>
  <body style="margin:0;padding:0;background:#F7F9FA;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',Arial,sans-serif;color:#022B30;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#F7F9FA;">
      <tr><td align="center" style="padding:32px 16px;">
        <table role="presentation" width="720" cellpadding="0" cellspacing="0" border="0"
               style="width:100%;max-width:720px;min-width:320px;background:#FFFFFF;border-radius:12px;overflow:hidden;">
          [body rows]
        </table>
      </td></tr>
    </table>
  </body>
</html>
```

**Layout rules** (why: webmail clients partially strip `<head>` and don't support modern CSS):
- Use `<table role="presentation" cellpadding=0 cellspacing=0 border=0>` for layout — no flex/grid
- Inline every visually important style on the element
- White card, `border-radius:12px`, `max-width:720px`, no shadow
- Body 16px / 1.6 line-height (1.7 for CJK content)

**Default palette** (override if the user has their own brand):
- Primary `#0E72ED` · Text `#022B30` · Muted `#5B6B73` · Divider `#E1E7EC`
- Page bg `#F7F9FA` · Card bg `#FFFFFF`
- Status: notice `#FFBF39` · warning `#FF5F0F` · error `#E8173D` · success `#268543`
- No gradients

**Strip from user-provided HTML**: `script`, `iframe`, `form`, and `input` elements, external stylesheets, `@import`, external fonts, event handlers, `position:absolute/fixed`, `display:flex/grid` on layout, `vh`/`vw` units, `javascript:` / unresolved `data:` URIs. If anything substantive got removed, mention it after.

**CTA buttons** use a table-wrapped HTML link and an MSO/VML fallback with identical text, URL,
background color, and accessible label.

**Total HTML size** must be under ~100 KB (Gmail clips at 102 KB). Deduplicate repeated inline styles if you approach the limit.

## Safety

- In interactive use, preview before sending; in workflow execution, rely on platform risk/HITL.
- A draft action must never invoke a send tool, and a send action must never invoke a draft tool.
- Don't fabricate recipients, signatures, titles, or unsubscribe links.
- If the user says "the team" / "everyone" without a list, ask who specifically.
- Warn before sending to > 20 recipients unless clearly intended (newsletters, announcements).
- Don't auto-CC or auto-BCC anyone the user didn't name.
- If the body mentions "attached" / "see attachment" / "附件" but there's no attachment, point it out before sending.

## Required Outputs

Populate every declared output:

- `response` (string): concise factual mail-write summary or the reason no write occurred.
- `delivery_succeeded` (boolean): true only when the provider confirms the requested draft/send action.
- `delivery_metadata` (string): confirmed message/draft identifier, provider URL, or grounded
  recipient/subject details; otherwise an empty string.

A composed body, non-empty `response`, connector authorization, or attempted tool call is not
success. Downstream nodes must branch on `delivery_succeeded`.
