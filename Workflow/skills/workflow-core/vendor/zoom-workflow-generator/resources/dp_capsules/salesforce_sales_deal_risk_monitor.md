---
name: salesforce_sales_deal_risk_monitor
description: Identifies grounded deal-risk signals from customer calls or internal deal-review meeting content, safely updates one uniquely matched Salesforce Opportunity, and creates a Google Doc risk report. External delivery by email or chat is a separate operation and is not performed by this capsule. Use for deal health checks, post-meeting risk scans, competitor/budget/champion/timeline/legal/procurement signals, and escalation analysis.
version: "1.0"
tags:
  - salesforce
  - crm
  - automation
  - meetings
  - workflow_planner
required_tools:
  - zm.connector_mcp.zm_salesforce.salesforce_get_user_info
  - zm.connector_mcp.zm_salesforce.salesforce_get_all_fields_for_object
  - zm.connector_mcp.zm_salesforce.salesforce_search_opportunities
  - zm.connector_mcp.zm_salesforce.salesforce_get_s_object_record
  - zm.connector_mcp.zm_salesforce.salesforce_update_a_record
  - zm.connector_mcp.zm_googledocs.googledocs_create_document
---

# Deal Risk Monitor

## Overview

Scans unstructured meeting content to identify 6 categories of deal risk signals, produces a severity-scored risk report, and executes two downstream actions:
1. Writes risk flags into the Salesforce Opportunity record
2. Generates a Google Doc risk report per meeting

Email, Slack, or Zoom Chat delivery is outside this capsule. The workflow planner must add a
separate delivery step only when the user requested one, with an explicit recipient and a typed
`report_created=true` gate.

---

## ⛔ Scope Check: Identify Usable Deal Content First

**Before anything else, determine whether the meeting contains grounded sales or customer-success
deal content where deal-level risk scanning applies. Decide from the meeting content, not from the
participants' employer or `is_internal` values.**

### Skip entirely (do not run Salesforce writes or Google Doc creation) for:

- Team standups, department syncs, project check-ins, or engineering reviews with no grounded
  customer, account, Opportunity, or deal-risk content
- 1:1 management conversations, all-hands, training, onboarding, or town halls with no deal content
- Product, marketing, HR, or other cross-functional discussions unrelated to a customer/prospect,
  active account, Opportunity, or deal decision
- Content that is not a meeting transcript or summary (see guardrail: no meeting content)

If any of the above apply, respond with:

> "This meeting does not contain usable sales or customer-success deal content for Deal Risk Monitor. No Salesforce update or risk report was created."

Do **not** call Salesforce update tools or `googledocs_create_document` for these cases.

### Proceed with analysis for:

- Sales cold calls or follow-up calls with a prospect or customer
- Customer demos, pricing, or contract discussions
- Customer support or after-sales calls tied to an account or deal
- Customer Success conversations such as QBRs, renewals, or escalation calls
- Internal account, pipeline, or deal reviews that explicitly identify a customer/account or
  Opportunity and contain attributable customer feedback or grounded deal-risk signals

Unless the saved task explicitly requires an external attendee, an internal participant roster is not
disqualifying. A current internal review may report evidence from an earlier customer interaction;
analyze it when the meeting clearly attributes that evidence and ties it to a customer/account or
Opportunity. Label reported evidence accurately and never invent
a customer statement. When usable deal context remains ambiguous, make no write or document side
effect and report the missing evidence; do not infer eligibility from attendance alone.

---

## Workflow

### Step 1 — Identify risk signals

Semantically scan the content for the 6 risk categories below. Tag each identified signal with a severity level.

| Risk category | Signal examples |
|--------------|----------------|
| 🔴 **Competitive threat** | "We're also looking at [competitor]", "their pricing is lower", "two other vendors in the RFP", "already using a competing tool" |
| 🟠 **Budget risk** | "Budget is frozen", "revisit in Q3", "CFO needs to re-approve", "we need to cut scope", "ROI hasn't been proven yet" |
| 🟡 **Champion risk** | "Our champion is leaving", "Sarah might not be on this project", "internally we're not aligned yet" |
| 🟡 **Timeline slippage** | "Can't close this quarter", "waiting for year-end budget", "now isn't a good time", "let's put this on hold" |
| 🟠 **Legal / procurement blocker** | "Contract needs to go through legal", "procurement cycle is long", "security audit required", "data compliance issue" |
| 🔴 **Decision-maker change** | "New VP wants to re-evaluate", "CIO just changed", "our original champion moved to a different team" |

