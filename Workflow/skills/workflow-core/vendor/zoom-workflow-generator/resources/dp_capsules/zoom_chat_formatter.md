---
name: zoom_chat_formatter
description: "Beautifies model-generated content for Zoom Chat/Channel by converting unsupported markdown syntax into Zoom-compatible equivalents, adding emoji-based section headers, extracting action items, bolding summary sentences, converting implicit enumerations into bullet lists, and splitting dense paragraphs; accepts any plain text or markdown content; use when the user asks to format, reformat, send, or prepare content for Zoom Chat or a Zoom Channel."
version: "1.1"
tags:
  - Zoom Chat
  - Zoom Channel
  - formatter
  - workflow_planner
required_tools: []
---

# Zoom Chat Formatter

> This is a formatting-first skill, not a summarization skill.

## Purpose

Accepts any model-generated text or markdown content and produces a well-formatted, readable output for Zoom Chat. The skill converts unsupported markdown syntax into Zoom Chat-compatible equivalents, improves readability by bolding summary sentences and structuring content into emoji-based sections, and may make only minimal wording adjustments when strictly necessary to improve readability or resolve awkward formatting — without changing meaning, tone of body content, or level of detail. The output is ready to paste into a Zoom Chat channel or DM.

This skill formats the message content only. It does not itself send the message unless a downstream tool or workflow explicitly handles delivery.

## When to Use

Most commonly triggered when the user asks to prepare content for sending to a Zoom Chat, Zoom Channel, or direct message. Zoom Chat and Zoom Channel share the same message format.

Examples:
- "Send this to Zoom Chat"
- "Send this to Zoom Channel [name]"
- "Send a direct message to me"
- "Send this to the [channel name] channel"
- "Format this for Zoom Chat"
- "Make this Zoom Chat compatible"
- "Prepare this for Zoom Chat"

## Input

**Plain text or markdown** (pasted by user or piped from another skill):
- Accept any free-form text or markdown
- Extract the full content body as the transformation source
- If no content is provided, ask the user before continuing

## Core Principle

**Beautify for chat, preserve meaning.** Optimize the content for Zoom Chat readability — actively add structure where it improves clarity. Only minimal wording adjustments are permitted, and only when strictly necessary to improve readability or resolve awkward formatting. Every fact, conclusion, timeline, and action item must be preserved.

Do NOT:
- Change conclusions, timelines, owners, or action items
- Omit any content without a clear readability reason
- Add information not present in the original
- Rewrite body content for style preference alone

## Output Requirements

Structure the output into clearly defined sections using emoji-based headers. Each section starts with `EMOJI + *Section Title*`, followed by short bullets or lines.

- *CRITICAL*: Emoji must appear outside bold text — e.g. `📊 *Daily Activity Metrics*`
- Separate each section with a blank line
- Use a professional but engaging tone for headers and labels only; do not alter the tone of body content
- Prioritize actionable information; output must be directly usable in Zoom Chat

Recommended sections (adapt based on content; do not force sections the content does not support):
- 📌 *Summary*
- 📊 *Key Insights / Metrics*
- ⚠️ *Risks / Issues*
- ✅ *Action Items*
- 📅 *Next Steps*

## Zoom Chat Syntax Reference

### Allowed markup

| Syntax | Renders as |
|--------|-----------|
| `*text*` | **Bold** — ONLY when `*` wraps a word or phrase |
| `_text_` | *Italic* |
| `~text~` | ~~Strikethrough~~ |
| `` `text` `` | Inline code |
| `> text` | Block quote |
| `•` | Bullet point |
| `<https://example.com>` | Link |
| `<https://example.com\|label>` | Labeled link |
| `<!{user_jid}\|Name>` or `<!{email}\|Name>` | Mention user |
| `<!all>` | Mention all |

### Disallowed syntax (must be removed or transformed)

| Syntax | Action |
|--------|--------|
| `#`, `##`, `###` headings | Convert to `EMOJI + *bold text*` |
| `* ` at the start of a line (list marker) | Remove marker and replace with allowed bullet |
| `-`, `+`, `1.` list markers | Remove marker and replace with allowed bullet |
| Markdown tables | Convert to key–value blocks |
| ````` fenced code blocks | Strip fences; preserve content |
| HTML, CSS | Remove or convert to plain text |
| Non-Markdown style attributes | Remove |
| `@mentions` | Remove the `@` prefix; keep the name as plain text unless valid Zoom mention syntax is explicitly intended |

**`*` disambiguation rule (critical):**
The character `*` has two distinct roles — context determines which applies:
- `*text*` (wraps a word/phrase) → bold emphasis — allowed, keep as-is
- `* ` (at the start of a line, followed by a space) → list marker — disallowed, remove the `* ` prefix and replace with an allowed bullet

## Transformation Rules

### 1. Headings → Emoji + Bold Labels

Convert all `#`-prefixed headings to `EMOJI + *label*` on their own line. Choose the most semantically appropriate emoji.
`## Action Items` → `✅ *Action Items*` / `### Background` → `📌 *Background*`

### 2. Bullet and Ordered Lists → Allowed Zoom Chat Bullets

