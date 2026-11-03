---
name: hiring-debrief-decision-log
description: Extract structured hiring decisions and action items from hiring debrief meeting transcripts. Use this skill whenever the user pastes or uploads a hiring debrief transcript, hiring committee meeting notes, interview debrief discussion, or candidate review meeting recording and wants to generate a decision log. Also trigger when the user mentions "hiring debrief", "debrief meeting", "candidate decision", "hiring committee notes", "interview panel recap", "offer decision meeting", or asks to summarize a debrief into actionable next steps. Even if the user simply pastes a meeting transcript that discusses candidate evaluations and hiring decisions without explicitly naming it a "debrief", this skill should activate. This skill is specifically for the post-interview group decision-making meeting — not for individual interviewer feedback forms.
version: "1.0"
tags:
  - meetings
  - hiring
required_tools:
---

# Hiring Debrief & Decision Log

## Purpose

Hiring debrief meetings are where the actual go/no-go decisions happen — a panel reviews interview feedback, debates candidate fit, and decides on next steps. These meetings are high-frequency, high-stakes, and highly collaborative, yet their outcomes often live only in someone's memory or scattered Slack messages.

This skill turns a raw debrief transcript into a structured, scannable decision log that the hiring team can immediately act on: who advances, who gets an offer, what's still open, and who owns each follow-up — with deadlines.

## Language Detection

Detect the primary language of the input transcript and produce all output in that same language. If the transcript mixes languages (common in multinational teams), use the dominant language for the output but preserve proper nouns, role titles, and technical terms as they appear in the original.

## Input

Accept any of the following:
- Raw meeting transcript (auto-generated or manual)
- Meeting summary / recap notes
- Pasted text from a video call recording transcript
- Uploaded transcript file (.txt, .md, .docx, .pdf)

If the user uploads a file, read it using the appropriate tool before proceeding.

## Extraction Process

### Step 1: Identify Candidates Discussed

Scan the transcript for all candidates mentioned. For each candidate, capture:
- **Full name** (or however they are referred to — "the backend candidate", "Candidate #3", etc.)
- **Position / Role** being considered for
- **Requisition or job ID** if mentioned

### Step 2: Extract the Decision for Each Candidate

For every candidate, determine exactly one primary decision from this taxonomy:

| Decision | When to use |
|----------|-------------|
| ✅ Advance to Next Round | Panel agrees candidate should continue; next interview round specified |
| 🎉 Extend Offer | Panel decides to make an offer; may include comp discussion |
| ⏸️ Hold / Pending | Decision deferred — waiting on additional info, references, or another interview |
| 🔄 Additional Interview Needed | Specific skill gap or concern requires a targeted follow-up interview |
| ❌ Reject | Panel decides not to proceed with candidate |

Look for both explicit statements ("let's move her forward") and consensus signals (everyone agreeing, no objections raised). If the decision is ambiguous or was not clearly reached, mark it as ⏸️ Hold / Pending and note what remains unresolved.

### Step 3: Capture Key Discussion Points

For each candidate, extract a concise summary of:
- **Strengths** highlighted by the panel
- **Concerns** raised (skills gaps, culture fit doubts, experience gaps)
- **Dissenting opinions** — if someone disagreed with the group, note who and why, as this context matters for the record

Keep these to 1-2 bullet points each. The goal is a decision log, not a full transcript rehash.

### Step 4: Extract Action Items

This is the most operationally critical part. For every next step mentioned, capture:
- **Action**: What needs to happen (schedule next interview, draft offer letter, request references, etc.)
- **Owner**: Who is responsible — use the name as spoken in the meeting
- **Deadline**: When it should be done — convert relative dates ("by end of week", "before next Monday") to actual calendar dates based on today's date
- **Related Candidate**: Which candidate this action is for

If an owner or deadline was not explicitly stated, flag it clearly so the team can fill in the gap.

### Step 5: Extract Meeting Metadata

From the transcript, identify if available:
- Meeting date and time
- Attendees / panel members
- Hiring manager
- Recruiter

If these aren't discernible from the transcript, omit them rather than guessing.

