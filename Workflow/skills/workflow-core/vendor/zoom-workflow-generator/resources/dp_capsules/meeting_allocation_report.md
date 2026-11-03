---
name: meeting_allocation_report
description:
  Analyze meeting data to classify meetings by type (External, Team, 1:1, Cross-team),
  calculate time allocation, and summarize achievements and blockers. Generate the report as DP
  output, and email it only when the workflow task explicitly requests email delivery to a
  grounded recipient. Use for meeting-allocation analysis and periodic meeting reports.
version: "1.0"
required_tools:
  - zm.meeting.meeting.get_meeting_summary
  - zm.connector_mcp.zm_gmail.gmail_send_email
---

# Meeting Allocation Report

## When to Use

- User asks about meeting time distribution or allocation
- User wants a weekly/daily meeting summary or productivity report
- User asks to classify or categorize their meetings
- User wants to know key achievements or blockers from meetings

## Workflow

### Required execution-state contract

- If the meeting search returns no usable meetings, stop without generating a fake report and make
  no Gmail call. Set `has_data=false`, `delivery_succeeded=false`, `fallback_required=false`, and
  `report_html=""`.
- Never turn "no data" into a delivery failure or fallback branch.
- Email is opt-in. Generate report output only unless the task explicitly asks to email it to an
  explicit or trigger-grounded recipient. Do not infer the requester, host, attendees, or
  stakeholders as recipient.
- `delivery_succeeded=true` only when Gmail confirms the requested action.
- `fallback_required=true` only when `has_data=true`, a report was generated, email delivery was
  explicitly requested, and the Gmail call failed. It is false after successful delivery, when no
  delivery was requested, and when no data exists.

### Step 1: Determine Time Range

Identify the `period_type` from user input and compute the exact date range. Default to `weekly` (current Mon–Sun) if unspecified.

| User Input | `period_type` | Date Range |
|---|---|---|
| "this week" / "last week" / specific week | `weekly` | 7 days, Mon–Sun |
| "last 2 weeks" / "bi-weekly" / "biweekly" | `biweekly` | 14 days |
| "this month" / "last month" / "April" / "2026-04" | `monthly` | Full calendar month (~28–31 days) |
| "this quarter" / "Q1 2026" / "last quarter" | `quarterly` | 3 calendar months (~90 days) |

### Step 2: Fetch Meeting Data

Use the `search_meeting` to retrieve all meetings the current user actually attended within the time range. Include meeting topic, participants, start/end time, and meeting summary/content.

### Step 3: Classify Each Meeting

Tag every meeting with exactly one type using these rules (evaluate in order):

| Type | Rule |
|------|------|
| **1:1** | Exactly 2 participants (including the user) |
| **External** | Any participant is from outside the user's organization (different email domain) |
| **Cross-team** | 3+ internal participants from different teams/departments (infer from titles, org info, or meeting context) |
| **Team** | All other meetings (same team, internal, 3+ people) |

When classification is ambiguous, use the meeting topic and context as tiebreakers. If still unclear, default to **Team**.

### Step 4: Calculate Time Allocation

Produce a summary table with:

- Total number of meetings in the period
- For each type: count, total duration (hours), and percentage of total meeting time
- A time breakdown at the appropriate granularity for the period:

| `period_type` | Breakdown granularity | `daily` dict keys |
|---|---|---|
| `weekly` | Per day (7 entries) | `YYYY-MM-DD` |
| `biweekly` | Per day (14 entries) | `YYYY-MM-DD` |
| `monthly` | Per day (all days; chart auto-groups by ISO week) | `YYYY-MM-DD` |
| `quarterly` | Per day (all days; chart auto-groups by month) | `YYYY-MM-DD` |

**Output format example:**

```
📊 Weekly Meeting Time Allocation (2026-04-06 ~ 2026-04-10)

Total meetings: 18 | Total duration: 14.5h

Type          | Count | Hours   | Share
-------------|-------|---------|-------
1:1          | 6     | 3.0h    | 20.7%
Team         | 5     | 4.5h    | 31.0%
External     | 4     | 4.0h    | 27.6%
Cross-team   | 3     | 3.0h    | 20.7%
```