**Severity definitions:**
- 🔴 **High** — Directly threatens close probability this quarter
- 🟠 **Medium** — Slows deal momentum; requires proactive action
- 🟡 **Low** — Latent risk; needs monitoring

**Extraction rules:**
- Only flag risks with explicit evidence from the transcript — do not over-infer
- A single signal may span multiple categories (e.g. "competitor quoted us lower" triggers both Competitive Threat and Budget Risk)
- Always retain the original quote as evidence

---

### Step 2 — Identify and update Salesforce Opportunity

Extract the account name and any project/deal keywords directly from the meeting transcript. Do not ask the user. Use what you find to search Salesforce automatically.

**Extraction targets (from transcript):**
- Company name (e.g. "Meridian HealthTech", "Acme Corp")
- Deal or project name if mentioned
- Contact names that may appear in Opportunity names

**Search using:**
```
zm.connector_mcp.zm_salesforce.salesforce_search_opportunities
  name: [extracted deal/project name when available]
  account_name: [extracted account name when available]
  limit: 5
```

- If exactly one match → preflight-read that returned ID, then use it; no extra confirmation needed.
- If zero or multiple matches → make no Salesforce write and continue to Step 3 without blocking.
- Never choose by first/top result, owner, recency, stage, semantic similarity, or a `best` ranking.

Before writing, call
`salesforce_get_s_object_record(sobject_api_name="Opportunity", record_id="<resolved 006...>", fields="Id,Name,AccountId,Description,NextStep")`.
Use `salesforce_get_all_fields_for_object(object_name="Opportunity")` to confirm that every proposed
field is writable and to resolve optional custom-field API names. Omit an unverified custom field;
never invent one.

**Update using:**
```
zm.connector_mcp.zm_salesforce.salesforce_update_a_record
  api_name: "Opportunity"
  record_id: [exact Id from the unique search and preflight read]
  fields: {"NextStep": "...", "Description": "...", "<verified risk field>": "..."}
```

After the update, read back the same record ID. Set `salesforce_updated=true` only when the tool
confirms success and read-back reflects the requested values. Do not change `Probability` unless the
saved workflow task explicitly requests that field; a general risk-monitor request does not.

**If no Opportunity is found:**
- Do not block. Skip the Salesforce write entirely.
- Note in the Google Doc: `Salesforce: No matching opportunity found — please link manually`.
- Continue to Step 3 (Google Doc) as normal. Keep `salesforce_updated=false`.

**Write strategy (by priority):**

| Field | Content | Notes |
|-------|---------|-------|
| `Risk_Flags__c` | Risk category labels, comma-separated | If this custom field exists |
| `Description` | Append risk summary block | Preserve existing content — append only |
| `NextStep` | Single most urgent action only | Overwrite — SF field is one line |
| `Probability` | Suggest downward adjustment for High risks | Show recommendation; require user confirmation before writing |

**Description append format:**
```
--- Risk Monitor [YYYY-MM-DD] ---
🔴 Competitive threat: Customer evaluating competing vendors. Executive outreach needed.
🟠 Legal blocker: Contract review ~3 weeks. Send MSA template proactively.
Next Steps (all):
  1. [Most urgent action]
  2. [Second action]
  3. [Third action if any]
```

Note: `NextStep` field gets only the single most urgent action. All remaining actions are written into `Description` under "Next Steps (all)" so nothing is lost.


After writing, retrieve and store the Opportunity URL:
```
https://[instance].salesforce.com/[OpportunityId]
```

---

### Step 3 — Generate Google Doc risk report

**Create using:**
```
zm.connector_mcp.zm_googledocs.googledocs_create_document
  title: "Risk Report — [Account Name] — [YYYY-MM-DD]"
  text: [full report body below]
```

