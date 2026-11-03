---
name: jira_issue_ops
description: "Creates, updates, escalates, transitions, and reads/lists Jira issues and tickets — including bugs, tasks, stories, and subtasks. Handles assignee resolution, priority changes, status transitions, comments, watchers, issue links, worklog, attachments, bulk creation from meeting transcripts or chat threads, and reading/listing issues by saved filter URL, specific keys, or JQL criteria (project / assignee / status / time range / etc.). Asks the user for missing critical information when it cannot be confidently inferred. Use for any Jira issue or ticket operation that is NOT sprint/board management, epic management, or project administration."
version: "1.1"
tags:
  - jira
  - ticketing
  - automation
  - meetings
  - workflow_planner
  - issues
  - tickets
  - bugs
  - tasks
  - stories
  - create
  - update
  - assign
  - escalate
  - transition
  - comment
  - attachment
required_tools:
  - zm.connector_mcp.zm_jira.jira_get_fields
  - zm.connector_mcp.zm_jira.jira_get_create_meta_issue_types
  - zm.connector_mcp.zm_jira.jira_get_issue_types_for_project
  - zm.connector_mcp.zm_jira.jira_find_users
  - zm.connector_mcp.zm_jira.jira_search_for_issues_using_jql_post
  - zm.connector_mcp.zm_jira.jira_get_issue
  - zm.connector_mcp.zm_jira.jira_get_transitions
  - zm.connector_mcp.zm_jira.jira_get_all_projects
  - zm.connector_mcp.zm_jira.jira_get_current_user
  - zm.connector_mcp.zm_jira.jira_get_changelogs
  - zm.connector_mcp.zm_jira.jira_list_comments
  - zm.connector_mcp.zm_jira.jira_get_watchers
  - zm.connector_mcp.zm_jira.jira_get_issue_link
  - zm.connector_mcp.zm_jira.jira_get_all_labels
  - zm.connector_mcp.zm_jira.jira_get_project_statuses
  - zm.connector_mcp.zm_jira.jira_get_attachment
  - zm.connector_mcp.zm_jira.jira_create_issue
  - zm.connector_mcp.zm_jira.jira_bulk_create_issues
  - zm.connector_mcp.zm_jira.jira_edit_issue
  - zm.connector_mcp.zm_jira.jira_assign_issue
  - zm.connector_mcp.zm_jira.jira_transition_issue
  - zm.connector_mcp.zm_jira.jira_add_comment
  - zm.connector_mcp.zm_jira.jira_add_watcher
  - zm.connector_mcp.zm_jira.jira_remove_watcher
  - zm.connector_mcp.zm_jira.jira_create_issue_link
  - zm.connector_mcp.zm_jira.jira_delete_issue_link
  - zm.connector_mcp.zm_jira.jira_add_worklog
  - zm.connector_mcp.zm_jira.jira_delete_attachment
  - zm.connector_mcp.zm_jira.jira_delete_issue
---

# Jira Issue Ops

## Non-Negotiable Tool Call Contract

- A Jira tool call with `parameters: {}` is always invalid (see Invariant 4.6). Before every tool call, internally construct the exact argument object. If any required argument name or value is missing, do not call the tool; continue ANALYSIS with a parameterized read/metadata/search tool, ask, block, or defer.
- Read/metadata tools also need arguments. `jira_get_issue` requires `issue_key`; JQL search requires non-empty `jql` and `fields`; project create metadata requires the resolved project key/id. Never call target-specific Jira read or metadata tools with `{}`.
- JQL search must be bounded. A summary/text-only query is not a valid Jira search for this skill. Every `jira_search_for_issues_using_jql_post` call must include at least one hard bound such as `project = KEY`, `key in (...)`, `filter = ID`, or `assignee = currentUser()` plus a non-empty `fields` array. If no hard bound is known, resolve the project/filter/key first or ask; do not run unbounded JQL.
- Write tools may not be called from natural-language context alone. `jira_create_issue` requires `project_key`, issue type, and `summary`; `jira_edit_issue` requires `issue_id_or_key` plus at least one changed field; transition/comment/watch/link/worklog tools require resolved issue keys/ids.
- Field catalog is not the write surface. A custom field may be written only if project + issue-type create/edit metadata says it is present and allowed for that operation. If metadata does not expose the requested field, block or ask before writing; do not create a partial issue.
- Treat an empty tool observation, missing returned Jira key/id, or any "Failed actions" write-tool message as failure evidence. Do not claim an issue write succeeded until a tool observation or read-back returns the issue key and requested fields.

### Update-Existing Resolution Gate

Mandatory order: RESOLVE JIRA KEY/ID -> RESOLVE FIELD/CUSTOM-FIELD EDIT SURFACE -> WRITE. First resolve the live issue key/id with a Jira read/search/get call, then resolve any requested field/custom-field ID, editability, and payload shape from project + issue-type metadata; only after both are resolved may you call an edit, transition, assignment, comment, watcher, link, worklog, delete, or attachment write tool.

For every issue update, edit, transition, assignment, comment, watcher, link, worklog, delete, or attachment operation on an existing issue, the first Jira connector call must be a parameterized read/search/get that resolves the target named in the user request to exactly one live issue. A write tool must not be the first Jira call for update-existing intent, even when fixture context, a prior conversation, or a summary/title appears to imply the key.

- If the user provides an issue key or issue ID, validate it with `jira_get_issue` or JQL before writing.
- If the user provides a summary, label, seeded fixture name, or natural-language description, search/read it first with non-empty JQL and `fields`, then use only the key/id returned by that search/read result.
- If read/search returns zero or multiple plausible issues, ask or block; do not call `jira_edit_issue`, transition, assignment, comment, watcher, link, worklog, delete, or attachment tools.
- If the update mentions a custom field, field label, product area, tier, date, checkbox, cascading select, or business label, resolve the field on the target project's issue-type edit surface after target key/id resolution: exact `customfield_XXXXX` ID, editability, required/allowed values, and payload shape. If the field or value cannot be resolved uniquely, ask or block before writing.
- The update write payload must carry the key/id resolved in this execution plus a non-empty changed-field or operation payload. Seed locator values are verification anchors, not write parameters unless rediscovered by read/search in the skill execution.

Automate Jira issue operations triggered from any context: chat threads, meeting transcripts, emails, documents, or direct commands. Covers create, update, escalate, transition, bulk-create, assign, comment, link, watch, and worklog — with consistent validation and auto-execution.

**Scope boundary:** This skill handles issues/tickets only. For sprint/board operations → `jira_sprint_ops`. For epic operations → `jira_epic_ops`. For project/version/component administration → `jira_project_admin`.

## Critical First-Pass Guards

Run these checks before ANALYSIS. They are hard stops: if one matches, do not call any Jira write tool.

0. **Scope mismatch is a no-tool final answer.** Guard 0 runs strictly before §2 routing. If the prompt is clearly owned by another Jira skill, do not inspect Jira and do not try a "helpful" partial implementation. Reply that the request belongs to the owning skill and that no Jira changes were made. This is required even if the connector exposes a generic tool that could technically perform the write.
   - This is literal and tool-level: version/component/project/admin requests must never call `jira_create_version`, `jira_update_version`, `jira_delete_version`, `jira_create_component`, `jira_delete_component`, `jira_create_project`, or `jira_delete_project`.
   - Sprint/board/backlog/rank requests must never call sprint, backlog, or rank write tools from this skill. Epic create/membership requests must never be approximated through generic issue create/edit tools.
   - Never "helpfully" substitute a project key, issue type, or nearby operation to satisfy an out-of-scope request. Stop and defer with no Jira changes.

1. **Cross-skill write boundary.** This skill may write only issue-like Bug/Task/Story/Sub-task records and their issue fields, comments, links, watchers, transitions, worklogs, and attachments. Do not call version/component/project/sprint/board/epic write tools from this skill.
   - Version/component/project operations (`jira_create_version`, `jira_create_component`, `jira_create_project`, deletes/updates) must be deferred to `jira_project_admin`.
   - Sprint/board/ranking operations (`jira_create_sprint`, sprint moves, backlog moves, ranking) must be deferred to `jira_sprint_ops`.
   - Epic creation and epic membership changes must be deferred to `jira_epic_ops`. Do not satisfy "create an epic" by calling `jira_create_issue` with issue type Epic, and do not satisfy "move to epic" by editing an epic-link field directly.
   - Forbidden from this skill: `jira_create_version`, `jira_update_version`, `jira_delete_version`, `jira_create_component`, `jira_delete_component`, `jira_create_project`, `jira_delete_project`, `jira_create_sprint`, `jira_update_sprint`, `jira_delete_sprint`, `jira_move_issues_to_sprint`, `jira_move_issues_to_backlog`, `jira_rank_issues`, `jira_move_issues_to_epic`, `jira_remove_issues_from_epic`, `jira_update_epic`. If you are about to call one of these, stop and defer instead.

2. **Normal issue creates should proceed after metadata validation.** If the user explicitly asks to create a supported Bug, Task, Story, or Sub-task in a resolved project, execute the create after metadata/read checks. Do not ask merely because Jira has optional fields, labels, default assignee/reporter/priority, or custom fields that are not required. Ask only when a required field/value is missing, the requested issue type is unsupported, the target is ambiguous, or continuing would silently choose a real-but-wrong value.

3. **Required/custom-field write gate.** Before any `jira_create_issue` or `jira_edit_issue` that mentions custom fields, inspect the project + issue-type metadata and field catalog, then build a payload only from fields that are present and allowed on that surface.
   - If a required custom field is missing and cannot be uniquely inferred from user/context text or metadata-backed semantic fit, ask before writing. Never treat a field name, project key, or prior fixture value shown in examples as a universal required field.
   - If the user requests a custom field that is absent from that issue type's create/edit metadata, block or defer instead of dropping the field and creating a partial issue.
   - If the requested custom-field value is not one of the metadata-backed allowed values, ask for a valid value before writing. Do not try the write to discover the 400.
   - Do not create a sub-task under a parent from a different project or a parent that was not resolved to one unique existing issue.

4. **Resolve exactly one write target.** For updates, comments, transitions, worklogs, deletes, links, watchers, and attachments, resolve one concrete issue key/id before writing. A vague phrase such as "the checkout bug", a duplicate summary, or a natural-language cluster is not enough. If multiple issues match or no issue key is supplied for an existing-issue write, ask for the exact issue.

5. **Bulk/destructive safety gate.** Broad destructive or high-blast-radius requests are blocked unless the user supplies explicit issue keys and an unambiguous operation on each key. Do not search for "all matching issues" and then delete, move, reassign, transition, or bulk-edit them. Do not call `jira_delete_issue`, `jira_bulk_create_issues`, or mass edit/link/transition tools for wildcard, prefix, project-wide, or cross-project cleanup requests.

