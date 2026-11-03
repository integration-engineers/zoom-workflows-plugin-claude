---
name: email-html-generator
description: Generate clean, email-client-safe HTML from plain text, Markdown, or existing HTML. Use whenever the user wants to compose or prepare an HTML email body, convert notes/announcements/release-notes/newsletters/meeting-summaries to email, turn Markdown into sendable email, or clean up raw HTML so it renders in Gmail, Outlook, Hotmail/Outlook.com, Apple Mail, and Yahoo Mail. Enforces brand styling (primary #0E72ED, no gradients), email-safe markup (inline CSS, table layout, no JS/external assets, ≤720px rounded white card on #F7F9FA), and adapts language/fonts to the detected input language.
version: "1.0"
required_tools:
---

# Email HTML Generator

Turn text, Markdown, or existing HTML into one self-contained HTML document that renders faithfully in major email clients.

## Output

A single `<!DOCTYPE html>` document returned in the DP response. It contains `<html lang dir>`, a
small `<head>` reset, and `<body>`. **Inline every visually important style** because webmail may
strip the head style block.

## Pipeline

**1. Classify input.** HTML if content is primarily tag markup (`<div>`, `<table>`, `<h1>` forming the layout). Markdown if it has `#`, `- `, `**`, `` ` ``, `>`, fenced blocks, or pipe tables. Otherwise plain text. When genuinely ambiguous, ask briefly.

**2. Detect language** (CJK vs Latin vs RTL script). Set `<html lang="…" dir="…">`; use a system
font stack with `PingFang SC`, `Hiragino Sans GB`, and `Microsoft YaHei` fallbacks for CJK and set
`dir="rtl"` for RTL scripts. Write generated framing in that language. Do not translate the content.

**3. Build from this shell.** Use a full-width `role="presentation"` table on `#F7F9FA`, containing
a centered white presentation table with both `width="720"` and
`style="width:100%;max-width:720px;min-width:320px;border-radius:12px"`. Put each content block in
its own `<tr><td>` and use 48px desktop / 24px mobile padding.

**4. Fill the body.**

- **Text/Markdown (Branch A)** — promote the first heading to a title if present; derive a preheader from the opening line. Map Markdown to purposeful blocks (section headers, comfortable paragraphs, tinted tables, status-colored callouts, bulletproof CTA button, dividers). Match structure to content type — a short announcement should feel short; a release note earns a title + summary + grouped sections. Omit the header row entirely if there's no clear title; empty banners look amateurish. Keep the footer minimal — never invent sender names, unsubscribe links, legal text, or logos.

- **Existing HTML (Branch B)** — preserve faithfully. Extract body content, wrap in the shell's card, and only intervene when something is actually broken for email: strip `script`/`iframe`/`form`/`input` elements/external stylesheets/`@import`/event handlers; replace `position:absolute`/`display:flex`/`display:grid` on structural layout with tables; clamp any container > 720px; replace `vh`/`vw` with `px`; drop `rgba()` on *text* (clients strip alpha) while keeping it on backgrounds; make image URLs absolute; inline any critical `<style>` rules. Don't restyle the content's design choices. After returning output, briefly list what you changed.

**5. Apply this design system:**

| Role | Color |
|---|---|
| Primary (links, CTA, accents) | `#0E72ED` |
| Auxiliary (sparingly) | `#FFBF39`, `#FF5F0F`, `#007C7C`, `#9053C2`, `#022B30` |
| Status — notice / warning / error / success | `#FFBF39` / `#FF5F0F` / `#E8173D` / `#268543` |
| Page bg / card bg | `#F7F9FA` / `#FFFFFF` |
| Body / muted / divider | `#022B30` / `#5B6B73` / `#E1E7EC` |

No gradients. Soften with `rgba()` on *backgrounds* only. Card: white, `border-radius:12px`, max-width 720px, no shadow. Body 16px / 1.6 line-height (1.7 for CJK). Heading scale 32/24/20/18. Section spacing 32–40px, card padding 48px desktop → 24px mobile.

Branch B keeps the user's original colors/layout; only Branch A applies the design system wholesale.

**6. Email-safety pass:**

- Table-based layout with `role="presentation" cellpadding=0 cellspacing=0 border=0` (no flex/grid outside of tiny decorative bits)
- Every visually important style inlined on the element
- No `script`, `iframe`, or `form` elements, external stylesheets, `@import`, external fonts
- Absolute URLs only; every `<img>` has `alt`, `width`, `display:block`, `border:0`
- CTA uses a table-wrapped HTML link plus an Outlook MSO/VML fallback with the same label and URL
- Card width ≤ 720px, set via both `width=""` attr and inline `style`
- Total output under 100 KB (Gmail clips at ~102 KB)
- MSO conditional for Outlook-specific fallbacks where needed

## Handing back

Return only the complete HTML string unless the workflow instruction explicitly asks for another
field. For Branch B, briefly list substantive removals only when the requested output permits prose.
Important sends still deserve real-client testing.