**Doc content** (this is also the full report shown to the user):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨  Deal Risk Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋  Summary
  Opportunity     [Opportunity Name]
  Account         [Account Name]
  Meeting date    [YYYY-MM-DD]
  Overall risk    🔴 High / 🟠 Medium / 🟡 Low / ✅ Healthy
  Salesforce      [SF Opportunity URL]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Risk signals identified
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[For each identified risk signal:]
🔴/🟠/🟡 [Risk category] ([Severity])
  Evidence: "[exact quote from transcript]"
  Recommendation: [specific action]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅  No signals found
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Budget risk · Champion risk · Timeline slippage · Decision-maker change

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝  Recommended next steps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. [Most urgent action, targeting highest risk]
  2. [Second action]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Set `report_created=true` only when creation returns a non-empty `documentId`. Construct the canonical
report URL as `https://docs.google.com/document/d/[documentId]/edit` from that confirmed ID; otherwise
leave `report_url` empty and set `report_created=false`.
Display the full Doc content inline in the chat as well, so the user sees the complete report without opening the Doc.

---

### Step 4 — Return typed state for downstream delivery

Do not send email, Slack, or Zoom Chat from this capsule. Populate the required outputs below.
The planner may add a separate user-requested delivery node gated on `report_created isTrue` and
bind `report_url` directly; it must not parse `response` prose to infer success.

## Required outputs

- `response` (string): concise risk-analysis, Salesforce, and Google Doc execution summary.
- `risk_analyzed` (boolean): true only when usable deal-risk meeting content was analyzed.
- `salesforce_updated` (boolean): true only after a uniquely matched Opportunity write is confirmed;
  false when no unique match exists, the meeting is out of scope, or the write fails.
- `report_created` (boolean): true only after Google Docs confirms report creation.
- `report_url` (string): the confirmed shareable Google Doc URL, otherwise an empty string.

No meeting content/out-of-scope meeting: set every boolean false, leave `report_url` empty, and make
no tool call. A report body in memory or non-empty `response` is not proof that the Doc was created.

---

## Overall risk level calculation

| Condition | Overall level |
|-----------|--------------|
| Any 🔴 High signal present | 🔴 High |
| 2+ 🟠 Medium signals, no High | 🟠 Medium |
| 1 🟠 Medium only, or only 🟡 Low signals | 🟡 Low |
| No signals identified | ✅ Healthy |

---

## Typical trigger scenarios

### Scenario A — Auto-trigger on meeting end
```
[Zoom meeting ends]
→ Transcript auto-passed to agent
→ Analyze for risk signals
→ Search SF by extracted account name
→ If exactly one record matches, write the approved non-Probability risk fields
→ Generate Google Doc risk report
→ Return report_created + report_url for any separately requested delivery step
```

### Scenario B — Pipeline review prep
```
User: "Pipeline review tomorrow. Run a risk check
       on last week's TechCorp call."
→ Analyze → Tool-confirm SF update → Generate Doc → Return typed report result
```

### Scenario C — Batch scan across multiple calls
```
User: [pastes 3 meeting transcripts]
      "Any problems across these deals?"
→ Analyze each separately → Sort by severity
→ Tool-confirm SF update per deal → One Doc per deal → Return typed report results
```

---

## Important guardrails

1. **No meeting content** — If no transcript or summary is provided, stop immediately. Do not proceed with any steps.
2. **Scope Check** — Follow **Scope Check** above. If the meeting lacks grounded sales or customer-success deal content, stop immediately; do not run Salesforce writes or create a Google Doc. Unless the saved task explicitly requires an external attendee, never stop solely because all participants are internal.
3. **Don't over-flag** — Standard negotiation language ("can you do anything on price?") is not a High risk signal. Read in context.
4. **Always cite evidence** — Every risk flag must include the original quote. No inferences without textual backing.
5. **Never auto-adjust Probability** — Show the suggested value, but wait for explicit user confirmation before writing. Probability changes affect Forecast roll-ups.
6. **Append, don't overwrite Description** — Preserve existing CRM history. Always add the risk block at the bottom.
7. **Multi-opportunity safety** — If the meeting involves multiple accounts or deals, analyze each separately. One Google Doc per deal.
8. **Tool connection check** — If Salesforce or Google Docs is not connected, complete what's possible and clearly state what was skipped.
