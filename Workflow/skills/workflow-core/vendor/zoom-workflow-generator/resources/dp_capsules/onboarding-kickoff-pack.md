---
name: onboarding-kickoff-pack
description: Generate a structured New Hire Onboarding Kickoff Pack from a meeting transcript or onboarding sync notes. The pack includes first-week tasks, key contacts, training resources, and 30/60/90-day milestones — all extracted intelligently from the conversation. Use this skill whenever the user mentions "onboarding plan", "onboarding pack", "new hire plan", "kickoff pack", "new employee onboarding", "onboarding sync", "first week plan", "30-60-90 plan", or pastes a transcript and asks to generate onboarding materials. Even if the user simply shares a meeting transcript involving a new hire discussion and asks "what should the onboarding look like", this skill should trigger. This is one of the highest-value HR automation tasks — it turns a 60-minute meeting into an actionable, professionally formatted onboarding document in seconds.
version: "1.0"
tags:
  - meetings
  - hiring
  - HR
required_tools:
---

# New Hire Onboarding Kickoff Pack Generator

## Purpose

After an onboarding kickoff meeting or onboarding sync, HR teams and hiring managers typically spend 30–60 minutes manually assembling an onboarding plan. This skill automates that process: feed it a meeting transcript (or summary), and it produces a polished, reader-friendly Markdown onboarding pack ready to share with the new hire, their manager, and HR.

## Language Detection Rule

**The output language MUST match the input transcript language.** If the transcript is in Chinese, the entire onboarding pack is in Chinese. If the transcript is in English, output in English. If the transcript is mixed, default to the dominant language. Do NOT translate — mirror the language the team actually speaks.

## Workflow

### Step 1: Receive Input

Accept any of the following:
- Raw meeting transcript (from Zoom, Teams, Google Meet, Otter.ai, etc.)
- Meeting summary or notes
- Bullet-point recap from the user
- Uploaded transcript file (.txt, .docx, .pdf)

If the user uploads a file, read it using the appropriate tool before proceeding.

### Step 2: Extract Structured Information

Scan the transcript carefully and extract these categories. Not every category will appear in every meeting — extract only what is explicitly mentioned or strongly implied.

**A. New Hire Profile**
- Name, role/title, team, department
- Start date
- Manager name, HR contact, buddy/mentor (if assigned)
- Work location (office / remote / hybrid)

**B. First-Week Tasks** (Days 1–5)
Look for signals like: "on the first day", "during the first week", "make sure they...", "set up", "walk them through", "introduce them to", assignment of equipment, account provisioning, orientation sessions.

**C. Key Contacts & Stakeholders**
Extract people mentioned as important for the new hire to connect with. Include their name, role, and the context of why they matter (e.g., "Sarah from Design — she'll be collaborating on the Q3 project").

**D. Training & Resources**
Look for mentions of: training sessions, courses, documentation, wikis, Confluence pages, Notion docs, onboarding videos, product demos, shadowing sessions, tools to learn.

**E. 30/60/90-Day Milestones**
Extract any goals, expectations, deliverables, or checkpoints mentioned for the first 30, 60, and 90 days. Signals include: "by the end of the first month", "after 60 days we expect", "the 90-day review", "ramp-up goals", "first project", "fully onboarded by".

**F. Logistics & Admin**
Equipment, badge/access, parking, benefits enrollment deadlines, IT setup, Slack channels to join, recurring meetings to add.

**G. Open Items & Follow-ups**
Anything flagged as unresolved, pending, or requiring action from someone.

### Step 3: Fill Gaps Intelligently

For information NOT found in the transcript:
- Mark with a clear placeholder: `[TBD – confirm with hiring manager]` or `[待确认]`
- Do NOT fabricate details. If the transcript doesn't mention a buddy, don't invent one.
- If very little was discussed for a category (e.g., no training resources mentioned), include the section header with a short note: "Not discussed in the meeting — recommend adding before sharing with the new hire."

### Step 4: Generate the Onboarding Pack

Produce a clean Markdown document with these sections in order: title and profile summary; First
Week checklist; Key Contacts table; Training & Resources; 30/60/90-Day Milestones table;
Logistics & Admin checklist; Open Items & Follow-ups. Omit no section, but mark genuinely missing
information as TBD instead of inventing it.

Key formatting principles:
- Use clear hierarchy: H1 for title, H2 for major sections, H3 for subsections
- Use tables for structured data (contacts, milestones) — they are scannable
- Use task checkboxes (`- [ ]`) for first-week tasks and action items — they feel actionable
- Keep prose minimal — this is a reference doc, not an essay
- Use emoji sparingly for visual anchors (one per section header is fine)
- Bold key names, dates, and deadlines for quick scanning
- End with an "Open Items" section so nothing falls through the cracks

### Step 5: Deliver the Output

Return the complete Markdown pack in the DP response/output field requested by the workflow. Do not
assume a filesystem, create a file, or ask a follow-up question during unattended workflow execution.

## Extraction Confidence

When a piece of information is inferred rather than explicitly stated, note the confidence:
- ✅ **Explicit** — directly stated in the transcript
- ⚠️ **Inferred** — reasonably implied but not directly stated
- ❓ **Unclear** — mentioned ambiguously, needs confirmation

Include these markers in the "Open Items" section for anything that isn't ✅.

## Edge Cases

- **Transcript is too short or vague**: Generate whatever is possible, then list what's missing and suggest the user fill in the gaps or provide more context.
- **Multiple new hires discussed**: Create separate sections or separate files for each person. Ask the user which approach they prefer.
- **No clear 30/60/90 goals mentioned**: Include the section with suggested generic milestones based on the role type (engineering, sales, design, etc.) and clearly mark them as suggestions.
- **Non-English transcript**: Output entirely in the transcript's language. Section headers, placeholders, and notes all follow the same language.
