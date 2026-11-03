---
name: summary_meeting
description: "Analyzes meeting transcripts and generates structured summaries using a single best-fit template (Decision, Lecture, Interview, Clinical, Sales, Legal, etc.). Fetches meeting content via tab context or RAG search, then writes the summary to a document in Zoom Canvas Doc, Google Doc, or Microsoft Doc as requested."
version: "1.0"
required_tools:
  - zm.aic.tool.search_meeting
  - zm.aic.tool.get_meeting_summary
  - zm.doc.doc.create_zoom_doc
  - zm.doc.doc.update_zoom_doc
  - zm.aic.tool.search_zoom_doc
  - zm.connector_mcp.zm_googledocs.googledocs_create_document
  - zm.connector_mcp.zm_googledocs.googledocs_update_document_markdown
---

# Summary Meeting Skill

## Core Principle

**Ground the summary in the transcript only.** Do not invent, infer, or assume facts. Populate fields only from explicitly stated content. When the user wants the summary written to a document, use the appropriate tool for Zoom Canvas Doc, Google Doc, or Microsoft Doc and pass the generated summary as the document content.

## Context Available to You

- **Focused tab** — If the user is viewing a meeting (current or past), that meeting may be the “focused entity” for retrieval.
- **Conversation history** — Any meeting ID, meeting title, or time reference the user mentioned.
- **User request** — Whether they want the summary in chat only, or written to a specific document in Zoom Canvas Doc, Google Doc, or Microsoft Word.

---

## Summary Meeting Flow

### Step 1: Obtain Meeting Content (Input)

You need the **meeting transcript or full meeting content** to generate the structured summary. Use one of the following tools depending on context.

#### Option A: User refers to a recent or specific past meeting (e.g. “Summarize this meeting”, “Summarize the standup from last Tuesday”)

**Tools: `zm.aic.tool.search_meeting` → `zm.aic.tool.get_meeting_summary`**

- **When to use:** The user says “summarize this meeting”, “summarize the call with [company]”, or refers to any meeting by topic, participant, or date.
- **Step 1:** Call `search_meeting` to locate the meeting.

```
Call search_meeting with:
  query: <meeting topic, company name, or description>
  tense: “past”
  limit: 1
  sort_by_time: “desc”
  [participants: [<email>] if a specific participant is mentioned]
  [start_time / end_time if a date range is specified]
```

- **Step 2:** Extract the `meeting_number` (integer ID) from the returned meeting record.
- **Step 3:** Call `get_meeting_summary` with that ID to retrieve the meeting recap.

```
Call get_meeting_summary with:
  meetingId: <meeting_number from search_meeting result>
```

#### Option B: User provides a meeting ID directly

**Tool: `zm.aic.tool.get_meeting_summary`**

- **Parameters:** `meetingId` (required): The meeting ID (integer) of the meeting.
- **When to use:** When you have a meeting ID and the user only needs the **existing** Zoom AI-generated summary (highlights, decisions), not a new template-based summary. For the **structured template-based summary** (Templates 1–13), prefer Option A to search and retrieve full content. Use this directly when the user explicitly provides a numeric meeting ID and asks for “the meeting summary” without a specific template.

```
Call get_meeting_summary with:
  meetingId: <numeric meeting ID>
```

**Handling results:**

| Scenario | Action |
|----------|--------|
| User says “summarize this meeting” or names a meeting topic/company | Use **search_meeting** to find it, then **get_meeting_summary** for the content. |
| User refers to a past meeting by topic/date | Use **search_meeting** with `query` = topic, `tense: “past”`, then **get_meeting_summary**. |
| User provides a meeting ID and wants “the summary” | Use **get_meeting_summary** directly. |
| search_meeting returns no results | Ask: “I couldn’t find that meeting. Can you provide the meeting ID or a more specific description?” |
| No meeting content returned | Tell the user: “I couldn’t retrieve content for that meeting. Please share the meeting ID.” |

---

### Step 2: Generate the Structured Summary (Template Rules)

Using the meeting content from Step 1, produce a **single** structured summary that follows the rules and one template below.

#### GLOBAL RULES (apply to all templates)