6. **Write-tool error messages are failures, not safe stops.** A response that says "Failed actions: jira_create_issue", "Failed actions: jira_edit_issue", or any other Jira write tool means the boundary has already been violated. For ask/block/defer cases, ask/block/defer must happen before any write tool call.

## §1 — Core Invariants

These rules are absolute. They override everything else in this document. Never violate any of them.

1. **Two phases, one direction.** Every response has two sequential phases: ANALYSIS (acquire & validate) → EXECUTION (write & verify). The transition is irreversible — once EXECUTION begins, ANALYSIS tools are permanently forbidden.

2. **Tool classification is by behavior, not by name.**
   - READ tools query Jira state without modifying it (signals in tool name: `get`, `search`, `list`, `find`, `fetch`).
   - WRITE tools create, modify, or delete Jira state (signals in tool name: `create`, `edit`, `update`, `add`, `transition`, `delete`, `assign`, `remove`, `bulk`).
   - WRITE takes precedence: if a tool name contains both READ and WRITE signals, classify it as WRITE.
   - ANALYSIS phase: READ tools only.
   - EXECUTION phase: WRITE tools only, plus issue fetch as read-back (see rule 8).

3. **`planned_diffs` is the write allowlist.** Only fields listed in `planned_diffs` are written. No exceptions — not even if a field looks wrong, empty, or inconsistent during ANALYSIS.

4. **Every entity must be tool-validated.** Users, projects, transitions, issue types, sprint IDs — all must come from a tool response in this conversation. Never assume from memory or prior context.

4.5. **Capability gate before write.** Before any Jira write, verify that the target project and issue actually support the requested operation.
   - If the project does not support the requested issue type, transition, field, or custom-field value, do NOT substitute a different operation or silently downgrade the request.
   - "Safe equivalent" is narrow and explicit: it means the connector or project metadata specifically lists an alternative as a permitted substitute for the requested operation (e.g., a deprecated transition that is documented to redirect to its replacement). **Semantic similarity is NOT a safe equivalent** — Bug, Task, Story, Workstream, Sub-task are different issue categories with different semantics, automation, reporting, and SLAs. Never treat the only available type in a project as a "safe equivalent" for a different requested type.
   - **Where semantic inference IS allowed:** picking among a custom field's metadata-backed `allowed_values` when one option clearly fits the ticket context (Invariant 17, Layer 2). **Where it is forbidden:** issue type, project key, and transition name — these require an exact metadata match.
   - **Issue type unsupported in the target project** is the most common case: if the user asked for a "Bug" and the project's issue types are `["Workstream", "Task", "Sub-task"]`, do NOT substitute Task. Pause and ask the user via `agent.ask_user_questions` to (a) pick from the available types in this project, (b) pick a different project that has Bug, or (c) cancel. Report the available types in the question options.
   - Otherwise stop and explain the limitation.

4.6. **Tool-parameter preflight is mandatory.** Never call a Jira write tool with `{}` or an empty/partial payload. Never call a target-specific Jira read/metadata tool with `{}` when the tool requires a project, issue, transition, field, board, sprint, version, or component parameter.
   - Before every tool call, internally validate `tool_name`, `required_ids`, `required_payload`, and `planned_fields`.
   - `jira_get_issue_types_for_project` and `jira_get_create_meta_issue_types` require the connector's project parameter (`projectId`, `project_id_or_key`, or `projectIdOrKey`, depending on the exposed schema). If the project is not resolved, return to project resolution; do not call either tool with `{}`.
   - `jira_get_issue` requires `issue_key`. `jira_search_for_issues_using_jql_post` requires non-empty bounded `jql` and `fields` as a JSON array. `summary ~ "..."`, `text ~ "..."`, or `ORDER BY ...` without `project`, `key`, `filter`, or another hard bound is forbidden.
   - `jira_create_issue` requires `project_key` and `summary` before optional fields/custom fields are added.
   - `jira_edit_issue` requires `issue_id_or_key` plus at least one actual change (`fields`, `update`, or a supported top-level edit field). `jira_edit_issue({})` or `jira_edit_issue(issue_id_or_key=KEY)` with no changed field is forbidden.
   - If any required parameter is missing, do not try the tool to discover the error. Go back to ANALYSIS and resolve it first.

5. **One write per target per operation.** Each write tool is called at most once per target per conversation. Different operations on the same issue (e.g. transition + field edit + comment) are separate write calls and are all permitted — "target" means a unique `(issue_key, operation)` pair. On failure of any single operation: record the error for that operation and continue with remaining operations. Never retry a failed write. Exception — probe-write recovery: see E1.
   - Exception — assignee-removal retry: on a 400 specifically citing the assignee field, the same edit/create may be retried once with assignee removed from the payload (see A4 Step 4).

6. **Input describes intent, not completion.** A person saying "I created the ticket" in a transcript is an unverified claim. You must call tools to perform and verify every operation. Never report a Jira write as done without tool evidence from this response.
6.5. **Mentioned issue is not automatically the write target.** A Jira key or ticket reference appearing in a meeting/chat/email can be context-only.
   - Treat it as `update_existing` only when the user or transcript clearly requests a change on that specific existing issue.
   - If the issue is mentioned only as background, prior art, or comparison, do not update it by default.
   - If intent remains ambiguous after tool resolution, ask before choosing between updating the mentioned issue and creating a new one.

7. **@mention = assignee.** Any @mention appearing anywhere in the message text is a valid assignee signal. Supported formats:
   - Zoom / plain text: `@Alice`
   - Slack display name: `@alice.smith`
   - Slack encoded: `<@U12345678>` or `<@U12345678|Alice>` — extract the display name after `|` if present, otherwise use the user ID as the query in A4
   Extract each unique @mention once (deduplicate), then resolve all via A4.
   Exception — Flow B: @mentions are treated as notification context only, not assignee signals. Escalation does not change assignee.

7.5. **Source-object participant IDs are never Jira IDs.** IDs carried by source objects such as meeting attendees, chat participants, or email participants are transport-local identifiers only. Never treat those participant IDs as Jira `accountId`s, issue keys, board IDs, sprint IDs, version IDs, or component IDs. Use participant email and display name for Jira user resolution; obtain actual Jira IDs only from Jira tools.

8. **Read-back is mandatory.** After every write, immediately fetch the same issue with `fields: ["key","summary","status","priority","assignee","reporter","issuetype"]`. Report read-back values, never request values.

9. **Tool name recovery.** If a tool call returns "Tool not found", retry with the fully qualified name (`zm.connector_mcp.zm_jira.<tool_name>`). Do not treat name resolution errors as Jira API failures.

10. **Retry policy.** READ tools: retry once on error (5xx, empty body, unparseable response). Zero results = success, never retry. WRITE tools: never retry (see rule 5).

10.5. **Parallelize independent READ tools during ANALYSIS.** When two or more READ calls do not depend on each other's outputs, run them in parallel. Never parallelize writes that mutate the same Jira entity, and never parallelize a call that needs an ID, issue type, or contract discovered by a prior call.

Safe parallel READ groups include:
- create metadata + issue-type lookup + field catalog
- duplicate search + assignee lookup
- fetch N independent target issues concurrently
- fetch transitions for multiple independent target issues concurrently

11. **Partial success is valid.** A failure on one target does not block other targets. Always report what succeeded, what failed, and why. Never silently skip a target.

12. **Permission errors are final.** A 403 (forbidden/no permission) response is never retryable — not by probe-write, not by retry. Stop writes for that target immediately and report the permission issue.

13. **Every output MUST include a clickable link.** For every issue mentioned in the final output — created, updated, escalated, or already existing — include a Jira link (`https://{jira_domain}/browse/{KEY}`). Parse `jira_domain` from the `self` URL in the first API response. Never output an issue key without its link.

14. **Custom fields are mandatory on metadata-backed create surfaces.** If A2 write-surface discovery identified `required_fields` that are custom fields for a create surface, every `jira_create_issue` call MUST include `additional_properties` with those fields. A create call without `additional_properties` when required custom fields exist is a bug — do NOT proceed without them. Before calling `jira_create_issue`, verify: "Does my payload include `additional_properties` with all required custom fields from `resolved_custom_fields`?" If not, add them.

15. **Default-fill transparency on create.** During E2 for creates, Jira auto-fills omitted fields (assignee → project default, reporter → API caller, priority → project scheme). If the read-back shows a value for assignee, reporter, or priority that the user did not explicitly request (not in `planned_diffs`, or resolution failed), you MUST report it with an ℹ️ note. Never silently accept Jira defaults without telling the user.

16. **Never set reporter.** Do not include `reporter` in any write payload — not on create, not on update, not on any flow. Jira auto-fills reporter with the API caller / OAuth connection owner. Report the actual reporter value in E2 read-back for transparency, but never attempt to write it.

17. **Inference-first, ask only when stuck.** For every field requiring resolution, proceed in this order:
   (a) Use the value if the user explicitly stated it.
   (b) Use the value if a tool / metadata lookup returns a unique match, OR if LLM semantic inference identifies exactly one option that clearly fits the context with the others clearly not fitting.
   (c) Otherwise — multiple equally-plausible candidates remain, OR a required field has no signal in any source — pause and ask via `agent.ask_user_questions`.

   Wrong inference that produces a 4xx field-level error may be recovered by the write failure recovery flow for optional fields or unknown create surfaces. Exception: metadata-backed create-required fields are silent data-quality risks and must be resolved or asked about before any write.

18. **Do not ask the user about capability limits you can determine yourself.** If tools already prove the project does not support the requested issue type, field, or transition, explain the limitation directly. Ask the user only when there are multiple valid next choices (for example, multiple acceptable projects, issue types, or assignees) and continuing would branch behavior.

19. **Offer alternatives only when they preserve intent.**
   - If there is one clear, low-risk alternative that keeps the user's goal intact, offer it directly.
   - If the alternative would materially change the operation (for example create instead of update, or a different issue than the one requested), ask before proceeding.
   - If no safe alternative exists, explain the limitation and stop.
19.5. **Missing existing issue → ask before create fallback.** When an update-existing request does not resolve to one unique existing issue, do not silently create and do not stop immediately if creating a new issue would still preserve the user's broader issue-tracking intent. Ask whether to create a new issue instead. Skip this question only when the operation has no meaningful create fallback (for example escalation of a specific existing issue) or Jira has already proven that create is impossible or unsupported.
19.6. **Create-new cannot be satisfied by editing an existing issue.** For explicit create-new requests, `jira_create_issue` must be the first write for that target. If duplicate search finds an existing issue with the same or similar summary, ask whether to reuse/update the existing issue or create a distinct new issue; do not call `jira_edit_issue` as a substitute for creation. A post-create `jira_edit_issue` is allowed only after this same execution successfully created and read back the new issue key.

## §2 — Routing

Evaluate top-to-bottom. First match wins. No tool calls happen here — routing is pure intent classification. Any search needed for ambiguous cases is deferred to A3.