Remove `-`, `* `, `+`, `1.` / `2.` / `3.` markers and replace:
- `•` for standard bullets — `* Fix the bug` → `• Fix the bug`
- `1️⃣ 2️⃣ 3️⃣` for numbered sequences — `1. Deploy` → `1️⃣ Deploy`
- `*Action Items*` → keep as-is (bold label, not a list marker)

### 3. Tables → Key–Value Blocks

Convert each row to a key–value block using column headers as labels. Separate row groups with a blank line.

`| Auth regression | Alice | Apr 10 |` →

*Risk:* Auth regression
*Owner:* Alice
*Due:* Apr 10

### 4. Fenced Code Blocks → Plain Text or Inline Code

Strip fences. Preserve all line breaks. Use `` `inline code` `` only if content is a single line ≤ 80 characters; otherwise keep as plain text.

### 5. Direct Quotes → Block Quotes

Wrap clearly attributed verbatim quotes with `> text`.
`Alice said: "Ship by Friday."` → `Alice said:` / `> Ship by Friday.`

Apply only when the source text explicitly presents quoted speech or quoted writing. Do NOT convert emphasis, conclusions, or paraphrases into block quotes.

### 6. Long Paragraphs → Shorter Lines

Split at sentence boundaries (`.`, `?`, `!`) only. Do NOT split within abbreviations (`e.g.`, `U.S.`), numbers (`3.2`), or version strings (`v1.2.3`).

### 7. Spacing and Grouping

Blank line between sections; no consecutive blank lines within a logical unit. Do NOT bold entire paragraphs. Keep language concise and skimmable.

## Active Beautification Rules

These rules apply even when the original content has no explicit formatting.

### B1. Bold Summary Sentences

Bold sentences that introduce a topic, state a key conclusion, or act as a section header in prose form. Do NOT bold mid-paragraph sentences or content that is already structured.

`Here are the action items from today's meeting. Alice will fix...`
→ `*Here are the action items from today's meeting.*` / `Alice will fix...`

### B2. Implicit Enumerations → Bullet Lists

If 3 or more clearly parallel items are listed inline (comma/semicolon/`and`/`or`), convert to bullets. Preserve the introductory clause wording as closely as possible; bold it only when it genuinely functions as a summary or lead-in. Do NOT apply to 2-item lists or naturally flowing sentences.

`We need to fix the login bug, deploy to staging, and update the roadmap doc.`
→ `*We need to:*` / `• fix the login bug` / `• deploy to staging` / `• update the roadmap doc`

### B3. Structure Injection

**B3a — Action items:** Always extract action items first into `✅ *Action Items*`, each on its own bullet line, preserving original wording.

**B3b — Section injection:** For remaining unstructured content, group into logical sections with emoji-based headers. Do NOT change wording; only reorganize for readability.

**B3c — Dense splitting:** Break paragraphs exceeding ~3–4 sentences into smaller chunks without changing meaning.

## Language Rule

- Output language must match the dominant language of the input
- Do NOT translate or alter people names, company names, product names, tool names, URLs, or any proper nouns

## Escaping & Safety

- When showing literals, escape these characters as needed: `\* \_ \< \> \~ \\`
- Escape special characters only in user-provided raw text content before insertion; do NOT escape characters in formatting you generate yourself (e.g., bold labels, emoji headers, bullet markers)
- Do NOT escape valid existing Zoom-compatible syntax that should be preserved as functional output (e.g., `<https://...>` links or mention syntax already present in the input)
- Do not auto-link; only preserve or emit exact Zoom-compatible syntaxes listed in this spec

## EXECUTION

Apply rules in this order:

1. **Headings** — replace all `#`-prefixed lines with `EMOJI + *label*`
2. **Code blocks** — strip fences; preserve line breaks; inline code only for single lines ≤ 80 chars
3. **Tables** — convert each row to a key–value block using column headers as labels
4. **Lists** — remove `-`, `* `, `+`, and numbered markers; replace with allowed bullets
5. **Direct quotes** — wrap clearly attributed verbatim quotes with `> text`
6. **Long paragraphs** — split at sentence boundaries only; do not rewrite
7. **B1** — bold intro/summary/conclusion sentences
8. **B2** — convert 3+ parallel inline items to bullet list
9. **B3a** — extract action items into `✅ *Action Items*`
10. **B3b** — inject emoji section headers for remaining unstructured content
11. **B3c** — break dense paragraphs (> ~4 sentences) into smaller chunks
12. **Spacing** — blank lines between sections; no consecutive blank lines within a unit

Apply all rules in a single pass.

## Final Validation (mandatory before output)

Scan the output and confirm:
- No `#`, `##`, `###` headings remain
- No fenced code blocks remain
- No `-`, `* `, `+`, or `1.` / `2.` / `3.` list markers remain
- No markdown table rows (lines containing table syntax) remain
- All section headers use `EMOJI + *text*`
- Only allowed Zoom Chat syntax is present
- The message is concise, structured, skimmable, and action-oriented
- No factual content, owners, dates, decisions, or action items have been dropped unless strictly necessary to remove unsupported syntax duplication

If any violation is found, fix it before returning output. Return only the formatted content — no preamble, no explanation, no commentary.