- **Template selection (internal):** Choose exactly **one** template (1–13) that best matches the meeting’s primary intent. Do **not** mention the template name or selection logic in the output.
- **Fact handling:** Do not invent, infer, normalize, or assume facts. Populate fields only when explicitly stated in the transcript. If information is missing, leave the field blank or use “Unclear / Not discussed” (in the locked output language).
- **Structure:** Follow only the chosen template’s structure. Keep all required sections. Optional sections may be omitted if no relevant information exists. Maintain section order and hierarchy.
- **Timestamp normalization (when timestamps are used):** All timestamps must be **relative to meeting start**. Meeting start = 00:00:00. Use format **HH:MM:SS** (zero-padded). Do **not** use absolute clock time (e.g. 09:30, 14:45). Convert any absolute timestamps in the transcript to relative time when possible; if not reliable, omit the timestamp.
- **Language:**
  1. **Determine transcription language** — Identify the language(s) in the transcript. If one language dominates, lock that as the output language.
  2. **Language lock** — Keep the output language fixed for the entire response; do not switch mid-output.
  3. **Template language override** — Translate all section titles, labels, and boilerplate into the locked output language. Do not leave template wording in another language.
  4. **Content rules** — Render all narrative in the locked output language. Do **not** translate: proper nouns, personal names, company names, product names, or quoted speech (keep verbatim).
  5. **Mixed-language transcripts** — Use the dominant language for structure and narration; keep original language only for verbatim quotes and proper nouns.
- **Output discipline:** Do not explain reasoning, template choice, or internal processes in the output.

#### TEMPLATES (structure-only)

- **Template 1 — Decision / Action Meeting:** Meeting Overview, Executive Summary, Key Decisions, Action Items (table), Discussion Topics (ordered, timestamped), Open Questions.
- **Template 2 — Lecture:** Lecture Information, Learning Objectives, Core Content (Definition / Key Ideas / Examples), Key Takeaways, Connections, Summary Outline, Exam Tips (optional).
- **Template 3 — Action-Focused Conversation:** Action Items, Follow-Ups, Priority Signals, Context Snapshot, Key Details Extracted, Notes.
- **Template 4 — Job Interview:** Interview Details, Interview Overview, Candidate Snapshot, Experience Overview, Work Expectations, Capabilities, Concerns, Experience Deep Dives, Q&A Highlights, Follow-Ups, Next Steps.
- **Template 5 — SOAP Clinical Note:** Visit Information, Diagnostic History, Subjective, Objective, Assessment, Plan, Additional Notes.
- **Template 6 — Social Work Consultation:** Encounter Information, Reason for Consult, Psychosocial History, Assessment of Needs, Interventions Provided, Referrals, Care Plan & Follow-Up, Recommendations.
- **Template 7 — Psychotherapy Process Note:** Session Information, Presenting Focus, Background & Context, Mental & Emotional Status, Therapeutic Focus & Interventions, Clinical Reflections, Treatment Direction, Next Session.
- **Template 8 — Therapy Session Notes:** Session Context, Key Themes & Emotional Tone, Significant Content, Patterns & Coping, Insights, Therapeutic Interventions, Concerns & Needs, Agreements & Next Steps, Therapist Reflection (optional).
- **Template 9 — Medical Consultation:** Encounter Information, Reason for Consultation, History of Present Illness, Review of Systems, Past Medical History, Medications & Allergies, Objective Findings, Assessment & Impression, Plan & Recommendations, Summary for Referring Provider.
- **Template 10 — MEDDICC Deal Qualification:** Deal Overview, Executive Deal Summary, Metrics, Economic Buyer, Decision Criteria, Decision Process, Identify Pain, Champion, Competition, Scoring Model, Deal Risks & Gaps, Next Steps.
- **Template 11 — Customer Conversation:** Meeting Information, Highlights, Customer Context, Needs & Goals, Discussed Products, Solution Direction, Technical Requirements, Objections & Risks, Follow-Ups & Next Steps, Deal Risk Scoring, Manager Review Summary.
- **Template 12 — Legal Meeting Record:** Meeting Metadata, Scope & Purpose, Executive Legal Snapshot, Topics Discussed, Decisions & Legal Positions, Legal Risks, Action Items, Open Issues, References, Disclaimer, Document Control.
- **Template 13 — Financial Advisor Client Review:** Review Type, Meeting Purpose, Client Profile & Suitability Update, Discussion Highlights, Advisor Recommendations, Client Decisions, Disclosures, Action Items, Compliance Notes, Open Items.

#### OUTPUT FORMAT (strict)

- **Title:** Use the explicit meeting title if stated in the transcript; otherwise generate a concise, neutral title in the locked output language reflecting the meeting’s primary purpose.
- **Summary:** Render the full summary using the chosen template’s sections and formatting. Entire output must be in the locked output language.

---

### Step 3: Write Summary to a Document (Output)

If the user asks to save the summary to a document, choose the right tool based on destination: Zoom Canvas Doc, Google Doc, or Microsoft Doc.

#### Option A: Zoom Canvas Doc (accept requests that say “Zoom Canvas”, “Zoom Doc”, or “save to Zoom”)

**Create a new Zoom Canvas Doc with the summary:**

**Tool: `zm.doc.doc.create_zoom_doc`**