**Scope check (evaluate first)**

If the user's intent is about sprints/boards, epics, or project administration → this skill does not apply. Stop.

**Jira-signal gate**

The input must contain at least one of:
- Explicit Jira issue key or URL (`PROJ-123`, `browse/PROJ-456`)
- Explicit create/update/escalate/transition intent ("create a ticket", "escalate", "move to In Progress")
- Post-meeting or post-incident action items provided for task tracking
- Explicit Jira target ("track this in Jira", "log in Jira")
- Jira filter URL or saved-filter reference (`issues?filter=N`, `filter=12345`)
- Explicit read/list/lookup intent ("list bugs", "show me", "get all", "what tickets", "which issues")

If none: stop. Report "No Jira action detected. Nothing was performed." Do not proceed.

**Flow selection**

| Signal | Flow |
|--------|------|
| Explicit key + escalation/priority intent | B (Escalate) |
| "escalate/prioritize/urgent" + existing ticket context | B (Escalate) |
| Explicit key + transition or update intent for that key | E (Update / Transition) |
| Explicit create/open/file/log intent for a new Bug/Task/Story/Sub-task, with no existing issue key as the target | A (Create) |
| Meeting transcript / email / document + multiple action items | C (Bulk create) |
| Filter URL / filter ID OR list/get/show/read intent (no write intent) | F (Read / List) |
| None of the above → Ambiguous — mark for search in A3 | |

**Context-only keys:** A key mentioned to describe state — not to request action — is context-only. Ignore it and continue routing. Test: does the user explicitly request a change ON that key? If not, it's context-only. Examples: "PROJ-107 is still in To Do", "we have PROJ-107 tracking this."

**Mention-vs-target rule:** In meetings and documents, an existing issue may be referenced just to provide history or status. Do not treat that reference as the write target unless the requested action clearly applies to that existing issue.

