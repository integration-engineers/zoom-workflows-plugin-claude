---
name: meeting_to_sf_note
description: Save meeting content as a Salesforce Note attached to an Opportunity or Account. Use this skill whenever the user wants to log, save, record, or write meeting notes into Salesforce — even if they just paste a transcript and say "save this" or "log this to SF". Trigger on phrases like "save meeting to Salesforce", "log meeting notes", "add a note to the opportunity", "write this to SF", "record meeting in CRM", "attach meeting summary to account", or any time raw meeting content needs to be persisted in Salesforce. Do NOT modify Opportunity fields — this skill writes Notes only.
version: 3.0.0
required_tools:
  - zm.connector_mcp.zm_salesforce.salesforce_get_user_info
  - zm.connector_mcp.zm_salesforce.salesforce_search_accounts
  - zm.connector_mcp.zm_salesforce.salesforce_search_opportunities
  - zm.connector_mcp.zm_salesforce.salesforce_get_opportunity
  - zm.connector_mcp.zm_salesforce.salesforce_create_note
tags:
  - meetings
  - salesforce
  - crm
  - sales
  - automation
---


# Meeting → Salesforce Note

Save structured meeting notes to Salesforce as a Note attached to an Opportunity or Account.

---

## Tools

| Tool | When to use |
|------|-------------|
| `salesforce_get_user_info` | Verify connection and retrieve org instance URL at the start |
| `salesforce_search_opportunities` | Find the target Opportunity by name or keyword |
| `salesforce_search_accounts` | Fallback — find Account if no Opportunity match |
| `salesforce_create_note` | Write the final Note to Salesforce |

---

## Step 1: Verify Connection & Get Instance URL

Call `salesforce_get_user_info` before anything else.

- **Success** → extract the Salesforce **instance URL** (e.g. `https://yourorg.salesforce.com`) from the response and store it — needed to construct the Note URL in Step 5
- **Failure** → stop and return an error:
  ```
  ❌ Salesforce connection unavailable. Please check the zm_salesforce MCP connection.
  ```

---

## Step 2: Structure the Meeting Content

Distill the raw input into a formatted Note body:

```
📅 Meeting Date: YYYY-MM-DD
👥 Attendees: [Name list]
🏢 Client / Organization: [Company name]

📝 Summary
[2–4 sentences capturing the core outcomes of this meeting]

🔑 Key Discussion Points
- [Point 1]
- [Point 2]
- [Point 3]

✅ Next Steps
- [Action item] (Owner / Due date)

⚠️ Risks / Watch-outs
- [Omit section if none]
```

**Formatting rules:**
- Only include information explicitly stated in the meeting — never infer or fabricate
- Convert shorthand amounts (e.g. "500K" → 500,000; "50万" → 500,000)
- Convert relative dates to YYYY-MM-DD based on today's date
- Keep the Note concise — bullet points over paragraphs

---

## Step 3: Compose the Note Title

Format:
```
[Meeting Title] – YYYY-MM-DD
```

- **Meeting Title**: use the title provided in the input (e.g. Zoom meeting topic, calendar event name). If no title is available, fall back to `[Client Name] Meeting`
- **Date**: today's date in `YYYY-MM-DD` format

Examples:
```
Q2 Business Review – 2026-03-18
Acme Corp Kick-off – 2026-03-18
```

---

## Step 4: Identify the Target Record

**If the workflow provides an Opportunity ID** → validate it with
`salesforce_get_opportunity(opportunity_id="<006...>")` and use it only when the returned record is
the intended Opportunity.

**If the workflow provides an Opportunity name** → call
`salesforce_search_opportunities(name="<grounded name>", account_name="<grounded account when available>", limit=5)`.
Continue only when the search returns exactly one matching Opportunity ID. A human-readable name is
never a write target by itself.

**If not provided** → call `salesforce_search_opportunities` with the company name or project
keyword supplied by the workflow, using only the real `name`, `account_name`, and `limit` parameters.
Continue only when the search identifies exactly one matching Opportunity. Do not choose the first,
top, closest, or "best available" result when several records match.

**If no Opportunity match** → call `salesforce_search_accounts` only when the task explicitly
allows an Account fallback, and continue only when exactly one Account matches.

**If there are zero matches, multiple matches, or no explicit permission for an Account fallback**
→ make no write, set `note_created=false`, and stop with:
```
❌ No matching Opportunity or Account found for "[keyword]". Please provide the exact record name or ID.
```

---

## Step 5: Write the Note

Call `salesforce_create_note` with:

```
title:      [composed in Step 3]
body:       [structured note content from Step 2]
parent_id:  [Opportunity.Id or Account.Id from Step 4]
```

**On success**, construct the direct URL to the Note:

```
https://[instance_url]/[note_id]
```

Where:
- `instance_url` = retrieved from `salesforce_get_user_info` in Step 1 (strip trailing slash)
- `note_id` = the Note ID returned by `salesforce_create_note`

Return the following:

```
✅ Note saved to Salesforce
   Record : [Opportunity / Account Name]
   Title  : [Note title]
   URL    : https://[instance_url]/[note_id]
```

**On failure**, return the error message and stop.

Set `note_created=true` only when `salesforce_create_note` confirms the write. A connection check,
search result, formatted Note body, or prose response is not proof of creation.

## Required Outputs

Populate every declared output:

- `response` (string): concise execution summary or the reason no write occurred.
- `note_created` (boolean): true only after Salesforce confirms Note creation.
- `note_info` (string): confirmed record, Note ID/title, and URL; otherwise an empty string.

Downstream nodes must branch on `note_created`, never on non-empty `response` text.

---

## Scope

This skill writes **Notes only**. It does not:
- Update Opportunity fields (StageName, Amount, CloseDate, etc.)
- Create Tasks or Events
- Send emails or Slack messages