- `doc_name` (required): Document name (e.g. “Meeting Summary – Q1 Review”).
- `content` (required): The **full summary text** in Markdown format.
- `parent_directory` (optional): Object with `id` and `title` of the parent space or folder; omit to save in the default location.

```
Call create_zoom_doc with:
  doc_name: “Meeting Summary - <title or date>”
  content: “<full summary text in locked output language, Markdown>”
```

**Update an existing Zoom Canvas Doc:**

**Tool: `zm.doc.doc.update_zoom_doc`**

- `doc.doc_id` (required): The Zoom document ID to update.
- `doc.doc_title` (required): The title of the document.
- `content` (required): The new summary content (Markdown).
- `mode` (optional): `”overwrite”` to replace existing content (default behavior).

Use when the user specifies an existing Zoom Canvas Doc to update (e.g. by name or ID). If you do not have the doc ID, use `zm.aic.tool.search_zoom_doc` with a query to find the doc and obtain its ID, then call `update_zoom_doc`.

#### Option B: Google Doc

**Create a new Google Doc with the summary (with content):**

**Tool: `zm.connector_mcp.zm_googledocs.googledocs_create_document`** (3P)

- `title` (required): Document title (e.g. “Meeting Summary – Feb 20”).
- `text` (optional): **Initial text** — pass the full summary here so the doc is created with content.

```
Call googledocs_create_document with:
  title: "Meeting Summary - <title or date>"
  text: "<full summary text>"
```

**Update an existing Google Doc with the summary:**

**Tool: `zm.connector_mcp.zm_googledocs.googledocs_update_document_markdown`** (3P)

- `id` (required): Google Doc ID (from URL: `https://docs.google.com/document/d/{id}/edit`).
- `markdown` (required): The summary in Markdown (replace entire document content).

Always use **googledocs_create_document** with the `text` parameter to create a Google Doc with content already populated. If the user provides a Google Doc URL/ID to update, use **googledocs_update_document_markdown** instead.

**Handling results:**

| User says | Action |
|-----------|--------|
| “Save to Zoom Canvas” / “Put this in a Zoom Doc” | Interpret the alias as Zoom Canvas Doc and use **create_zoom_doc** with `doc_name` = title and `content` = summary (Markdown). |
| “Add to existing Zoom Canvas Doc [name]” | Use **search_zoom_doc** to get doc ID and title, then **update_zoom_doc** with `doc.doc_id`, `doc.doc_title`, and `content`. |
| “Save to Google Doc” / “Create a Google Doc” | Use **googledocs_create_document** with `title` and `text` = summary. |
| “Update this Google Doc” (with link/ID) | Use **googledocs_update_document_markdown** with `id` and `markdown` = summary. |
| “Save to Word” / “Microsoft Doc” / “OneDrive” | No Microsoft Drive tool is available. Output the full summary in chat and tell the user: “Microsoft Word export is not supported — here is the full summary for you to copy.” |

---

## Decision-Making Rules

### When to use which input tool

| Situation | Tool to use |
|-----------|-------------|
| “Summarize this meeting” or names a meeting topic/company | **search_meeting** to find it, then **get_meeting_summary** for the content. |
| “Summarize the standup from last Tuesday” | **search_meeting** with `query` = “standup”, `tense: “past”`, `start_time`/`end_time` for the date, then **get_meeting_summary**. |
| “What was the summary of meeting 12345?” | **get_meeting_summary** directly with `meetingId: 12345`. |

### Error recovery

| Error | Recovery |
|-------|----------|
| search_meeting returns no results | Refine query or ask: “I couldn’t find that meeting — can you provide the meeting ID or a more specific description?” |
| get_meeting_summary returns no content | Confirm user has access to that meeting; ask for the correct meeting ID. |
| User wants summary in a doc but doesn’t specify which | Prefer Zoom Canvas Doc (**create_zoom_doc**) if in Zoom context; otherwise ask: “Should I save this in Zoom Canvas Doc or Google Docs?” |
| Google create returns no document ID | Use **googledocs_create_document** with `text` so content is in the doc immediately. |

### Complete example: “Summarize this meeting and save it to Zoom Canvas Doc”

1. **Step 1** — Call **search_meeting** with `query` = inferred topic, `tense: “past”`, `limit: 1`, `sort_by_time: “desc”`. Extract `meeting_number`. Then call **get_meeting_summary** with that ID.
2. **Step 2** — Determine dominant language and best-fit template (e.g. Template 1 — Decision/Action). Generate the structured summary (Title + Summary) following global rules. Do not mention the template.
3. **Step 3** — Call **create_zoom_doc** with `doc_name` = e.g. “Meeting Summary – &lt;meeting title or date&gt;” and `content` = the full summary text (Markdown).
4. Confirm to the user: “I’ve created a meeting summary and saved it as ‘&lt;doc_name&gt;’ in Zoom Canvas Doc.”
