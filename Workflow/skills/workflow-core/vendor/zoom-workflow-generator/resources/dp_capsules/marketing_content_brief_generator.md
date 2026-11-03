---
name: marketing_content_brief_generator
description: "Generate professional marketing content briefs from meeting transcripts, summaries, or planning notes. Use this skill whenever a user shares notes or transcripts from a marketing meeting — campaign planning, content strategy, brand kickoff, demand generation, social media planning, email marketing, product marketing, or editorial planning — and wants a structured content brief. Trigger when users say things like: turn this into a brief, generate a content brief, make a campaign brief from these notes, what content should we create, or summarize this meeting into a brief. Covers all marketing content types: social posts, blog articles, email campaigns, paid ads, video scripts, landing pages, whitepapers, and more."
version: "1.0"
tags:
  - meetings
required_tools:
---

# Marketing Content Brief Generator

Transform raw marketing meeting transcripts, summaries, and planning notes into polished, professional **Content Briefs** — structured documents that align creative teams and guide content execution from strategy to delivery.

**Primary context:** Marketing — campaign planning, content strategy, brand, demand gen, social, email, product marketing, editorial.

---

## Output Format

Always output in **rich, professional Markdown**:
- `##` / `###` headings for section hierarchy
- **Bold** for labels and key terms
- `> blockquotes` for strategic rationale and key quotes from source
- Tables for channels, deliverables, CTAs, timelines
- Bullet lists for audience traits, messages, assets
- `---` horizontal rules between major sections

---

## Section Classification

Sections are split into **Required** and **Contextual**. Apply this distinction strictly — do not pad the brief with empty or near-empty contextual sections.

### ✅ Required Sections
Always include these, regardless of source richness. If a required section has no information, include it with a `> ⚠️` note — because the team **must** resolve it before work begins.

| # | Section | Why Required |
|---|---------|-------------|
| 1 | Campaign Overview | Establishes scope and purpose |
| 2 | Target Audience | Everything downstream depends on this |
| 3 | Core Message & Tone | Directs creative execution |
| 4 | Deliverables | Defines what gets made and who owns it |
| 5 | Call to Action | Every piece of marketing content needs one |

### 🔘 Contextual Sections
Include **only if the source material contains relevant information**. If a contextual section has nothing to offer, **omit it entirely** — do not include it just to fill space.

| # | Section | Include When... |
|---|---------|----------------|
| 6 | Channels & Distribution | Specific platforms, formats, or posting cadence are discussed |
| 7 | SEO & Keywords | SEO, search, blog content, or keyword strategy is mentioned |
| 8 | References & Assets | Brand guidelines, existing assets, competitors, or research are mentioned |
| 9 | Approval & Next Steps | Owners, deadlines, or review process are defined |
| 10 | Open Questions & Risks | Ambiguities, conflicts, or unresolved items exist in the source |

> **Rule of thumb:** A lean, high-signal brief beats a padded one. Five tight sections are better than ten diluted ones.

---

## Brief Template

### Header (always present)

```
# 📋 Content Brief: [Campaign / Initiative Name]

> **Strategic Intent:** One-sentence synthesis of what this content is meant to achieve and for whom.

**Source:** [Transcript / AI summary / Meeting notes / Bullet points]
**Meeting Date:** [If mentioned, otherwise omit this line]
**Prepared by:** Content Brief Generator
```

---

### Section 1 — 🎯 Campaign Overview *(Required)*

```
## 1. 🎯 Campaign Overview

| Field | Details |
|-------|---------|
| **Campaign Name** | |
| **Campaign Type** | Awareness / Lead Gen / Retention / Launch / Engagement / etc. |
| **Business Objective** | |
| **Success Metrics / KPIs** | |
| **Timeline / Launch Date** | |
| **Budget** | |
```

Only include rows where information exists or is inferable. Remove rows that are entirely unknown rather than leaving them blank — except for **Business Objective** and **Campaign Type**, which should always appear with a `⚠️` if missing.

---

### Section 2 — 👥 Target Audience *(Required)*

```
## 2. 👥 Target Audience

### Primary Audience
- **Segment:**
- **Pain Points / Motivations:**
- **Awareness Stage:** Unaware / Problem-aware / Solution-aware / Ready to convert

### Secondary Audience *(if mentioned)*
- **Segment:**
- **Notes:**
```

If no audience is defined at all:
```
## 2. 👥 Target Audience

> ⚠️ **No audience was defined in the source.** This is a critical gap — content strategy cannot proceed without it.
>
> Based on context, possible audiences to consider: [suggest 2–3 based on any available signals]
```

---