### Step 5: Generate Executive Summary

Write a one-sentence executive summary (≤100 characters) that captures the overall meeting time allocation picture. It must include:
- **Key data**: total meetings, total hours, and the dominant meeting type with its percentage
- **An opinion/observation**: a clear judgment about the time allocation pattern (e.g. whether it's healthy, imbalanced, or needs attention)

**Good examples:**
> This week included 16 meetings totaling 11.8h, with Cross-team taking the largest share at 34%, so reducing cross-team load could protect focus time.

> This week had only 12 meetings totaling 8.2h, with 1:1s at 40%, which looks like a healthy balance for team communication.

**Bad examples (no opinion or no data):**
> There were many meetings this week across several types. (No data)
> This week had 16 meetings totaling 11.8h, including 4h of Cross-team and 2.8h of External meetings. (No opinion)

### Step 6: Summarize Content (Key Achievements & Challenges)

Use the **nlp skill** to analyze meeting content and extract:

**Key Achievements** (≤150 characters total):
- List specific, concrete accomplishments from the meetings
- Name actual deliverables, decisions made, or milestones reached
- Do NOT use abstract language like "improved collaboration" or "made progress"

**Challenges and Blockers** (≤150 characters total):
- List specific, concrete problems or blockers surfaced in meetings
- Name actual issues, dependencies, or risks
- Do NOT use abstract language like "resource constraints" or "alignment needed"

**Good example:**
> Key Achievements: Completed the Q2 pricing review; signed an LOI with Acme; launched the new login page and passed QA.

**Bad example (too abstract):**
> Key Achievements: Moved several projects forward; improved cross-team collaboration; enhanced the product experience.

### Step 7: Extract Top Business Keywords from Transcripts

Use the **nlp skill** to analyze all meeting transcripts from the time range and extract the Top 10 most frequent business-related keywords/phrases.

Rules:
- **Include**: product names, feature names, technical terms, project names, business metrics, client/partner company names, tools, methodologies
- **Exclude**: person names (first/last names), common filler words, greetings, pronouns, generic verbs (e.g. "discuss", "think", "say", "review"), time expressions, meeting logistics words
- Count frequency across all transcripts combined
- Group synonyms/variants (e.g. "AI Search" and "Smart Search" count as one)
- For each keyword, also note which meeting type(s) it appeared in most

Output format — a list of keyword objects, sorted by frequency descending:

```json
[
  {"rank": 1, "keyword": "Smart Search", "count": 12, "context": "Core product capability mentioned in Design Review and Sprint Planning"},
  {"rank": 2, "keyword": "API Integration", "count": 8, "context": "Core requirement in the Acme Corp partnership plan"}
]
```

Rules:
- Exactly 10 keywords
- Each `context` ≤ 50 characters, briefly explain the keyword's business relevance
- Use the user's language

### Step 8: Generate Optimization Suggestions

Analyze the meeting data from Steps 3–5 and produce 3–5 actionable suggestions to optimize meeting productivity. Each suggestion must be specific and data-backed — reference actual numbers from the analysis.

Evaluate these dimensions (skip any that don't apply):

| Signal | Trigger condition | Example suggestion |
|--------|------------------|--------------------|
| **Meeting overload** | Total hours > 40% of work hours in the period (weekly: >16h/40h; biweekly: >32h/80h; monthly: >64h/160h; quarterly: >192h/480h) | "Meetings took X% of work hours this period; review which ones can be merged or handled async." |
| **Type imbalance** | Any single type > 40% of total time | "External meetings accounted for 66.7% (4.0h); check whether every session requires your attendance." |
| **Too many 1:1s** | 1:1 count > 5/week (biweekly: >10; monthly: >20; quarterly: >60) | "You had X 1:1s this week; consider moving lower-priority ones to biweekly or merging into a group sync." |
| **Long meetings** | Any meeting > 1.5h | "X meetings ran longer than 1.5 hours; consider a 50-minute cap and tighter agendas." |
| **Back-to-back** | 3+ consecutive meetings with no gap (weekly/biweekly only) | "3 back-to-back meetings on Day X; add a 10-minute break between sessions." |
| **Uneven load** | Busiest unit > 2× lightest unit (weekly/biweekly: per day; monthly: per week; quarterly: per month) | "Week X had 4.0h while Week Y had only 1.0h; spread some meetings to lighter weeks." |
| **Low-value recurring** | Same topic appears 2+ times within a week | "Weekly Standup appeared twice this week; merge into one session to save 0.5h." |

Output format — a list of suggestion objects:

```json
[
  {"icon": "⏰", "title": "Meeting time is on the high side", "detail": "Meetings took 11.8h this week, or 29.5% of work time. Review whether all Cross-team sessions (4h / 34%) require you."},
  {"icon": "🔄", "title": "Trim duplicate standups", "detail": "Weekly Team Standup appeared twice this week (Monday and Thursday). Merge it into one weekly session to save 0.5h."}
]
```

Rules:
- Each suggestion ≤ 80 characters for title, ≤ 150 characters for detail
- Must cite specific data (hours, percentages, meeting names)
- Prioritize high-impact suggestions first
- Use the user's language (Chinese or English based on their request)

### Step 9: Generate Report HTML and, Only When Requested, Email It

Generate a polished, self-contained HTML report directly from the analysis. Do not call a
script, read a Skill resource, or assume a filesystem. Preserve an internal structure equivalent to:

```json
{
  "user_name": "Example User",
  "period": "2026-04-06 ~ 2026-04-10",
  "period_type": "weekly",
  "total_meetings": 16,
  "total_duration_h": 11.8,
  "by_type": {
    "1:1":        {"count": 5, "duration_h": 2.8, "percentage": 23.4},
    "Team":       {"count": 4, "duration_h": 2.2, "percentage": 19.1},
    "External":   {"count": 3, "duration_h": 2.8, "percentage": 23.4},
    "Cross-team": {"count": 4, "duration_h": 4.0, "percentage": 34.0}
  },
  "daily": {
    "2026-04-06": {"1:1": {"count": 1, "duration_h": 0.5}, "Team": {"count": 1, "duration_h": 0.5}}
  },
  "executive_summary": "One-sentence summary, <=100 characters, with data and an opinion",
  "key_achievements": "Specific achievements, <=150 characters",
  "challenges_blockers": "Specific challenges, <=150 characters",
  "optimization_suggestions": [
    {"icon": "⏰", "title": "Suggestion title", "detail": "Specific recommendation with supporting data"}
  ],
  "top_keywords": [
    {"rank": 1, "keyword": "Smart Search", "count": 12, "context": "Core product capability mentioned repeatedly in design and planning meetings"}
  ]
}
```

Build the HTML with presentation tables and inline CSS: a header with totals, executive-summary
card, meeting-type table, daily breakdown table, achievements and blockers, Top 10 keyword table,
and optimization cards. Use a responsive white card on `#F7F9FA`, maximum width 720px, no external
CSS/JavaScript/fonts/images, and keep the document under 100 KB. Store it in `report_html`. Only when
the workflow task explicitly requests email delivery to a grounded recipient, pass that string
directly as the email body:

```json
{
  "tool": "zm.connector_mcp.zm_gmail.gmail_send_email",
  "params": {
    "recipient_email": "<user_email>",
    "subject": "Meeting Allocation Report (Apr 12-18, 2026)",
    "body": "<self-contained HTML string>",
    "is_html": true,
    "user_id": "me"
  }
}
```

`"is_html": true` must be a JSON boolean (not the string `"true"`), so the framework skips markdown conversion and sends the HTML as-is.

Treat the output as email content, not as a browser-only page. Do not claim it was sent unless the
send tool returns a successful result.

### Required outputs

Populate every declared output:

- `response` (string): concise analysis/delivery summary or the no-data reason.
- `has_data` (boolean): true only when usable meetings were found for the requested period.
- `delivery_succeeded` (boolean): true only after confirmed requested email success.
- `fallback_required` (boolean): true only for a generated report whose requested email failed.
- `report_html` (string): generated self-contained report HTML, or empty when `has_data=false`.

Downstream branches must use these booleans, never the non-emptiness or wording of `response`.