## Output Template

Produce a single Markdown document following this structure. Adapt section headers to match the detected output language.

```markdown
# Hiring Debrief — Decision Log

> **Date:** [YYYY-MM-DD or as identified]
> **Position:** [Role Title]
> **Panel:** [Names of attendees]
> **Hiring Manager:** [Name]  |  **Recruiter:** [Name]

---

## Candidate Decisions

### [Candidate Name] — [Decision Emoji + Label]

**Strengths**
- [Concise point]
- [Concise point]

**Concerns**
- [Concise point]

**Dissent:** [Name] felt [brief summary] *(omit this line if no dissent)*

---

*(Repeat for each candidate)*

## Action Items

| # | Action | Owner | Deadline | Candidate |
|---|--------|-------|----------|-----------|
| 1 | [What] | [Who] | [When]   | [Name]    |
| 2 | ...    | ...   | ...      | ...       |

> ⚠️ **Gaps to confirm:**
> - [Action] — owner not specified
> - [Action] — deadline not mentioned

## Summary

[2-3 sentence executive summary: how many candidates discussed, key decisions made, most urgent follow-ups]
```

## Quality Principles

- **Be definitive, not wishy-washy.** If the panel made a decision, state it clearly. If they didn't, say that clearly too — don't hedge with "it seems like they might want to…"
- **Preserve attribution.** When someone raises a concern or volunteers for an action item, name them. Accountability matters in hiring.
- **Deadlines are real dates.** Convert "next Friday" to "2025-04-04" (or whatever the actual date is). The whole point is to create an actionable artifact.
- **Flag gaps, don't fill them.** If the transcript doesn't contain an owner or deadline for an action item, say so explicitly in the "Gaps to confirm" section rather than inventing one.
- **Concise over comprehensive.** This is a decision log, not meeting minutes. Capture the signal, drop the noise. Each candidate section should be scannable in under 30 seconds.

## Edge Cases

- **Multiple positions discussed in one meeting**: Group candidates under their respective position headings.
- **Candidate discussed but no decision reached**: Use ⏸️ Hold / Pending and note what blocked the decision.
- **Off-topic discussion**: Ignore segments that aren't related to candidate evaluation or hiring decisions.
- **Vague action items** ("someone should follow up"): Include them in the Gaps section with a note that the owner needs to be assigned.
- **Compensation discussion**: Include in the candidate's section only if it directly affects the offer decision (e.g., "offer at band 5 mid-point"). Do not transcribe detailed salary negotiations.

## Example

**Input snippet (English):**
> "So for Candidate A, I think everyone agrees she crushed the system design round. Interviewer A, you had some concerns about her leadership experience? ... Yeah, I think she's strong technically but only 2 years of managing. Maybe we do one more round focused on leadership scenarios. Coordinator, can you set that up by next Wednesday? ... Agreed. And for Candidate B — I think he's a clear yes. Let's get the offer letter out. Recruiter, you'll handle comp? Target mid-band for L5. We want this done by Friday."

**Output:**

```markdown
# Hiring Debrief — Decision Log

---

## Candidate Decisions

### Candidate A — 🔄 Additional Interview Needed

**Strengths**
- Excellent system design performance; panel consensus on strong technical skills

**Concerns**
- Limited leadership/management experience (2 years)

**Dissent:** Interviewer A raised concerns about leadership readiness

---

### Candidate B — 🎉 Extend Offer

**Strengths**
- Strong overall performance; unanimous panel support ("clear yes")

**Concerns**
- None raised

---

## Action Items

| # | Action | Owner | Deadline | Candidate |
|---|--------|-------|----------|-----------|
| 1 | Schedule leadership-focused interview round | Coordinator | 2025-03-26 (Wed) | Candidate A |
| 2 | Prepare offer letter, target mid-band L5 | Recruiter | 2025-03-28 (Fri) | Candidate B |

## Summary

Two candidates reviewed. Candidate B received a unanimous offer decision (L5 mid-band). Candidate A will have one additional leadership-focused interview before a final decision. Both action items have clear owners and deadlines within the week.
```