### Section 3 — 💬 Core Message & Tone *(Required)*

```
## 3. 💬 Core Message & Tone

### Primary Message
> [The single most important takeaway for the audience — synthesized from source]

### Supporting Messages
1.
2.
3.

### Tone & Voice
- **Tone:**
- **What to Avoid:**
```

Always populate Tone with at least one directional note, even if inferred (e.g., "energetic and accessible" from "we want it to feel fun and approachable").

---

### Section 4 — 📦 Deliverables *(Required)*

```
## 4. 📦 Deliverables

| # | Content Piece | Format | Owner | Due Date | Status |
|---|--------------|--------|-------|----------|--------|
| 1 | | | | | Not started |
```

- Pull explicit deliverables first
- If none are stated but campaign type is clear, **suggest a standard content suite** with a note: *"No deliverables defined — suggested standard suite for [campaign type]:"*
- Owner and due date can be blank — the content piece name must always be present

---

### Section 5 — 🚀 Call to Action *(Required)*

```
## 5. 🚀 Call to Action

| Placement | CTA Copy | Destination |
|-----------|----------|-------------|
| | | |
```

If no CTA is mentioned:
```
> ⚠️ No CTA was defined. Recommend aligning on a single primary action before creative kickoff.
```

---

### Section 6 — 📣 Channels & Distribution *(Contextual)*

```
## 6. 📣 Channels & Distribution

| Channel | Format | Cadence / Timing | Notes |
|---------|--------|-----------------|-------|
| | | | |
```

Include only when specific channels, platforms, or distribution logic are discussed.

---

### Section 7 — 🔑 SEO & Keywords *(Contextual)*

```
## 7. 🔑 SEO & Keywords

- **Primary Keyword:**
- **Secondary Keywords:**
- **Topic Cluster / Pillar:**
```

Include only for blog posts, landing pages, or when SEO is explicitly discussed.

---

### Section 8 — 📎 References & Assets *(Contextual)*

```
## 8. 📎 References & Assets

- **Brand Guidelines:**
- **Assets to Repurpose:**
- **Competitive Examples:**
- **Data / Research Sources:**
```

Include only when brand assets, guidelines, or existing content are referenced.

---

### Section 9 — ✅ Approval & Next Steps *(Contextual)*

```
## 9. ✅ Approval & Next Steps

| Action Item | Owner | Due Date |
|------------|-------|----------|
| Brief review & sign-off | | |
| Creative kickoff | | |
| First draft | | |
| Feedback round | | |
| Final approval | | |
```

Include when owners, deadlines, or a review process are mentioned. Particularly useful when the source is a Zoom/Gong transcript with clear action item attribution.

---

### Section 10 — 📝 Open Questions & Risks *(Contextual)*

```
## 10. 📝 Open Questions & Risks

- [ ] [Unresolved item from source]
- [ ] [Conflicting information — both versions noted]
```

Include when the source contains ambiguities, unresolved decisions, or conflicting statements. Do not manufacture open questions if the source is clear.

---

## Extraction Priorities

**1 — Explicit:** Named campaigns, segments, dates, KPIs, platforms, deliverable owners — pull verbatim.

**2 — Inferred:** Derive from tone and context signals:
- *"We want this to feel premium"* → Tone: **Aspirational**
- *"Going after mid-market ops managers"* → Audience: **Mid-market operations leaders**
- *"Before the conference"* → Hard timeline constraint exists

**3 — Missing:** Required sections with no signal → `⚠️` note. Contextual sections with no signal → omit entirely.

---

## Edge Cases

| Situation | Behavior |
|-----------|---------|
| **Source too vague** (< 3 usable signals) | Add a banner warning at top; populate required sections with ⚠️ notes; suggest standard deliverables |
| **Multiple campaigns discussed** | Generate one brief per campaign, clearly labeled |
| **No deliverables mentioned** | Suggest a standard content suite for the inferred campaign type |
| **Conflicting info** | Show both versions, mark `⚠️ Conflict — needs resolution` |
| **Not a marketing meeting** | Note clearly that the source doesn't appear to be a marketing/content planning session; attempt extraction anyway; flag uncertainty prominently |
| **Empty input** | Respond with a friendly error asking for the source material |

---

## Final Check Before Outputting

- [ ] All 5 **required** sections are present (or have ⚠️ notes with a clear ask of the team)
- [ ] Contextual sections are included **only** when source supports them — no padding
- [ ] No invented facts — only extracted or explicitly inferred information
- [ ] Deliverables table has at least a content piece name for each row
- [ ] Tone has at least one directional note
- [ ] Brief reads as a useful standalone document — not just a reformatted summary
