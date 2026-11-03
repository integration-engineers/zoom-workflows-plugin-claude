---
name: interview-feedback-consolidator
description: Consolidate interview feedback from meeting transcripts into a structured hiring debrief report. Extracts each interviewer's assessment, candidate strengths, concerns with supporting evidence, and recommended next steps. Use this skill whenever the user pastes or uploads an interview transcript, debrief recording, hiring panel discussion, or asks to summarize interview feedback, write a hiring debrief, consolidate interviewer notes, or generate a candidate assessment report. Also trigger when the user mentions "interview summary", "hiring debrief", "candidate feedback", "panel debrief", "interviewer notes", or phrases like "summarize the interview", "what did the panel think", "consolidate feedback from the interviews", even if they don't explicitly say "interview feedback consolidator".
version: "1.0"
tags:
  - meetings
  - hiring
  - HR
required_tools:
---

# Interview Feedback Consolidator

Turn raw interview transcripts and debrief recordings into a clear, actionable hiring report that any stakeholder can read in under 2 minutes.

## Why This Matters

After every interview loop, recruiters and hiring managers face the same problem: scattered notes, vague impressions, and no single source of truth. This skill solves that by extracting signal from noise — pulling concrete evidence from conversational transcripts and organizing it into a structured assessment that drives faster, better hiring decisions.

## Input

Accept any of the following:
- Raw interview transcript (text, .txt, .docx, .pdf)
- Debrief meeting recording transcript
- Multiple interviewer feedback notes pasted together
- A single interviewer's feedback transcript

If the input is a file path, read the file first using the appropriate tool.

## Language Detection

Detect the primary language of the input transcript. Produce the entire output report in that same language. The only exception: if the user explicitly requests a specific output language, honor that request.

## Extraction Process

### Step 1 — Identify Participants

Scan the transcript for speaker labels, name mentions, and role references. Build a participant roster:
- **Interviewers**: name, role/title if mentioned, interview focus area (technical, behavioral, culture fit, hiring manager screen, etc.)
- **Candidate**: name, role applied for

If speaker labels are missing or ambiguous, infer from context (e.g., "As the hiring manager, I think…") and note any uncertainty.

### Step 2 — Extract Per-Interviewer Assessments

For each interviewer, extract:

| Dimension | What to Look For |
|-----------|-----------------|
| **Overall Signal** | Explicit hire/no-hire/lean-hire/lean-no-hire recommendation, or infer from tone and language |
| **Strengths** | Positive observations about the candidate — skills, experience, traits, cultural alignment |
| **Concerns** | Reservations, red flags, skill gaps, cultural misfit signals |
| **Evidence** | Concrete examples, candidate quotes, or behavioral observations that support each strength or concern. Paraphrase rather than quoting at length. |
| **Confidence Level** | How certain the interviewer seemed: High / Medium / Low — based on language hedging, qualifiers, and decisiveness |

Extraction principles:
- Prioritize concrete behavioral evidence over general impressions ("She walked through a system design for a rate limiter" > "She's technically strong")
- Distinguish between first-hand observations and hearsay ("I noticed…" vs. "I heard from the recruiter that…")
- Capture dissenting opinions — disagreements between interviewers are high-signal
- Note if an interviewer explicitly deferred judgment or had insufficient data

### Step 3 — Synthesize Cross-Interviewer Themes

After individual extraction, identify patterns across all interviewers:
- **Consensus strengths**: areas where multiple interviewers aligned positively
- **Consensus concerns**: recurring worries or flags
- **Split opinions**: dimensions where interviewers disagreed — these deserve extra attention
- **Blind spots**: areas no interviewer covered or had data on

### Step 4 — Determine Recommended Next Steps

Based on the overall signal, suggest concrete next steps. Choose from (or combine):
- Extend offer / proceed to offer stage
- Additional interview round (specify focus area)
- Reference check with specific questions to probe
- Hiring manager deep-dive on a specific concern
- Pass on candidate (with rationale)
- Hold for a different role that may be a better fit

## Output Format

Produce a single Markdown document using the exact structure below. Keep language crisp and professional — every sentence should carry information. Avoid filler.

```
# Interview Feedback Report

**Candidate:** [Name]
**Position:** [Role]
**Interview Date:** [Date if mentioned, otherwise "Not specified"]
**Report Generated:** [Today's date]

---

## Overall Recommendation

[One sentence: the aggregate signal — e.g., "Strong hire with minor concerns around X" or "Lean no-hire due to consistent gaps in Y."]

| Interviewer | Role / Focus | Signal | Confidence |
|-------------|-------------|--------|------------|
| [Name] | [Area] | [Hire / Lean Hire / Lean No-Hire / No-Hire] | [High/Med/Low] |
| ... | ... | ... | ... |

---

## Consensus Strengths

[Bulleted list. Each bullet: one strength + supporting evidence from one or more interviewers. Keep each bullet to 1-2 sentences.]

## Consensus Concerns

[Same format as strengths. Each concern + evidence.]

## Split Opinions

[If any. Describe the disagreement, who held which view, and why. This section is critical for hiring managers — don't skip it if disagreements exist.]

## Blind Spots

[Areas not covered. If none, write "All key areas were assessed."]

---

## Per-Interviewer Detail

### [Interviewer Name] — [Focus Area]

**Signal:** [Hire / Lean Hire / Lean No-Hire / No-Hire] | **Confidence:** [High/Med/Low]

**Strengths:**
- [Strength + evidence]

**Concerns:**
- [Concern + evidence]

**Key Quotes / Observations:**
- [Notable paraphrased observations — max 3]

[Repeat for each interviewer]

---

## Recommended Next Steps

[Numbered list of 1-3 concrete actions with rationale.]

---

*This report was generated from an interview transcript. Verify critical assessments with the original interviewers before making final hiring decisions.*
```

## Edge Cases

- **Single interviewer**: Skip the "Consensus" and "Split Opinions" sections. Focus on the per-interviewer detail and next steps.
- **Unclear recommendations**: If an interviewer didn't state a clear hire/no-hire signal, mark as "Not Stated" and note what they did say.
- **Off-topic discussion**: Ignore portions of the transcript unrelated to candidate assessment (logistics, scheduling, small talk).
- **Partial transcript**: If the transcript appears incomplete, note this at the top of the report and flag which interviewers may have missing data.
- **Multiple candidates discussed**: If the transcript covers multiple candidates, produce a separate report section for each candidate, clearly delineated.

## Quality Checklist

Before finalizing the output, verify:
- [ ] Every strength and concern is backed by specific evidence, not just an adjective
- [ ] The overall recommendation is consistent with the per-interviewer signals
- [ ] Split opinions are captured, not smoothed over
- [ ] The output language matches the input transcript language
- [ ] The report is scannable — a hiring manager can get the full picture in under 2 minutes