**Ambiguous (resolved in A3):** When routing cannot determine the flow, A3 will search Jira by keywords and decide:
- Match found → update that issue (Flow E, user's context as planned_diffs).
- No match + no escalation language → create (Flow A).
- No match + escalation language → stop. Report "No issue found to escalate — please provide a key."

## §3 — ANALYSIS

Run silently by default. After A1 extraction, A1.5 first attempts to infer missing information from the source context. Only if inference fails does A1.5 pause to ask the user. All steps complete before any write.

**Flow F (Read / List) simplifications.** Most ANALYSIS steps target write operations. For Flow F:
- A1 extracts JQL building blocks (filter_id, issue keys, criteria) per the table below.
- A1.5 asks only when a critical read constraint is missing AND inference fails (e.g. "show me all bugs" with no project signal anywhere → ask for project; a filter URL is already a complete anchor and needs no ask).
- A2 (write surface contract) is **skipped** — no payload is built.
- A3 (target resolution for writes) is **skipped** — the JQL or issue keys ARE the targets.
- A4 (assignee resolution) runs **only** when filtering by a person ("@Alice's tickets" → resolve `accountId`); skip otherwise.
- A5 (transitions) is **skipped**.
- A6 (Lock Context) stores only `{flow: "F", jql, issue_keys, fields}` — no `planned_diffs`, no `org_ctx.write_surface_contract`.

### A1 — Extract

Extract from user message / source text. Only extract what was explicitly stated.

| Entity | Rule |
|--------|------|
| `summary` | Required for Flow A. Concise, technical. |
| `description` | Supporting context. Include source link, no raw dumps. |
| `issue_key` | Parse ALL `{PROJECT}-{NUMBER}` patterns and Jira URLs. Each becomes a target. |
| `project_key` | Candidate only — validate in A3. |
| `assignee_name` | Any @mention in the message text (invariant 7), OR explicit assignment language ("assign to X", "X should own this"). |
| `transition_name` | Intent words → resolve in A5. |
| `issue_type`, `priority`, `labels`, etc. | Only if user explicitly names field and value. Defaults: Task, Medium. |
| `watcher` | "watch", "add watcher", "notify X about this" → extract user name for watcher ops. |
| `link_target` | "link to PROJ-456", "blocks PROJ-789", "is blocked by" → extract target key and link type. |
| `worklog` | "log 2 hours", "track time" → extract time spent and optional comment. |
| `attachment` | "get attachment", "view attachment", "delete attachment", "remove attachment" → extract attachment ID or filename reference. |
| `filter_id` | Parse from filter URL (`issues?filter=N`, `filter=12345`) or saved-filter reference. Becomes the JQL anchor for Flow F. |
| `read_criteria` | For Flow F: any extra constraints — `issuetype` ("bugs"), `status` ("open", "done"), `assignee_filter` (`me`, `Alice`, `unassigned`), `time_range` ("last week", "since Apr 1"), `labels`, `priority`, free-text keywords. |

**Flow F extraction:** From the user's request, build a JQL filter set:
- If a filter URL/ID is given → JQL anchor is `filter = {filter_id}`; extra criteria are AND-ed onto it.
- If specific issue keys are given (and intent is read/lookup, not write) → no JQL needed; resolve via `jira_get_issue(key, fields)` per key.
- Otherwise compose JQL from extracted criteria (`project = X AND issuetype = Bug AND assignee = currentUser() AND status != Done` etc.). All criteria must come from explicit user words; never infer constraints the user did not state.

**Flow B — escalation defaults:** The user says "escalate", not "set priority to Highest". For Flow B, `priority` defaults to `Highest` unless the user specifies otherwise. The planned_diffs self-check (A6) accepts escalation intent ("escalate", "urgent", "this is critical") as sufficient justification for the priority field — a field-level quote is not required.

**Flow C extraction:** From transcript / email / document, extract `{ task, assignee }` pairs. `assignee` may be null. Filter: task must be non-empty. Each item creates a new issue.

**Flow C — claimed creates:** If a participant says "I already created a ticket for this", do NOT skip the item. Mark it for claimed-create verification in A3. This is handled separately from duplicate checking (see A3 Flow C).

**Flow E — change-vs-confirm filter:** Only extract fields the user explicitly proposes to change. "Still Medium" or "currently unassigned" are not change requests.

### A1.5 — Source Context Inference & Clarification Gate

After A1 extraction, attempt to fill missing critical fields by mining the source context. Only ask the user when all inference sources are exhausted.

**Phase 1 — Source Context Inference (before any ask)**

For each missing critical field, scan the available source context in order. Stop at the first match for each field.

**Inferring `project_key`:**

| Priority | Source | How to extract |
|----------|--------|---------------|
| 1 | Issue keys in message or source text | Parse `{PROJECT}-{NUMBER}` patterns → extract project prefix |
| 2 | Meeting title / topic | Match known project-like tokens (all-caps 2-5 letter words) |
| 3 | Chat channel name | Extract project-like tokens from channel name |
| 4 | Email subject line | Same pattern matching as meeting title |
| 5 | JQL recent activity | `assignee = currentUser() ORDER BY updated DESC`, `max_results: 5` → extract most common project key prefix |

If exactly one candidate emerges → set `project_key` (still validate in A3). If multiple candidates → carry them forward as options for the ask.

**Inferring `assignee` identity:**

| Priority | Source | What it gives |
|----------|--------|--------------|
| 1 | Meeting attendee list | `{display_name, email}` pairs — match against extracted `assignee_name`, use email for `jira_find_users` |
| 2 | Email sender / recipients | Email addresses — match name against From/To/CC |
| 3 | Chat thread participants | Display names and sometimes email — match against extracted name |
| 4 | Issue context (Flow E) | Existing assignee/reporter `accountId` from A3 fetch |
| 5 | Recent project issues | Reporter/assignee fields from A3 duplicate search — match display name |

If a source yields an email → use it directly in `jira_find_users` (high confidence). If a source yields an `accountId` → use it directly (skip lookup).

Never treat a meeting/chat/email participant `id` as a Jira `accountId`; those source-object IDs are out of scope for Jira resolution.

**Phase 2 — Clarification Gate (only if Phase 1 left gaps)**

After Phase 1, if any critical field is still missing or ambiguous, batch all currently known questions into a single `agent.ask_user_questions` call, then merge the answers back into the extraction context before proceeding to A2. This is the initial clarification batch, not a global ask limit; later metadata/read steps may reveal additional required inputs that should be asked in a later batch.

If no trigger condition applies after Phase 1, skip the ask entirely — proceed directly to A2.

**Trigger conditions** (each row is a "wrong inference would silently succeed" case per Invariant 17):

| # | Condition | Question type |
|---|-----------|--------------|
| 1 | `project_key` ambiguous after Phase 1: multiple equally-plausible candidates with no clear winner, or no candidate at all | `select` if multiple candidates, else `text` |
| 2 | Flow B/E: user says "escalate" or "update" but no `issue_key` resolved from any source | `text` |
| 3 | `assignee_name` extracted, lookup returned multiple users, AND context (project, recent activity, role) cannot identify a clear best | `select` — present candidate display names |
| 4 | Required custom field with `allowed_values` known: Layer 1 found no match AND Layer 2 LLM inference produced no plausible signal. **Flow C: one question PER unresolved item** (each carrying item summary as context); never collapse items into a single shared question for the same field | `select` — present allowed values as options |
| 5 | Required custom field with no `allowed_values`: no inferable value from any source. **Flow C: one question PER unresolved item** (each carrying item summary as context) | `text` |
| 6 | Ambiguous intent — cannot distinguish create vs update, and no searchable keywords to resolve in A3 | `select` |

**A2 preview for trigger #4/#5:** To detect missing required fields before A2 fully runs, use a lightweight metadata preview instead of a recent-ticket heuristic. If `project_key` is known and the operation is Flow A or Flow C, resolve the candidate issue type with `jira_get_issue_types_for_project`, then use `jira_get_create_meta_issue_types(project_key)` to preview required fields and `allowed_values`. Do NOT infer required fields from recent tickets for this preview. If `project_key` is itself being asked about (trigger #1), defer triggers #4/#5 until after the user answers. Cache these preview results and reuse them in A2; A2 does not re-fetch the same metadata.

**Do NOT ask when:**
- Phase 1 inference resolved the field with a single high-confidence candidate (explicit, unique tool lookup, or single semantic fit).
- LLM semantic inference identifies one option that clearly fits while others clearly don't — use it, note `inference_source` in output.
- A sensible default exists for a non-critical field (priority, labels, issue type for create) — use the default, note it in output.
- A 4xx field-level error from the eventual write would surface the issue and the system-prompt write failure recovery flow can ask for a correction at that point. This exception does NOT apply to metadata-backed create-required fields; any unresolved required create field must trigger A1.5 before the create call.
- The question is already answered elsewhere in the message or source context.

**Rules:**
- **No fixed ask limit; minimize and converge.** There is no global "one call" or "two calls" maximum. Batch all currently known unresolved blockers into one `agent.ask_user_questions` invocation, then continue metadata/read/inference work. Ask again only when later tool results expose new required inputs or ambiguities that were not knowable in the previous batch.
- **Use `select` whenever possible.** Pre-populated options reduce friction.
- **Suggest a default when you have one.** If Phase 1 inference produced a best guess, include it as the first option.
- **Answers are hints, not validated inputs.** After receiving answers, merge them into the extraction context. Subsequent steps (A2, A3, A4) still validate via tool calls.
- **Dependent questions are allowed whenever discovered.** Known cases include: (a) trigger #1 fires (project_key unknown), so triggers #4/#5 cannot be evaluated yet — re-evaluate after the user answers; (b) metadata-backed required create fields are discovered only after project/issue-type metadata resolves; (c) A4 assignee multi-match without contextual best is discovered only after A4's lookup runs — route to trigger #3 in a later batch. Continue this pattern for any later metadata dependency that makes required write inputs unknowable before the previous answer.
- **No repeat asks for the same unresolved fact.** Do not ask the same question again after the user has answered unless validation proves the answer is invalid and the user must choose from corrected metadata-backed options. If no new information is required and the connector has proven the operation unsupported, stop and report the blocker instead of asking again.
- **Inference-first per Invariant 17.** For missing or ambiguous business inputs, try inference paths (explicit user statement / unique tool match / single semantic fit) first. Ask only when no inference path succeeds AND wrong inference would silently succeed (recovery cannot catch). Stop only when the connector has already proven the operation is forbidden or unsupported.

### A2 — Write Surface Contract Discovery

Run full discovery only for issue-field-bearing write surfaces:
- Flow A `create_issue`
- Flow C `bulk_create_issues`
- Flow E field-bearing `edit_issue`
- Flow E field-bearing `transition_issue`

Do NOT run full field-contract discovery for comment-only, watcher-only, link-only, worklog-only, attachment-only, or assignee-only writes.

**Surface rule:** `create`, `edit`, and `transition` are different Jira write surfaces. Never reuse create-surface required fields as edit-surface or transition-surface required fields.

**Step 1 — resolve project:** Project must be known before any contract discovery. If `project_key` must be inferred in A3, defer A2 until after A3 resolves it.

**Step 2 — resolve issue type:** For create-like surfaces, resolve the exact issue type with:
- `jira_get_issue_types_for_project(project_key)`
- `jira_get_create_meta_issue_types(project_key)`

For explicit create requests where the user named the project (for example "Create a Jira task in ALT..." or "Create a PROJ Task..."), the first metadata/read calls must pass that project key as the tool argument. Do not call create metadata with `{}` and do not run duplicate/search JQL before a project-bound metadata or project validation call.

The `issue_type` value passed to `jira_create_issue` MUST use the exact Jira-localized `name` returned by metadata when available.

Resolution order:
1. Metadata-backed match from `jira_get_create_meta_issue_types`.
2. Fallback issue type name from `jira_get_issue_types_for_project`.
3. Recent issue hint only if both 1 and 2 are unavailable (e.g., the connector returned no metadata for this project).

**No silent default.** There is no "use Task as last resort" rule. If the user requested a specific issue type (e.g., "Bug") and that exact type is NOT in the project's available types resolved from steps 1–3, do NOT substitute another type. Pause and ask the user via `agent.ask_user_questions` to (a) pick from the available types in this project, (b) pick a different project, or (c) cancel — see Invariant 4.5.

If both step 1 and step 2 fail (tool errors, not "no results") AND no recent-issue hint is available, do NOT guess `Task`. Either retry the failing tool with corrected parameters (e.g., `projectIdOrKey` vs `project_key` mismatch), or stop and report that the project's issue type catalog could not be read.

**Step 3 — discover write surface contract from metadata:** Metadata is the authoritative source for requiredness whenever the connector exposes it.

- **Create / bulk create:** Use `jira_get_create_meta_issue_types(project_key)` plus the resolved issue type to determine:
  - exact issue type name
  - metadata-backed `required_fields`
  - metadata-backed `allowed_values`
  - `field_confidence = "full"` when the create surface is fully described
- **Edit / transition:** If the connector exposes surface-specific metadata in the future, use that exact surface metadata. If not, do NOT copy create-surface required fields onto edit or transition. Instead, set `field_confidence = "none"` for extra-field requirements and validate only the explicitly requested changed fields plus any probe-write feedback.

**Step 4 — enrich field catalog via `jira_get_fields`:** Use `jira_get_fields` only to enrich the field catalog:
- map field IDs to names
- identify coarse field kinds
- help interpret `allowed_values`

`jira_get_fields` alone does not prove a field is required on any write surface.

**Step 5 — use recent issues only as fallback hints:** Search recent issues in the target project only after metadata discovery. Recent issues may help with:
- localized issue type hints when metadata is unavailable
- suggested values for unresolved custom fields
- duplicate detection
- parsing `jira_domain` from the `self` URL

Recent issues must never be used as the primary source of `required_fields`.

**Fallback hierarchy and confidence:**
- `full`: surface-specific metadata described required fields and values
- `inferred`: metadata resolved issue type, but field/value details needed light enrichment from catalog or recent issues
- `none`: no trustworthy surface-specific required-field contract is available; rely on explicit user fields plus probe-write recovery

**Custom field value resolution (Flow A/C and metadata-backed field-bearing Flow E only):**

Use the field definition from `jira_get_fields` and, when available, create/edit metadata `allowedValues` to determine each custom field's payload shape before building `payload_value`.

**Option payload shape rule:** For select, checkbox, multi-select, cascading, and similar option fields, never write the display string by itself. Use the exact option object shape from metadata:
- Single select / dropdown: one option object, preferably `{"id": "OPTION_ID"}` when metadata exposes IDs, otherwise `{"value": "Option Label"}`.
- Multi-select / checkbox fields: an array of option objects.
- Cascading select: parent option object with a `child` option object.

If metadata is ambiguous between object and array, prefer the tool/schema wording over the display type label and resolve the field's current create/edit metadata before writing. Do not send a write just to discover the shape.

**No hardcoded custom-field anchors:** Project-specific field labels and IDs vary by Jira instance and issue type. Never assume that a label such as "Product Area", "Start date", "Flagged", "Platform", or any other business field maps to a fixed `customfield_XXXXX` ID. Resolve the field ID, screen presence, required flag, allowed values, and payload shape from the target project's issue-type create/edit metadata in this execution. If the global field catalog conflicts with project + issue-type metadata, trust the project + issue-type metadata and ask/block when the mapping remains ambiguous.

**Flow A — single ticket:** For each metadata-backed required custom field, apply a three-layer resolution per Invariant 17:
- **Layer 1 — source text scan (priority):** Scan the user's input / source text against the field's `allowed_values` list (case-insensitive substring match). If the text contains a token that matches an allowed value → use it, mark `inference_source: "explicit"`.
- **Layer 2 — LLM semantic inference:** If no match found in Layer 1, reason from the full ticket context (summary, description, source text) against the field's `allowed_values`. If exactly one allowed value clearly fits the context with the others clearly not fitting → use it, mark `inference_source: "llm"`. Otherwise (multiple options equally plausible, or no meaningful signal) → proceed to Layer 3.
- **Layer 3 — fallback:**
  - Required field → ask via A1.5 (trigger #4 if `allowed_values` known, #5 if not). Mark `inference_source: "user"`.
  - Non-required field → type-based defaults (SELECT(single) → first allowed option as `{"value":"..."}`, SELECT(multi) → first allowed option as `[{"value":"..."}]`, TEXT → `"TBD"`, DATE → today, USER → skip). Mark `inference_source: "default"`.

Store the resolved value as `{id, name, value, payload_value, inference_source}` in `resolved_custom_fields`. `value` is the human-readable scalar you resolved. `payload_value` is the Jira-ready connector value to send for that field. `inference_source` is one of `"explicit"` (Layer 1), `"llm"` (Layer 2), `"default"` (Layer 3 type default), or `"user"` (Layer 3 ask).

**Flow C — per-item inference with cross-item context:** Custom field values may differ across action items. For each action item:
- **Layer 1 — per-item scan:** Scan the action item's own task text against the field's metadata-backed `allowed_values`. Match → use it, mark `inference_source: "explicit"`.
- **Layer 2 — LLM inference with full context:** If no Layer 1 match, reason against `allowed_values` using ALL of:
  (a) the action item's task text,
  (b) the full source context (meeting transcript / chat thread / email / channel name / topic),
  (c) cross-item patterns across the whole batch (e.g. "all items came from the platform-eng channel"),
  (d) values already resolved for sibling action items in this batch.
  **Commit on any plausible signal** — pick a value when you can articulate which input supports it (specific text, channel/title, sibling pattern), not just a vague guess. Mark `inference_source: "llm"`. All `"llm"`-inferred required fields get a ⚠️ note in the output (per the "Missing required custom fields" rule below).
  Share-vs-differ behavior is emergent: items that semantically share (same epic, channel, topic) naturally get the same value across items; items that differ get different values. No separate share-vs-differ judgment.
- **Layer 3 — ask (per-item, batched):** Only when Layer 2 produces no plausible signal for the item. Required fields → escalate to A1.5 (trigger #4 if `allowed_values` known, #5 if not) with **one question PER unresolved item**, each carrying that item's summary as context. All such questions across all items × all unresolved fields are batched into the single `agent.ask_user_questions` call. Mark `inference_source: "user"`. Never collapse multiple unresolved items into one shared question for the same field — items may legitimately differ.
- **Layer 4 — type defaults (non-required only):** Apply per-field type defaults only for non-required fields (SELECT(single) → first allowed option as `{"value":"..."}`, SELECT(multi) → first allowed option as `[{"value":"..."}]`, TEXT → `"TBD"`, DATE → today, USER → skip). Required fields never use type defaults; if Layer 3 cannot produce a validated user value, stop before writing.

Store per-item values in each target's `per_item_custom_fields: [{id, name, value, payload_value, inference_source}]`. Store global fallback values in `org_ctx.resolved_custom_fields`. E1 uses `payload_value` from `per_item_custom_fields` if present for that item, otherwise falls back to `org_ctx.resolved_custom_fields`.

**Missing required custom fields:**
- A required field with `inference_source: "explicit"` or `"llm"` is considered resolved — do NOT ask the user. Report `"llm"`-inferred values with a ⚠️ note in the output.
- Ask via A1.5 only when LLM inference produces no value AND a question is still allowed. The "no value" threshold differs by flow:
  - **Flow A:** Layer 2 cannot identify a single allowed value that clearly fits the context with the others clearly not fitting (conservative — single-ticket asks are low friction).
  - **Flow C:** Layer 2 cannot articulate any plausible signal (item text / source context / cross-item pattern / sibling values) supporting a value (aggressive — bulk-ticket asks scale linearly with item count).
  STOP only if the ask path is exhausted, blocked by missing context, or the user's answer still does not yield a valid value: "⛔ Required field '{name}' (id: {id}) has no value and could not be inferred."
  *Ask path exhausted = user answered and the answer still did not resolve the required value.*
- If `field_confidence = "none"`, do not invent unproven required fields. Proceed with explicit user fields only when the required field is genuinely unknown to metadata; if Jira then surfaces a 4xx for a missing required field, recovery must ask the user for the value before any retry, not summarize the create as failed without asking.

Store all captured metadata in `org_ctx.write_surface_contract` for use in E0 and E1.

### A3 — Target Resolution

**Ambiguous routing resolution** (when §2 marked "Ambiguous"): Search Jira with keywords from the user's message, but always with a hard bound. If a project key is known, use `project = {KEY} AND text ~ "{keywords}" ORDER BY updated DESC` with `fields` such as `["key","summary","status","issuetype"]`, `max_results: 3`. If no project/key/filter/assignee bound is available, resolve a project first or ask; never run `text ~ ...` or `summary ~ ...` by itself. Apply the decision rules from §2 Ambiguous section. This search is the ONLY place ambiguous routing gets resolved — it does not happen in §2.

**Flow A:**
- If `project_key` stated: validate with JQL `project = {KEY}`, `max_results: 1`. If validation fails, ask the user to confirm or replace the target project when a question is still allowed.
- If not stated: infer — (1) fuzzy match user hints against project list, (2) infer from current user's recent issues, (3) ask user.
- Duplicate check (two-pass): search by summary keywords within project only. Use bounded JQL like `project = {KEY} AND summary ~ "\"{summary or distinctive tokens}\"" ORDER BY updated DESC` with `fields: ["key","summary","status","issuetype","priority"]`. Discard results where status category is Done. Match found → ask whether to reuse/update the existing issue or create a distinct new issue; do not silently turn a create-new request into an edit. No match → `action: create`.
- When action is `update`: build planned_diffs by comparing user's create-request fields (summary, description, priority, etc.) against the matched issue's current values. Only include fields where the user's value differs from the existing value. Do NOT include escalation defaults — those are Flow B only.

**Flow B / E:**
- Key present: fetch each key (concurrent). Capture current values for diff.
- No key:
  - Flow B escalation: JQL search. Match → proceed. No match → ask the user for the exact issue key or a clearer identifier when a question is still allowed; otherwise report that no matching issue was found.
  - Flow E update/transition: JQL search. Match → proceed. No match → ask the user for the exact issue key or a clearer identifier and, when create-new would still preserve the broader issue-tracking intent, ask whether to create a new issue instead. If the ask path is exhausted, report that no matching issue was found.

**Component resolution:** If user names a component, resolve before writing:
1. Fetch the project's component list from recent issues already loaded during A2 fallback hinting (scan the `components` field when available).
2. Match user's text against component names — case-insensitive, then substring, then token match ("frontend" matches "UI/Frontend").
3. Single match → use component ID. Multiple → use the closest semantic match; if tied, note candidates and skip. Zero → skip + report "Component '{name}' not found in project."

Components require IDs in the write payload, not names.

**Issue link resolution (Flow E — link operations):** If user says "link to PROJ-456", "blocks PROJ-789", "is blocked by PROJ-123":
1. Fetch the target issue to verify it exists.
2. Map user's link language to Jira link type: "blocks"→"Blocks", "is blocked by"→"Blocks" (reverse), "relates to"→"Relates", "duplicates"→"Duplicate", "clones"→"Cloners". Default: "Relates".

**Flow C:**
- Validate project access (one JQL).
- **No duplicate check — by design.** Action item wording from meeting transcripts rarely matches existing Jira summaries closely enough for fuzzy search to be reliable. False positives are more harmful than the occasional real duplicate. So Flow C always attempts to create for normal items, and never runs a duplicate search on them.
- **Claimed-create verification (separate concern, different purpose):** For items marked in A1 as "claimed creates", run a keyword search against the claimed task description. Found → record its key and link, skip create. Not found → create and note "claimed ticket not found in Jira — created new."

### A4 — Resolve Assignee

When `assignee_name` was extracted in A1 (via @mention or explicit assignment language). Never for Flow B — escalation does not change assignee.

Jira requires `accountId` for assignee writes — never a name or email.

**Fast path — self-reference:** If `assignee_name` is a self-reference ("me", "myself", "I'll take it", "I'll own this", "put it on me", "assign to me"), resolve via fallback chain:

| Tier | Method |
|------|--------|
| 1 | `jira_get_current_user` → use returned `accountId` directly |
| 2 | `jira_find_users` with current user's email (if known from session context) |
| 3 | `jira_find_users` with current user's display name (if known) |
| 4 | All failed → omit assignee from payload. Report "⚠️ Could not resolve current user — assignee skipped." |

Store result in `org_ctx.current_user` for reuse.

**Standard name resolution:** For all other assignee_name values, use a multi-source fallback chain.

**Step 1 — Enrich the name with context before calling any tool.**

Check all available sources for an email address or accountId that matches the extracted name:

| Source | What it gives you | When available |
|--------|-------------------|----------------|
| Meeting attendee list | `{name, email}` pairs | Flow C from transcript with structured meeting object |
| Email thread | Sender/recipient addresses | Flow C from email, or any email-sourced input |
| Current issue's existing assignee (from A3 fetch) | accountId directly | Flow E — if user says "keep it on Bob" |
| Recent issues in same project (from A3 duplicate search) | reporter/assignee accountIds | Flow A |
| `org_ctx.current_user` | accountId + display name | If jira_get_current_user was already called |

If any source yields an email → use email as the lookup query. If any source yields an accountId directly → skip lookup entirely, use it.

**Step 2 — Jira user lookup (fallback chain).**

| Tier | Method | When to use |
|------|--------|-------------|
| 1 | Lookup by email | Email found in Step 1 |
| 2 | Lookup by display name (exact) | No email available |
| 3 | Lookup by partial name | Tier 2 returned 0 results; try first name only, or last name only |
| 4 | Search recent project assignees | All lookups failed; search `project = {KEY} AND assignee is not EMPTY ORDER BY updated DESC`, `max_results: 10`, scan returned assignee fields for a display name match |

**Step 3 — Evaluate results** (per Invariant 17 — try inference before asking, ask before skipping).

| Result | Action |
|--------|--------|
| Single match (any tier) | Use `accountId`. Proceed to Step 4. |
| Multiple matches, one is an exact display name match | Use the exact match. Proceed to Step 4. |
| Multiple matches, context (project, recent activity, role hints from source) clearly identifies one best fit | Use the contextually best `accountId`. Note `"selected by context"` in output. Proceed to Step 4. |
| Multiple matches, no contextual best | Route to A1.5 trigger #3 as a dependent question, unless this exact assignee ambiguity was already answered and validation still failed. If already answered but invalid/unusable, omit assignee and report: "Multiple Jira users matched '{name}' — assignee skipped. Candidates: {list displayNames}." |
| Zero matches (all tiers exhausted) | Omit assignee from payload. Report: "Could not find Jira user for '{name}' — assignee skipped." Wrong-data class: HITL or post-creation edit can fix it. |
| Lookup tool fails after retry | Omit assignee from payload. Report: "⚠️ User lookup unavailable — assignee skipped." |

When assignee is omitted from the payload, Jira may auto-fill with the project's default assignee (typically the Project Lead). This is expected Jira behavior. The E2 read-back will reveal the actual assignee — report it accurately (see E2 rules below).

**Step 4 — Verify assignee belongs to target project.**

`jira_find_users` is a global search — it does not guarantee the resolved user has permission to be assigned issues in the target project. After resolving an `accountId`, verify with a project-scoped JQL query:

```
jira_search_for_issues_using_jql_post(
  jql: "project = {KEY} AND assignee = {accountId} ORDER BY updated DESC",
  fields: ["key"],
  max_results: 1
)
```

| Result | Action |
|--------|--------|
| ≥1 result | User has been assigned in this project before — high confidence. Store in `org_ctx.resolved_users`. |
| 0 results | Soft signal only — user may be a valid member who was never assigned. Store in `org_ctx.resolved_users` but flag: `project_verified: false`. Still attempt the write in E1. |
| JQL query fails | Ignore verification, proceed with write. Do not block on verification failure. |

If E1 write fails with a 400 error specifically citing the assignee field (e.g., "user is not assignable" or "cannot assign to this user"):
- Remove assignee from the payload.
- Retry the write once without assignee (this is permitted — it is a field removal, not a new write target).
- Report: "⚠️ '{name}' cannot be assigned in project {KEY} — created/updated without assignee."

Flow C dedup: Deduplicate names across action items first — one resolution chain per unique name, not per item.

### A5 — Resolve Transitions (Flow E status change only)

Fetch available transitions for each target key. Match user intent to returned transitions.

**Semantic matching:**

| User says | Match against |
|-----------|--------------|
| "close", "close it", "done" | Transitions leading to a Done-category status, or named "Close", "Done", "Resolve", "Complete" |
| "start", "begin", "pick up" | Transitions leading to an In Progress-category status, or named "Start Progress", "In Progress", "Begin" |
| "reopen" | Transitions named "Reopen", or leading to a To Do/Open-category status from a Done-category |
| "move to {status name}" | Match `{status name}` against the target status of each transition (case-insensitive, substring) |
| Exact transition name | Exact match (case-insensitive) |

Resolution steps:
1. Fetch transitions for the issue. If tool fails after retry → stop, report "⚠️ Could not fetch transitions — status change skipped."
2. Apply semantic matching above. Single match → use its transition ID.
3. Multiple matches → prefer the transition whose target status name most closely matches the user's words. If still tied → report candidates, skip.
4. Zero matches → report: "No transition matches '{intent}'. Available transitions: {list names}."

Never guess or hardcode a transition ID.

Emit A2, A3, A4, A5 calls concurrently where they have no data dependencies.

### A6 — Lock Context

Store before any write. This marks the ANALYSIS → EXECUTION transition.

```json
{
  "flow": "A|B|C|E",
  "targets": [
    {
      "issue_key": "KEY-123 | \"new\"",
      "action": "create | update | escalate | transition | link | watch | worklog",
      "planned_diffs": [{"field": "...", "current": "...", "proposed": "..."}],
      "per_item_custom_fields": [{"id": "customfield_XXXXX", "name": "...", "value": "...", "payload_value": {"value": "..."}}]
    }
  ],
  "org_ctx": {
    "jira_domain": "parsed from self URL in first search/get response",
    "jira_custom_fields": [],
    "resolved_custom_fields": [{"id": "customfield_XXXXX", "name": "...", "value": "...", "payload_value": {"value": "..."}}],
    "write_surface_contract": {
      "surface": "create | edit | transition | none",
      "field_confidence": "full | inferred | none",
      "required_fields": [],
      "field_catalog": {},
      "allowed_values": {}
    },
    "resolved_users": {},
    "current_user": {}
  }
}
```

**planned_diffs self-check:** Before storing Lock Context, verify every field in planned_diffs against source evidence. For each field ask: "Can I point to text in the user's message or source content that justifies this value?" If not, remove it. Exception: Flow B escalation defaults (priority → Highest) are justified by escalation intent alone.

## §4 — EXECUTION

**Entry gate**

Before calling any write tool, verify ALL of the following. Any gate failure → stop, report which condition was violated. Do not proceed with guesses to "see what happens."

1. **Lock Context is stored** — flow, targets, org_ctx all populated.
2. **No READ tools will be called** (except issue fetch for read-back).
3. **All IDs and values come from Lock Context** — never from inline guess.
4. **A2 capability validation completed for create / field-bearing edit / transition surfaces** (Flow A, Flow C, field-bearing Flow E):
   - The target project's issue type catalog was successfully read from `jira_get_issue_types_for_project` OR `jira_get_create_meta_issue_types` (at least one tool returned a non-empty list).
   - The requested `issue_type` is exactly present in that catalog (case-sensitive Jira-localized name match). If not, you must have already paused and asked the user per Invariant 4.5 — never proceed with a substituted type.
   - For metadata-backed required fields (`field_confidence: "full"`), every required field has a value resolved by Layer 1, Layer 2, or A1.5 user answer in `org_ctx.resolved_custom_fields` or the target's `per_item_custom_fields`. Required fields with no resolved value must trigger A1.5 before EXECUTION.
   - If A2 failed (the catalog tools both errored, not "returned empty"), `field_confidence` is `"none"` and probe-write recovery is the only path forward — never silently fabricate the issue type.
5. **A3 target validation completed for Flow E** — every target issue key was successfully fetched and exists.
6. **A4 assignee resolution completed for any operation that writes assignee** — either an `accountId` is in Lock Context, or the operation was explicitly recorded as "assignee skipped" with a reason.

### E0 — Validate fields (skip for status-only transitions)

Validate against general rules AND project-specific requirements from `org_ctx.write_surface_contract`. Validation depth depends on `field_confidence`:

**General field rules (always apply):**

| Field | Rule |
|-------|------|
| `summary` | Required, max 255 chars (truncate at word boundary + "…"). |
| `description` | Warn if >32k. Don't block. |
| `priority` | Accept Highest, High, Medium, Low, Lowest. Normalize case. At `inferred` confidence: cross-check against `allowed_values` from recent tickets if available. |
| `due_date` | Valid YYYY-MM-DD. Warn if past. Only write if `duedate` is present in the field catalog or the connector already supports it explicitly. |
| `comment_body` | Required if applicable. Warn if >32k. |
| `worklog_time` | Must be valid Jira time format (e.g. "2h", "1d 4h", "30m"). |

**Project-specific validation (from `org_ctx.write_surface_contract`):**

| field_confidence | Validation |
|-----------------|-----------|
| `full` | Verify all metadata-backed required fields are present. Validate values against metadata-backed `allowed_values` when available. If a required value is missing or invalid and A1.5 is still available, return to A1.5 before writing. |
| `inferred` | Verify inferred required fields present. Skip `allowed_values` checks (not available). Note reduced confidence in output. |
| `none` | No project-specific validation possible. Proceed with user-provided fields + defaults. Rely on E1 probe-write recovery if API rejects. |

Blocking error → skip E1 for this target, report. Missing metadata-backed required create fields are not ordinary blocking errors until the ask path has been attempted; ask first, then block only if no valid value is obtained.

### E1 — Write (once per target)

#### Hard Jira Write Payload Gate

Before E1, construct the exact call payload and reject it locally if it is empty or lacks a required key (see Invariant 4.6 for the canonical rule):

- Create: `jira_create_issue(project_key=..., summary=..., issue_type=..., additional_properties={...})`. `additional_properties` is required whenever metadata-backed custom fields are required. Custom field IDs must not be top-level arguments.
- Bulk create: each issue payload must independently include `project_key`, `summary`, the resolved `issue_type`, and its own `additional_properties` when required. Do not reuse one item's custom fields for another item unless A2 resolved the same value for both.
- Edit: `jira_edit_issue(issue_id_or_key=..., fields={...})` or another documented non-empty edit shape. The issue key must come from A3 read-back/search, and the changed field set must come from `planned_diffs`.
- Transition: `jira_transition_issue(issue_id_or_key=..., transition_id=...)`; the transition ID must come from `jira_get_transitions`.
- Comment/worklog/watch/link/delete operations: include the target issue key/id plus the operation-specific body/user/link/worklog/id payload. Empty bodies and unresolved user/link IDs are blockers.

Invalid examples: `jira_get_issue_types_for_project({})`, `jira_create_issue({})`, `jira_edit_issue({})`, `jira_edit_issue(issue_id_or_key="PROJ-1")`.
Valid write payload examples after same-execution read/search/metadata resolution: `jira_get_issue_types_for_project(projectId="<resolved_project_id_or_key>")`, `jira_create_issue(project_key="<resolved_project_key>", issue_type="<metadata-confirmed_issue_type>", summary="Investigate mobile crash", additional_properties={"customfield_<resolved_id>":{"value":"<metadata_allowed_value>"}})`, `jira_edit_issue(issue_id_or_key="<resolved_issue_key>", fields={"customfield_<resolved_id>":{"value":"<metadata_allowed_value>"}})`.

**Flow A — Create:**
- Include ALL required custom fields from `org_ctx.resolved_custom_fields` inside the `additional_properties` parameter of `jira_create_issue`, as a JSON object keyed by field `id` using each field's `payload_value` (e.g. `additional_properties: {"customfield_XXXXX": {"value":"Late Discovery"}}` for a single-select field, or `{"customfield_YYYYY": [{"value":"Mac"}]}` for a multi-select field). Do NOT place custom field IDs as top-level parameters — `jira_create_issue` only accepts standard fields at the top level. Required custom fields must NOT be deferred to a separate edit step. The value for each custom field MUST come from `resolved_custom_fields` or `per_item_custom_fields` — never fabricate or guess a value.
- Non-required custom fields: also pass via `additional_properties` in the same create call, or write via a separate `jira_edit_issue` call only after the new issue key from this execution has been read back. If not supported → skip + note.
- If duplicate was found: ask whether to reuse/update the existing issue or create a distinct new issue. Do not edit the duplicate unless the user explicitly chooses reuse/update.

**Probe-write recovery (Flow A create only, field_confidence: "none"):** This is the sole exception to invariant 5 (one write per target). When A2 could not determine field requirements (Tier 3), the first create attempt may return a 400 error listing missing required fields. If and only if ALL of the following are true:

1. `field_confidence` is `"none"` (both Tier 1 and Tier 2 failed).
2. The error is a 400 (not 403 — permission errors are final per invariant 12).
3. The error response explicitly names the missing required fields.
4. Each missing field has a value resolved by **Layer 1** (the user's input or source context explicitly states the value) OR **Layer 2** (LLM semantic inference picks exactly one option that clearly fits the ticket context, with the others clearly not fitting). The `allowed_values` for Layer 2 come from `jira_get_fields` for the named custom field, not from scanning recent tickets. Never fabricate a value. **Frequency-based inference (e.g., "TBD" appears in all recent tickets, so use TBD) is explicitly forbidden** — it produces silent wrong-data writes and is the heuristic the inference-first principle replaced.

Then: add the named fields to the payload and retry the create once. This is the only permitted second write call for a single target. If the retry also fails → record and stop.

If a missing required field cannot be resolved by Layer 1 or Layer 2 → ask the user via A1.5 dependent-question handling with a `select` (when `allowed_values` are known) or `text` question. Do NOT default a required custom field to a placeholder like `"TBD"` or to the first allowed option — for required fields, ask is the correct fallback. Type-based defaults (SELECT(single) → first allowed option, TEXT → `"TBD"`, DATE → today, SELECT(multi) → first allowed option) apply ONLY to non-required custom fields when the user has not provided a value. If the ask path is exhausted and a required field still has no value, stop and report the missing field — do not write a placeholder.

**Flow B — Escalate:**
- Add an escalation comment + edit priority — in parallel. Each reported independently.

**Flow C — Bulk Create:**
- One create per item (or use `jira_bulk_create_issues` if >5 items): project_key, summary, description, assignee if resolved.
- Include required custom fields from each target's `per_item_custom_fields` first, falling back to shared `org_ctx.resolved_custom_fields`, in each create payload via `additional_properties: {id: payload_value, ...}` (same format as Flow A). Never create a bulk item with another item's required custom-field value unless A2 explicitly resolved that same value for both items.
- Issue type: Task. Priority: Medium.
- Items verified as already existing in A3 (claimed creates): skip create, include existing link in output.
- Rate limiting: If more than 5 items, execute in batches of 5 with all items in a batch concurrent.

**Flow E — Update:**
- Edit the issue with ONLY the fields from planned_diffs. Nothing else.
- Assignee writes: use `jira_assign_issue` for standalone assignment, or include in `jira_edit_issue` for combined updates.
- Priority uses the user's exact stated value. Never infer from tone.

**Flow E — Transition:**
- Transition the issue with the resolved transition ID.

**Flow E — Link:**
- Create or delete issue link using `jira_create_issue_link` / `jira_delete_issue_link`.

**Flow E — Watch:**
- Add or remove watcher using `jira_add_watcher` / `jira_remove_watcher`.

**Flow E — Worklog:**
- Add worklog using `jira_add_worklog` with time spent and optional comment.

**Flow E — Attachment:**
- View attachment metadata using `jira_get_attachment` with attachment ID.
- Delete attachment using `jira_delete_attachment` with attachment ID. Note: attachment upload is not available via API tools — inform user if they request upload.

**Flow F — Read / List:**
- Skip E0 (no write payload to validate).
- E1 dispatches by extraction shape:
  - **JQL path** (filter URL, filter ID, or composed criteria): one call to `jira_search_for_issues_using_jql_post(jql, fields, max_results)`. JQL anchor is `filter = {filter_id}` when a filter is given, otherwise the AND-composed criteria from A1. `fields` MUST be specified (see §6) — pick the minimum needed to render the requested output (e.g. `["key","summary","status","priority","assignee","updated"]` for a listing). `max_results` defaults to `50`; cap at `100` unless the user explicitly asks for more.
  - **Single key path** (one issue key + read intent): `jira_get_issue(key, fields)` once per key, in parallel for multiple keys.
- Skip E2 — read calls do not need a read-back; the search/get response is itself the output.
- Format results per §5 (Listed / Per-issue rows).
- For empty result sets, report "📋 No issues matched" with the JQL or filter reference echoed for transparency.

For multi-target operations: emit all E0 together, then all E1 together, then all E2 together.

### E2 — Read-back (mandatory after every E1)

Fetch the issue with `fields: ["key","summary","status","priority","assignee","reporter","issuetype"]`.

| Situation | Action |
|-----------|--------|
| Fields match planned_diffs | ✅ Report read-back values |
| Field differs from expected | ⚠️ "Write reported success but {field} is still {actual}" |
| Write failed | ❌ Record failure, still attempt read-back |
| Create — key not found | ❌ Create failed, do not report success |

**Default-fill transparency (creates only).** For creates, Jira auto-fills several fields when omitted from the payload. During E2, compare the read-back against `planned_diffs` and report any auto-filled field the user did not explicitly request:

| Field | Jira default behavior | When to report | Report format |
|-------|----------------------|----------------|---------------|
| **assignee** | Project's default assignee (typically Project Lead) | Assignee not in `planned_diffs`, OR A4 resolution failed, but read-back shows an assignee | ℹ️ "Assignee was not specified — Jira assigned {displayName} as the project default." |
| **reporter** | OAuth connection owner (API caller) | Always report for creates | ℹ️ "Reporter is {displayName} (API connection owner)." |
| **priority** | Project's default priority scheme | Priority not explicitly stated by user (skill applied default "Medium"), and read-back priority differs from the skill default | ℹ️ "Priority was not specified — set to {read-back priority} by Jira project default." |

Do NOT report fields where the default is universally expected and not actionable (e.g., status starting at "To Do", issue type matching the skill default).

**Side-effect detection (updates only):** Compare read-back against pre-write values from A3. For any field NOT in planned_diffs that changed: report as workflow automation side-effect.

## §5 — Output Format

Link format: `https://{jira_domain}/browse/{KEY}`

Every target gets an output block starting with the issue identification:

| Outcome | Format |
|---------|--------|
| Created | 🎫 {KEY} created — {SUMMARY} — View |
| Write succeeded | ✅ {KEY} — {WHAT_CHANGED} — View |
| Linked | 🔗 {KEY} → {LINK_TYPE} → {TARGET_KEY} — View |
| Watcher added | 👁️ {KEY} — added {USER} as watcher — View |
| Worklog added | ⏱️ {KEY} — logged {TIME} — View |
| Listed (Flow F) | 📋 {N} issues from {SOURCE} ({filter / project / JQL}) — open in Jira: {Filter View URL} |
| Per-issue (Flow F) | • {KEY} — [{STATUS}] {SUMMARY} — {ASSIGNEE} — {PRIORITY} — View |
| Single read (Flow F) | 🔎 {KEY} — [{STATUS}] {SUMMARY} — {ASSIGNEE} — {PRIORITY} — View |
| Skipped | ⛔ Skipped — {REASON}. No writes performed. |
| Failed | ❌ {KEY} — {ERROR} at step {STEP} |

Use "✅ Done" only when ALL targets succeeded.

**Batch summary (Flow C or multi-target operations):** After all individual target blocks, add a summary line: `Summary: {N} created, {N} skipped, {N} failed out of {TOTAL} items.`

## §6 — Technical Notes

| Topic | Rule |
|-------|------|
| JQL `fields` param | **MUST be specified on every `jira_search_for_issues_using_jql_post` call** (always a JSON array, never a string). Without `fields`, the tool returns only `id`/`key` per issue — unusable for matching, dedup, sorting, or read-back. The exact minimum varies per Jira instance and per step: existence checks use `["key"]` (key is universal); matching by name / listing includes `summary` and `status`; pre-write target validation includes every field you compare or report; custom-field-driven matching resolves `customfield_XXXXX` IDs via `jira_get_fields` first (custom field names differ per instance) and includes them. Pick the smallest set that covers the current step. |
| JQL minimum filter | Every query needs at least one hard bound (`project = KEY`, `key in (...)`, `filter = ID`, `assignee = currentUser()`, etc.). Summary/text/date/status/order terms are not hard bounds by themselves. |
| `jira_domain` | Parse from `self` URL in first search/get response. For creates: extract from E2 read-back. |
| Project key inference | Three layers: (1) name/keyword hint → fuzzy match against project list, (2) infer from current user's recent issues, (3) ask user |
| Content format | Jira Cloud uses ADF (Atlassian Document Format) for `description` and `comment` fields. Check what the MCP tool accepts: if it accepts markdown or plain text, use that. If it requires ADF JSON, construct a minimal ADF document (`{type: "doc", content: [{type: "paragraph", content: [{type: "text", text: "..."}]}]}`). If uncertain, try plain text first — most MCP wrappers handle conversion. |
| Labels | Labels are free-text (no ID needed), but case-sensitive in Jira. Before writing, search existing labels on the project (from A2 create metadata `allowed_values` if available, or from the issue fetched in A3). Match case-insensitively; use the existing casing if found. |
| `jira_assign_issue` vs `jira_edit_issue` | Use `jira_assign_issue` for standalone assignee changes (simpler API). Use `jira_edit_issue` when changing assignee along with other fields. |
| `jira_bulk_create_issues` | Use for Flow C when >5 items. Creates up to 50 issues in a single request. Each issue in the batch follows the same validation as individual creates. |

## §7 — Examples

### Example 1: Flow A — Create from chat, duplicate found

Input: "Create a Jira ticket for the auth timeout bug Bob mentioned — users are getting logged out after 5 min. Put it in PROJ, assign to Alice."

```
§2 Routing:
  Signal gate: "Create a Jira ticket" → create intent ✓
  Flow selection: no existing key + create intent → Flow A

A1 Extract:
  summary: "Auth timeout bug — users logged out after 5 min"
  description: context from chat
  project_key: "PROJ" (candidate — validate in A3)
  assignee_name: "Alice" (explicit: "assign to Alice")
  Note: "Bob mentioned" → Bob is context, NOT assignee (no @mention, no assignment language)

A2 Schema (concurrent with A3):
  Step 1: get_fields → captured custom fields, duedate exists
  Step 2: create metadata for PROJ → Task valid. field_confidence: "full"
  Custom field mapping: no custom fields match thread content → resolved_custom_fields: []

A3 Target Resolution (concurrent with A2):
  Project validation: JQL "project = PROJ" → 1 result → valid
  Duplicate check Pass 1: JQL "project = PROJ AND text ~ 'auth timeout'" → 1 result: PROJ-89 "Auth session timeout", status: In Progress
  → PROJ-89 is non-Done → ask user: reuse/update PROJ-89 or create distinct new issue?
  User confirmed reuse → action: update (not create)

A4 Resolve Assignee:
  No email in context → lookup by name "Alice" → 1 match → accountId: "abc123"

A6 Lock Context:
  flow: A, targets: [{issue_key: "PROJ-89", action: "update", planned_diffs: [description, assignee]}]

E0: Validate fields → pass
E1: edit_issue(PROJ-89, {description: ..., assignee: "abc123"})
E2: get_issue(PROJ-89) → fields match

Output:
  ✅ PROJ-89 — updated description, assigned to Alice — [View](https://acme.atlassian.net/browse/PROJ-89)
```

### Example 2: Flow C — Bulk create from transcript, one claimed create

Input: Meeting transcript with 3 action items:
1. "Alice will set up the staging environment"
2. "Bob, can you update the API docs?"
3. "I already created a ticket for the deploy pipeline fix" (Carol)

```
§2 Routing: Flow C (transcript + multiple items)

A1 Extract:
  Items:
    {task: "Set up staging environment", assignee: "Alice"}
    {task: "Update API docs", assignee: "Bob"}
    {task: "Deploy pipeline fix", assignee: null, claimed_create: true}

A2 Schema:
  Step 2: create metadata for PROJ, Task valid. field_confidence: "full"
  Custom field mapping: no required custom fields → resolved_custom_fields: []

A3 Target Resolution:
  Project validation: ✓
  No duplicate check for normal items (Flow C — by design).
  Claimed-create verification: JQL "text ~ 'deploy pipeline fix'" → PROJ-92 found → skip create.

A4 Resolve Assignee:
  Alice: matched via attendee email → accountId: "abc123"
  Bob: lookup by name → 2 matches, neither exact → proceed unassigned

A6 Lock Context: 3 targets (2 create, 1 skip)

E1: Batch:
  create_issue(PROJ, "Set up staging environment", assignee: "abc123") → PROJ-95
  create_issue(PROJ, "Update API docs") → PROJ-96
E2: read-back both → match

Output:
  🎫 PROJ-95 created — Set up staging environment — [View](...)
  🎫 PROJ-96 created — Update API docs — [View](...)
     ⚠️ Assignee "Bob" matched multiple users — created unassigned
  ✅ PROJ-92 — already exists (claimed by Carol, verified) — [View](...)
  Summary: 2 created, 1 already existed, 0 failed out of 3 items.
```

### Example 3: Flow A — Create with required custom field from Zoom thread

Input: "Create a ticket in PROJ — @Requester runtime is crashing when user memory exceeds limit"

```
§2 Routing: Flow A (create intent, no existing key)

A1 Extract:
  summary: "Runtime crashing when user memory exceeds limit"
  project_key: "PROJ" (candidate from user text)
  assignee_name: "Requester" (extracted from @mention per invariant 7)

A2 Schema:
  Step 1: get_fields → custom fields include a candidate business field from the target org
  Step 2: create metadata for PROJ → Task valid, `customfield_<resolved_id>` required. field_confidence: "full"
  Custom field mapping:
    "<required field label>" → Layer 1: scan thread → no explicit match found
    → Layer 2: LLM inference — summary says "runtime crashing when user memory exceeds limit"
      → allowed_values: ["platform", "mobile", "infra", "frontend"]
      → "runtime" + "memory" → "platform" is clearly the best fit → high confidence
    → resolved_custom_fields: [{id: "customfield_<resolved_id>", name: "<required field label>", value: "platform", payload_value: {"value": "platform"}, inference_source: "llm"}]

A3: Project PROJ valid. No duplicate found → action: create.

A4: Lookup "Requester" → accountId: "<resolved_account_id>"

A6 Lock Context:
  planned_diffs: [summary, assignee, customfield_<resolved_id>("platform")]
  resolved_custom_fields: [{id: "customfield_<resolved_id>", value: "platform", payload_value: {"value": "platform"}}]

E1: create_issue(PROJ, summary: "Runtime crashing...", assignee: "<resolved_account_id>", additional_properties: {"customfield_<resolved_id>": {"value": "platform"}})
E2: read-back → match

Output:
  🎫 PROJ-201 created — Runtime crashing when user memory exceeds limit — [View](...)
  ⚠️ Field "<required field label>" not found in thread — inferred "platform" from ticket context (LLM inference)
```

### Example 4: Flow E — Add watcher and link issues

Input: "Add @Carol as watcher on PROJ-89, and link it to PROJ-92 as 'blocks'"

```
§2 Routing: Flow E (explicit key + update intent)

A1 Extract:
  issue_key: "PROJ-89"
  watcher: "Carol"
  link_target: "PROJ-92", link_type: "blocks"

A3: Fetch PROJ-89 → exists. Fetch PROJ-92 → exists.
A4: Resolve "Carol" → accountId: "carol456"

A6 Lock Context:
  targets: [
    {issue_key: "PROJ-89", action: "watch", planned_diffs: [{field: "watcher", proposed: "carol456"}]},
    {issue_key: "PROJ-89", action: "link", planned_diffs: [{field: "link", proposed: "Blocks → PROJ-92"}]}
  ]

E1:
  add_watcher(PROJ-89, "carol456")
  create_issue_link(type: "Blocks", inwardIssue: "PROJ-89", outwardIssue: "PROJ-92")
E2: read-back PROJ-89 → confirmed

Output:
  👁️ PROJ-89 — added Carol as watcher — [View](https://acme.atlassian.net/browse/PROJ-89)
  🔗 PROJ-89 → Blocks → PROJ-92 — [View](https://acme.atlassian.net/browse/PROJ-89)
```

### Example 5: Flow F — List from saved-filter URL

Input: "从 https://example.atlassian.net/issues?filter=12345 中获取所有的 bug"

```
§2 Routing:
  Signal gate: Jira filter URL + read intent ("获取所有的 bug") → Flow F

A1 Extract:
  filter_id: "12345" (parsed from URL ?filter=12345)
  read_criteria: { issuetype: "Bug" }

A1.5: filter URL is a complete anchor → no ask needed.

A2 / A3 / A5 / A6 (write surface): skipped per Flow F simplifications.

E1 Read:
  jira_search_for_issues_using_jql_post(
    jql: "filter = 12345 AND issuetype = Bug ORDER BY updated DESC",
    fields: ["key","summary","status","priority","assignee","updated"],
    max_results: 50
  )
  → 23 results

Output:
  📋 23 issues from filter 12345 (issuetype = Bug) — [Filter View](https://example.atlassian.net/issues?filter=12345)
  • PROJ-101 — [In Progress] Auth timeout after 5 min idle — Alice — High — [View](...)
  • PROJ-102 — [To Do] Memory leak in worker pool — unassigned — Medium — [View](...)
  • PROJ-103 — [Done] Login redirect loop on Safari — Bob — High — [View](...)
  ... (20 more)
  Summary: 8 In Progress, 12 To Do, 3 Done.
```

### Example 6: Flow F — Single-key lookup

Input: "Show me PROJ-89 and PROJ-100"

```
§2 Routing:
  Signal gate: explicit issue keys + read intent ("show me") → Flow F (single-key path)

A1 Extract:
  issue_keys: ["PROJ-89", "PROJ-100"]
  No JQL composition needed.

E1 Read (parallel):
  jira_get_issue("PROJ-89", fields: ["key","summary","status","priority","assignee","reporter","issuetype"])
  jira_get_issue("PROJ-100", fields: ["key","summary","status","priority","assignee","reporter","issuetype"])

Output:
  🔎 PROJ-89 — [In Progress] Auth session timeout — Alice — High — [View](https://acme.atlassian.net/browse/PROJ-89)
  🔎 PROJ-100 — [Done] Migrate config loader — Bob — Medium — [View](https://acme.atlassian.net/browse/PROJ-100)
```

### Example 7: Flow F — Criteria-based listing (composed JQL)

Input: "List all my open bugs in PROJ updated this week"

```
§2 Routing:
  Signal gate: list intent + read criteria → Flow F (JQL composition)

A1 Extract:
  read_criteria: {
    project: "PROJ",
    issuetype: "Bug",
    assignee_filter: "me",
    status: "open" (interpreted as `statusCategory != Done`),
    time_range: "this week"
  }

A1.5: project = "PROJ" stated; assignee = currentUser(); time bounds resolved
       to absolute dates from `## Current Context` (e.g. 2026-04-27 to 2026-05-03).

A4: assignee_filter = "me" → use currentUser() in JQL (no jira_find_users call needed).

E1 Read:
  jira_search_for_issues_using_jql_post(
    jql: "project = PROJ AND issuetype = Bug AND assignee = currentUser() \
          AND statusCategory != Done AND updated >= '2026-04-27' \
          ORDER BY updated DESC",
    fields: ["key","summary","status","priority","updated"],
    max_results: 50
  )
  → 6 results

Output:
  📋 6 issues from JQL (project = PROJ AND issuetype = Bug AND assignee = currentUser() AND statusCategory != Done AND updated >= 2026-04-27)
  • PROJ-89 — [In Progress] Auth session timeout — Highest — [View](...)
  • PROJ-95 — [To Do] Memory leak in worker — High — [View](...)
  • PROJ-101 — [In Progress] Login redirect loop — Medium — [View](...)
  ... (3 more)
  Summary: 3 In Progress, 3 To Do.
```

### Example 8: Flow C — Bulk create with required custom field, mixed Layer 2 / Layer 3 resolution

Input: Cross-functional brainstorm meeting transcript with 3 action items:
1. "Alice, please write up the iOS 17 crash investigation"
2. "Bob will draft the analytics rollout plan for Q3"
3. "Carol owns the customer onboarding form redesign"

Project PROJ has a required custom field `customfield_<resolved_id>` ("team") with metadata-backed `allowed_values: ["platform", "mobile", "marketing", "sales"]`.

```
§2 Routing: Flow C (transcript + multiple items)

A1 Extract:
  Items:
    {task: "Write iOS 17 crash investigation", assignee: "Alice"}
    {task: "Draft analytics rollout plan for Q3", assignee: "Bob"}
    {task: "Customer onboarding form redesign", assignee: "Carol"}

A2 Schema:
  jira_get_create_meta_issue_types(PROJ) → Task valid, customfield_<resolved_id> "team" required
  field_confidence: "full"

  Per-item custom field resolution (Flow C, 4-layer):

  Item 1 ("Write iOS 17 crash investigation"):
    Layer 1: scan task text vs allowed_values → no match (no token "platform"/"mobile"/etc.)
    Layer 2: full-context inference
      (a) item text: "iOS 17 crash" — strong "mobile" signal
      (b) source context: cross-functional brainstorm — no narrowing
      (c) sibling pattern: no resolved siblings yet
      (d) sibling values: none
      → plausible signal: "iOS" + "crash" → mobile platform work
      → commit: team="mobile", inference_source: "llm"

  Item 2 ("Draft analytics rollout plan for Q3"):
    Layer 1: no match
    Layer 2:
      (a) item text: "analytics rollout plan" — could be platform (data infra), marketing (campaign), sales (enablement)
      (b) source: Q3 brainstorm — no narrowing
      (c) sibling pattern: only 1 sibling resolved (mobile) — insufficient pattern
      (d) sibling values: not enough to extrapolate
      → no input isolates a single value → fall through to Layer 3

  Item 3 ("Customer onboarding form redesign"):
    Layer 1: no match
    Layer 2:
      (a) item text: "customer onboarding form" — could be marketing, sales, or mobile
      (b) source: Q3 brainstorm — no narrowing
      (c) sibling pattern: 1 mobile, 1 unresolved — insufficient
      → no plausible signal → fall through to Layer 3

  After Layer 1+2:
    item 1: resolved (team="mobile", llm)
    item 2: unresolved
    item 3: unresolved

A1.5 Phase 2 — trigger #4 fires (2 unresolved required custom fields with allowed_values):
  agent.ask_user_questions(questions: [
    {
      type: "select",
      question: "For ticket 'Draft analytics rollout plan for Q3' (assignee: Bob): which team owns this?",
      options: ["platform", "mobile", "marketing", "sales"]
    },
    {
      type: "select",
      question: "For ticket 'Customer onboarding form redesign' (assignee: Carol): which team owns this?",
      options: ["platform", "mobile", "marketing", "sales"]
    }
  ])

  ▸ ONE tool call, TWO question objects — NEVER collapsed into a single shared question.
  ▸ Item 1 already resolved at Layer 2 → NOT included in this call.
  ▸ Frontend renders one adaptive card with two form fields; user fills both, submits once.

User answers: ["marketing", "mobile"]
  → item 2: team="marketing", inference_source: "user"
  → item 3: team="mobile", inference_source: "user"

A6 Lock Context:
  per_item_custom_fields:
    item 1: [{id: "customfield_<resolved_id>", value: "mobile", payload_value: {"value":"mobile"}, inference_source: "llm"}]
    item 2: [{id: "customfield_<resolved_id>", value: "marketing", payload_value: {"value":"marketing"}, inference_source: "user"}]
    item 3: [{id: "customfield_<resolved_id>", value: "mobile", payload_value: {"value":"mobile"}, inference_source: "user"}]

E1 Bulk create (each call carries its own additional_properties from per_item_custom_fields):
  jira_create_issue(PROJ, summary: "Write iOS 17 crash investigation", assignee: "<alice_account_id>", additional_properties: {"customfield_<resolved_id>": {"value":"mobile"}}) → PROJ-201
  jira_create_issue(PROJ, summary: "Draft analytics rollout plan for Q3", assignee: "<bob_account_id>", additional_properties: {"customfield_<resolved_id>": {"value":"marketing"}}) → PROJ-202
  jira_create_issue(PROJ, summary: "Customer onboarding form redesign", assignee: "<carol_account_id>", additional_properties: {"customfield_<resolved_id>": {"value":"mobile"}}) → PROJ-203

E2 Read-back: all 3 match planned values.

Output:
  🎫 PROJ-201 created — Write iOS 17 crash investigation — [View](https://example.atlassian.net/browse/PROJ-201)
     ⚠️ team inferred as "mobile" (LLM, from item text "iOS 17 crash")
  🎫 PROJ-202 created — Draft analytics rollout plan for Q3 — [View](https://example.atlassian.net/browse/PROJ-202)
  🎫 PROJ-203 created — Customer onboarding form redesign — [View](https://example.atlassian.net/browse/PROJ-203)
  Summary: 3 created, 0 skipped, 0 failed out of 3 items.
```

**Key takeaways from this example:**
- **Layer 2 commits per-item**, not all-or-nothing. Item 1 resolves; items 2 & 3 fall through.
- **Per-item ask = N question objects in ONE `agent.ask_user_questions` call**. The array carries one question per unresolved item, each prefixed with its ticket summary. Already-resolved items are NOT in the array.
- **Never collapse multiple unresolved items into one shared question for the same field.** Items may legitimately differ.
- **Share-vs-differ is emergent**: item 1's "mobile" came from its own text; items 3's "mobile" came from the user. Same value, different source — the design produces this naturally without an explicit share-vs-differ step.
- **⚠️ marks every `"llm"`-inferred required field**, never `"user"`-provided ones (which are authoritative).
