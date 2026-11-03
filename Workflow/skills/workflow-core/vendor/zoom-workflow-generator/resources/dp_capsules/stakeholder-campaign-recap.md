---
name: stakeholder-campaign-recap
description: Automatically generates a structured Stakeholder Campaign Recap from marketing team meeting notes,status updates, or verbal summaries. Output covers five standard sections: Published/Live, In Progress,Planned/Pending, Risks & Blockers, and Next Milestones — ready to share with stakeholders via email,Slack, or as a report attachment.Use this skill whenever the user mentions "summarize the meeting", "sync campaign status", "write a recap","campaign summary", "marketing status update", "stakeholder update", "activity progress report","help me organize today's meeting notes", or "generate a status update".Even if the user simply pastes a block of meeting notes and asks "can you organize this?", this skillmust be triggered.
version: "1.0"
tags:
  - meetings
  - marketing
required_tools:
---

# Stakeholder Campaign Recap Skill

Transforms messy meeting notes or status updates into a clean, professional Stakeholder Campaign Recap.

---

## Core Workflow

### Step 1: Parse the Input

Accept any of the following input formats:
- Raw meeting transcripts (casual, stream-of-consciousness writing is fine)
- Existing status update text
- Verbal campaign progress descriptions from the user
- Mixed formats (e.g., part bullet list, part paragraph)

**If the input is empty or too thin**, proactively ask the user:
- Which campaigns or activities are involved?
- What is the current status of each?
- Are there any firm deadlines or milestones?
- Are there any issues or risks to flag?

---

### Step 2: Extract and Categorize Information

Map all input content to one of the five sections below:

| Section | What belongs here |
|---------|------------------|
| **✅ Published / Live** | Completed, launched, or already-executed campaigns and deliverables |
| **🔄 In Progress** | Actively running, started but not yet complete, under review, or currently live |
| **📅 Planned / Pending** | Scheduled but not started, awaiting approval, queued, or planned for upcoming weeks |
| **⚠️ Risks & Blockers** | Delay risks, resource gaps, dependency blocks, unresolved questions, budget issues |
| **🚀 Next Milestones** | Upcoming key dates, deadlines, decisions needed, or must-dos before the next sync |

**Categorization rules:**
- Each item belongs in exactly one section — choose the most accurate fit
- If a section has no content, explicitly write "None at this time" — do not omit the section
- Preserve specific numbers, dates, and owner names from the original input

---

### Step 3: Generate the Recap Document

Output in **Markdown** using this structure:

```
# 📋 Campaign Recap — [Date or "This Week" / Meeting Topic]

**Prepared by**: [if available]
**Period covered**: [if available]
**Attendees / CC**: [if available]

---

## ✅ Published / Live

- [Campaign name]: [brief status + key data or results]
- ...

---

## 🔄 In Progress

- [Campaign name]: [current progress + owner (if known) + expected completion]
- ...

---

## 📅 Planned / Pending

- [Campaign name]: [planned scope + target start date + dependencies (if any)]
- ...

---

## ⚠️ Risks & Blockers

- [Risk description]: [scope of impact] → Suggested action (if applicable)
- ...

---

## 🚀 Next Milestones

| Date | Item | Owner |
|------|------|-------|
| [date] | [milestone description] | [owner] |
| ...  | ...  | ...   |

---

*Auto-generated recap. Please review and add any missing details.*
```

---

### Step 4: Post-Output Guidance

After generating the recap, proactively let the user know:
1. **What can be edited**: If anything is incorrect or incomplete, they can say so and it will be updated
2. **Suggested next steps** (suggest only — do not execute):
   - Send to stakeholders via email, Slack, or messaging tools
   - Export as a Word document
   - Add items to a project management tool (e.g., monday.com, Asana)

---

## Output Quality Standards

- **Information density**: Each bullet should include "what + current status + key detail (date / owner / metric)"
- **Tone**: Professional and concise — appropriate for non-execution stakeholders (leadership, cross-functional teams)
- **Language**: Match the user's input language by default (English input → English output)
- **Completeness**: All five sections must appear; use "None at this time" when a section is empty
- **Length**: A single recap should fit on one A4 page (roughly 400–700 words)

---

## Edge Case Handling

### Multiple campaigns running in parallel
Group by campaign name within each section — lead with the campaign name, then describe its status.

### Input contains performance metrics (CTR, ROAS, GMV, etc.)
Preserve the exact numbers in the relevant section. Metrics are what stakeholders care about most.

### User wants to update only one section
Support partial updates — regenerate only that section and label it "(Updated)".

### Meeting notes cover multiple topics beyond campaign status
Extract only campaign-relevant content. Briefly note to the user that other topics were omitted.
