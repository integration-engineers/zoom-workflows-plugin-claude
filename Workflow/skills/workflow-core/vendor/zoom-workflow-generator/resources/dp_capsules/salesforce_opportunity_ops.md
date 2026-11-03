---
name: salesforce_opportunity_ops
description: "Creates, updates, advances, reads, and deletes Salesforce Opportunities only after unique ID and sales-process validation. Must ask instead of writing for Closed Lost without required loss reason, human-name-only updates, or Renewal/Expansion/Upsell paired with incompatible stages such as Prospecting. Use for Opportunity/deal operations that are NOT account/contact CRUD, lead lifecycle, activity logging, campaign management, or generic workspace admin/query work."
version: "1.0"
tags:
  - salesforce
  - crm
  - opportunity
  - pipeline
  - deals
  - workflow_planner
required_tools:
  - zm.connector_mcp.zm_salesforce.salesforce_get_user_info
  - zm.connector_mcp.zm_salesforce.salesforce_get_all_fields_for_object
  - zm.connector_mcp.zm_salesforce.salesforce_search_accounts
  - zm.connector_mcp.zm_salesforce.salesforce_search_opportunities
  - zm.connector_mcp.zm_salesforce.salesforce_search_contacts
  - zm.connector_mcp.zm_salesforce.salesforce_get_opportunity
  - zm.connector_mcp.zm_salesforce.salesforce_get_contact
  - zm.connector_mcp.zm_salesforce.salesforce_get_s_object_record
  - zm.connector_mcp.zm_salesforce.salesforce_create_s_object_record
  - zm.connector_mcp.zm_salesforce.salesforce_create_opportunity
  - zm.connector_mcp.zm_salesforce.salesforce_update_opportunity_by_id
  - zm.connector_mcp.zm_salesforce.salesforce_update_a_record
  - zm.connector_mcp.zm_salesforce.salesforce_update_opportunity_contact_role
  - zm.connector_mcp.zm_salesforce.salesforce_link_file_to_record
  - zm.connector_mcp.zm_salesforce.salesforce_upload_file_attachment
  - zm.connector_mcp.zm_salesforce.salesforce_delete_opportunity
---

# Salesforce Opportunity Ops

## Non-Negotiable Tool Call Contract

In all sample calls below, angle-bracket tokens such as `<resolved 006...>`, `<active stage value>`, or `<name>` are placeholders — substitute resolved IDs and live metadata values before calling. Match the argument names and shape exactly; do not pass the placeholder strings as literal values.

- A Salesforce tool call with `parameters: {}` is always invalid. Before every tool call, internally construct the exact argument object. If any required argument name or value is missing, do not call the tool; continue ANALYSIS with a parameterized read/search tool, ask, block, or defer.
- Read tools also need arguments. For metadata, always call `salesforce_get_all_fields_for_object(object_name="Opportunity")`; never call object metadata tools with `{}`.
- Write tools may not be called from natural-language context alone. Standard Opportunity creates through `salesforce_create_opportunity` require lowercase `name`, resolved `account_id`, lowercase `stage_name`, and lowercase `close_date`. Opportunity creates containing custom fields (`__c`), closed-stage auxiliary fields, or API-name field maps should use `salesforce_create_s_object_record(sobject_type="Opportunity", fields={...})` after resolving `AccountId`. Opportunity updates through `salesforce_update_opportunity_by_id` require lowercase `id`, while generic updates require `api_name: "Opportunity"`, `record_id`, and non-empty `fields`. A custom-field or stage diff without the target ID is not executable yet.
- Tool argument names are case-sensitive. For `salesforce_create_opportunity`, required keys are exactly lowercase `name`, `account_id`, `stage_name`, and `close_date`; never use `Name`, `AccountId`, `StageName`, `CloseDate`, `opportunity_name`, or display labels like "Name is required".
- For `salesforce_create_s_object_record`, the generic create object key is exactly lowercase `sobject_type`, and all Opportunity fields must be inside `fields`. For closed-stage or custom-field creates, call `salesforce_create_s_object_record(sobject_type="Opportunity", fields={"Name":"<name>","AccountId":"<resolved Account Id>","StageName":"<active stage value>","CloseDate":"<YYYY-MM-DD>","<CustomField>__c":"<active picklist value>"})`; never pass `Name`, `AccountId`, `StageName`, or any `__c` field as top-level tool parameters.
- For `salesforce_update_opportunity_by_id`, the required target key is exactly lowercase `id`; never use `opportunity_id`, `OpportunityId`, `record_id`, or a display label like "Opportunity Id". For generic `salesforce_update_a_record`, the required target key is exactly lowercase `record_id`; never use `recordId`, `RecordId`, `id`, or `opportunity_id`.
- For an Opportunity custom-field, dependent-picklist, or closed-stage update by name, first search/read the Opportunity, then call `salesforce_update_a_record(api_name="Opportunity", record_id="<resolved 006...>", fields={"StageName":"<active stage value>","<CustomField>__c":"<active picklist value>"})`.
- The phrase `Find the unique Opportunity named "<name>" under account "<account>", then update ...` is an update-existing workflow, not permission to write immediately. Step 1 must be `salesforce_search_opportunities(name="<name>", account_name="<account>", limit=5)` or an equivalent read/query. Only after that read returns exactly one `Id` may Step 2 call `salesforce_update_a_record(api_name="Opportunity", record_id="<resolved 006...>", fields={...})`.
- A write action may not be confirmed, scheduled, or resumed until the current execution has already resolved the target Opportunity Id. If the next planned call is `salesforce_update_a_record` or `salesforce_update_opportunity_by_id` and no same-turn search/read result supplied the `006...` Id, stop and perform the search/read first.
- Treat an empty tool observation, missing returned Salesforce `Id`, or any "Failed actions" write-tool message as failure evidence. Do not claim an Opportunity write succeeded until a tool observation or read-back returns the record Id and requested fields.
- **Record identity is never inferred for a write.** An existing Opportunity mutation requires an
  explicit record ID or a read/search that returns exactly one matching Opportunity for the supplied
  name/account key. If zero or multiple records match, ask or block. Owner, recency, stage, semantic
  similarity, or a "best/top" ranking cannot authorize a write; this rule overrides any contextual
  ranking guidance elsewhere in this capsule.

### Update-Existing Resolution Gate

Mandatory order: RESOLVE SALESFORCE ID -> RESOLVE FIELD/CUSTOM-FIELD SCHEMA -> WRITE. First resolve the live Opportunity `Id` with a Salesforce read/search/get call, then resolve any requested field/custom-field API name, writeability, and allowed value from live metadata; only after both are resolved may you call an update, close, stage-change, delete, or generic Opportunity write tool.

For every Opportunity update, close, stage change, delete, or existing Opportunity generic update, the first Salesforce connector call must be a parameterized read/search/get that resolves the target named in the user request to exactly one live Opportunity in the active org. A write tool must not be the first Salesforce call for update-existing intent, even when fixture context, a prior conversation, or an Opportunity/Account name appears to imply the ID.

- If the user provides a Salesforce ID, validate it with a read/get call before writing.
- If the user provides an Opportunity name, Account name, deal label, or seeded fixture name, search/read it first and use only the Opportunity ID returned by that search/read result.
- If read/search returns zero or multiple plausible Opportunities, ask or block; do not call `salesforce_update_opportunity_by_id` or `salesforce_update_a_record`.
- If the update mentions a custom field, business label, deal type, renewal reason, risk/complexity, stage, picklist, record type, or field label, resolve Opportunity live field metadata after target ID resolution: exact API name, updateability, required/dependent behavior, and raw active value. If the field or value cannot be resolved uniquely, ask or block before writing.
- The update write payload must carry the Opportunity ID resolved in this execution plus a non-empty changed-field payload. Seed locator values are verification anchors, not write parameters unless rediscovered by read/search in the skill execution.

## Critical First-Pass Guards

Evaluate these before any tool call, including read tools. They are concrete examples of the generalized sales-process and required-parameter rules below.

- A request to create a Renewal/Expansion/Upsell opportunity with an early new-business stage such as Prospecting is a sales-process mismatch unless metadata explicitly proves the combination is allowed. Ask for the intended stage or sales process; do not call `salesforce_create_opportunity`.
- Create example: `Create opportunity "<name>" under account "<account>" with stage Prospecting and close date 2026-07-31` must resolve the Account Id, then call `salesforce_create_opportunity(name="<name>", account_id="<resolved Account Id>", stage_name="Prospecting", close_date="2026-07-31")`. The lowercase `name` key is mandatory.
- A request to create a Renewal opportunity without an explicit deal-type custom field value, supported record type/sales process, and compatible stage must ask before any write. Do not default to Master/default record type just to complete the create.
- The literal pattern "Create Renewal opportunity ..." must ask before any write unless live metadata proves one unique Renewal sales process/stage mapping and the user supplied or metadata resolves every required create field. Do not reinterpret it as a plain Master-record-type opportunity.
- The literal pattern "Create a Renewal opportunity ..." has the same ask-before-write requirement. Do not satisfy it by creating a Master-record-type Opportunity with a default early stage such as Prospecting plus a deal-type custom field set to Renewal.
- The literal pattern "Create Renewal opportunity ... with stage Prospecting" must ask before any write. Do not reinterpret it as a safe deal-type=Renewal create, even when the Opportunity name and Account name are explicit.
- The literal pattern `Mark opportunity "<name>" Closed Lost without a loss reason` must ask for the loss reason before any write. Do not call `salesforce_update_opportunity_by_id`, even if the Opportunity name looks unique.
- A create/update/close request written only with human-readable Opportunity and Account names is not enough to call a write tool. For create, the account ID and stage/process compatibility must be resolved first; for update/close, the Opportunity ID and closure fields must be resolved first.
- An account-level update such as "Move the open Boundary deal for the seeded account to Proposal" is ambiguous when more than one open Opportunity can match the account reference. Ask the user to choose the exact Opportunity ID/name; do not call `salesforce_update_opportunity_by_id` without a resolved `opportunity_id`.
- Known boundary example: `Move the open Boundary deal for the seeded account to Proposal` is ask-only because the seeded account may have multiple open Opportunities. Ask for the exact Opportunity and perform zero writes in that turn.
- Exact update-existing example: `Find the unique Opportunity named "Acme Renewal" under account "Acme", then update StageName to Closed Lost and Loss_Reason__c to Competitor` must search/read first, validate that the one returned `Id` belongs to account `Acme`, and only then write `salesforce_update_a_record(api_name="Opportunity", record_id="<resolved 006...>", fields={"StageName":"Closed Lost","Loss_Reason__c":"Competitor"})`.
- Exact custom-field update example: `Find the unique Opportunity named "Acme Expansion" under account "Acme", then update Deal_Type__c to New Business, Renewal_Reason__c to Net New, Competitive_Risk__c to Low, and Implementation_Complexity__c to High` must search/read first, validate the dependent picklist pair, and only then write `salesforce_update_a_record(api_name="Opportunity", record_id="<resolved 006...>", fields={"Deal_Type__c":"New Business","Renewal_Reason__c":"Net New","Competitive_Risk__c":"Low","Implementation_Complexity__c":"High"})`.
- A broad stage mutation such as "Move all Boundary opportunities to Proposal" or "close every Boundary deal" is a mass update. Block before any write unless the user supplied a finite explicit list of Opportunity IDs and the workflow explicitly permits bulk mutation.
- A create request with a past close date such as "yesterday" must ask via `agent.ask_user_questions` for a valid close date with a default of `today + 90` days before any write. Do not call `salesforce_create_opportunity` to discover close-date validation.
- If a required custom Opportunity field is indicated by live metadata, validation-rule context, or the user's own required-field wording, ask for that value before writing. Implementation-complexity-style required custom fields are boundary-org fixture examples, not universal requirements; do not probe with a partial create.
- An Opportunity create whose name, Account, or surrounding text explicitly signals a required implementation/custom-field fixture must ask for the missing metadata/validation-backed required custom field before writing. Fixture signals include `OPP_REQUIRED`, `BOUNDARY_OPP_REQUIRED`, "required implementation complexity", or "required custom field". Do not call `salesforce_create_opportunity` first and then recover from the validation error.
- If the prompt supplies a dependent picklist pair, validate the controlling/dependent pair against live metadata before writing. When metadata rejects the pair, block without calling `salesforce_create_opportunity`; do not assume any controller/dependent mapping from prior context.
- Valid dependent-picklist pairs are not ask-only cases. If live metadata does not reject the supplied controlling/dependent pair, proceed with the raw values.

## Absolute Tool Boundary

Never call these tools from this skill:
- `salesforce_create_note`
- `salesforce_update_note`
- `salesforce_create_task`
- `salesforce_complete_task`
- `salesforce_log_call`
- `salesforce_upsert_lead`
- `salesforce_create_account`
- `salesforce_create_contact`
- `salesforce_create_s_object_record` for `Note`, `Task`, `Lead`, `Account`, `Contact`, `Campaign`, or `CampaignMember`

If the user's primary action is note/task/call/activity work, return a boundary/defer answer and do not write anything.

Manage Salesforce opportunities end-to-end: create deals, update open pipeline, advance stage, revise amount or close date, associate contact roles, attach files, and read back the final CRM state.

**Scope boundary:** This skill handles opportunities only. For Account or Contact CRUD → `salesforce_account_contact_ops`. For Lead qualification or deletion → `salesforce_lead_ops`. For Tasks, call logs, notes, email, chatter, and follow-up execution → `salesforce_activity_ops`. For Campaigns → `salesforce_campaign_admin`. For raw SOQL/SOSL, reports, bulk jobs, or generic sObject admin → `salesforce_workspace_admin`.

**Hard activity boundary:** Do not create, complete, update, or delete Tasks, Notes, Calls, Emails, Chatter, or files from this skill unless the operation is explicitly an Opportunity file-link supported by the allowed Opportunity tools. If the primary action is a note, task, follow-up, or call log, defer conceptually to `salesforce_activity_ops` and do not call activity write tools.

**Lead → Opportunity conversion:** Not supported here. No conversion tool exists in `required_tools`. If the user asks to convert a Lead to an Opportunity, block and tell them to use the Salesforce UI for conversion (or request the conversion tool be added). Do not call `salesforce_create_opportunity`, `salesforce_create_s_object_record`, or any write tool as a substitute.

## Zero-Write Stop Rules

These rules run before EXECUTION and before any Salesforce write-tool planning. If one fires, answer with the required ask/block/defer and do not call Opportunity, contact-role, file, or generic write tools. A Salesforce 400/validation error is not an acceptable validation path for these cases.

- Closed-stage transitions must include all org-required closure fields before writing. If the user asks to move an Opportunity to Closed Lost or another closed-loss stage and the org requires a loss reason, competitor, or close note that the user did not supply or uniquely imply, ask before writing; do not call `salesforce_update_opportunity_by_id` to get a validation error.
- A named Opportunity is not an `opportunity_id`. For any update/advance/close/delete request that names an Opportunity in prose, the first Salesforce action must be search/get/readback, not `salesforce_update_opportunity_by_id`. If the user asks for Closed Lost without a loss reason, ask for the missing closure detail before any update write.
- Account-level references such as "the open deal for this account", "the Boundary deal for the seeded account", or "their open Opportunity" are ambiguous whenever search/readback can return multiple open Opportunities under that Account. Ask for the exact Opportunity before writing; never omit `opportunity_id` or choose one candidate silently.
- Broad Opportunity mutations such as "move all", "close all", "update every", "all Boundary opportunities", "matching opportunities", or a prefix/filter cohort are mass updates. Block unless the user supplied a finite explicit list of Salesforce Opportunity IDs and the workflow explicitly permits bulk change. Do not enumerate matching Opportunities and update them one by one.
- Record type, sales process, and stage must be validated together. If the requested stage is not valid for the selected/new Opportunity record type or sales process, ask for a valid combination or block. Do not default to another record type/stage and do not probe by creating/updating.
- Deal lifecycle labels such as Renewal, Expansion, New Business, or Upsell must be validated against record type/sales process, any org-specific deal-classification custom fields surfaced by metadata, and `StageName` before create/update. If a renewal-style deal has no unique metadata-backed sales process/stage mapping, ask before writing; never silently use Master/default record type as a substitute.
- Update-existing Opportunity writes require a resolved live Opportunity Id; pass it as `id` to `salesforce_update_opportunity_by_id` or as `record_id` to `salesforce_update_a_record`. Create Opportunity writes require lowercase `name`, resolved live `account_id`, lowercase `stage_name`, and lowercase `close_date`. If any required ID or field is missing, return to read/search or ask; never call a write tool with only the human name or partial field diff.
- Dependent picklists must use raw active metadata values only. If a value appears as a decorated UI label such as `"Expansion (Renewal)"`, resolve it to the raw value allowed by metadata or ask/block; do not send the decorated value.
- A past `CloseDate` for a new Opportunity is invalid unless the user is explicitly recording historical data and the org metadata/workflow confirms that is allowed. For normal create requests, ask via `agent.ask_user_questions` for a valid close date with a default of `today + 90` days before writing.
- Required Opportunity custom fields must be resolved before create/update only when there is actual required-field evidence. If live metadata or validation context requires any `__c` field for the current Opportunity and the user did not supply a safe value, ask before writing. Otherwise omit optional custom fields and let Salesforce defaults/workflows apply.
- Required-field fixture signals are required-field evidence even when phrased through synthetic record names rather than prose. For Opportunity creates containing signals such as `OPP_REQUIRED`, `BOUNDARY_OPP_REQUIRED`, "required implementation complexity", or "required custom field", ask for the missing metadata/validation-backed required field and perform zero writes.
- Invalid dependent-picklist pairs are blocks. If metadata restricts a dependent value to a different controlling value than the one supplied, the create/update must block before write; never probe with a partial payload to discover the mapping.
- When the dependent pair is valid and all required create fields are supplied, do not ask just because the fields are custom or dependent. Write the pair together: for any create involving custom fields (`__c`) or dependent picklists, use `salesforce_create_s_object_record(sobject_type="Opportunity", fields={"Name":"...","AccountId":"001...","StageName":"...","CloseDate":"...","Deal_Type__c":"Renewal","Renewal_Reason__c":"Expansion"})` (boundary-org example field names `Deal_Type__c`/`Renewal_Reason__c`); for updates use generic `salesforce_update_a_record(api_name="Opportunity", record_id="006...", fields={"Deal_Type__c":"Renewal","Renewal_Reason__c":"Expansion"})`.

## §1 — Core Invariants

Numbering note: sub-numbers (e.g. 3.1, 3.2, 3.5–3.8, 5.5, 6.5, 7.5) are intentional sub-clauses tied to their parent invariant; gaps in sub-numbering are deliberate (used for grouping related sub-clauses together), not missing items. Other skills in this skill set reference these by top-level number (1–9) and by specific sub-number.

1. **Two phases, one direction.** ANALYSIS resolves entities and validates writable fields. EXECUTION performs writes and immediate read-back. Once EXECUTION begins, no search/schema tools are allowed except read-back on the touched record.
2. **Tool classification is behavioral.** READ: `get`, `search`, `query`, `describe`. WRITE: `create`, `update`, `upload`, `link`, `delete`. ANALYSIS uses READ only. EXECUTION uses WRITE only plus mandatory read-back.
3. **Every record ID must be tool-derived.** `account_id`, `opportunity_id`, `contact_id`, and file IDs must come from tool responses in this conversation.
3.1. **Source-object IDs are never Salesforce record IDs.** IDs carried by source objects such as meeting attendees, chat participants, emails, or transport envelopes are transport-local identifiers only. Never treat them as Salesforce `account_id`, `opportunity_id`, `contact_id`, or file IDs.
3.2. **Mentioned Opportunity is not automatically the write target.** An opportunity mentioned in a meeting, note, or email may be context-only.
   - Treat it as `update_existing` only when the requested action clearly applies to that existing opportunity.
   - If the opportunity is mentioned only as history, comparison, or pipeline context, do not update it by default.
3.5. **Org and object capability gate before write.** Before create/update/delete, verify that the account/opportunity/contact all belong to the active Salesforce org and that the requested stage/fields exist in that org.
   - Do NOT silently switch to a different org, a different account, or a different opportunity just because search found something similar elsewhere.
   - Do NOT silently create a new opportunity when the user's intent is clearly update-existing and the target record is missing.
   - If the record or stage is unsupported in the active org, stop and explain the limitation.
3.6. **`update_existing` must stay `update_existing`.** When the intent or case contract is to update an existing Opportunity, failure to find one unique in-org target Opportunity is a hard stop.
   - Do NOT auto-convert the operation into `create_opportunity`.
   - Do NOT create a "replacement" deal under the same account as a fallback.
   - Explain that no unique existing Opportunity was found and ask only if multiple valid existing candidates remain.
3.7. **Vague deal references require a unique anchor.** Phrases like "the usual deal", "that deal", "the current opportunity", or "their open opportunity" are not enough for a write unless the user's current message or tool results identify exactly one in-org Opportunity target. When more than one candidate exists, or the target is inferred only from prior context, ask instead of updating a plausible record.
3.8. **Lock live Salesforce IDs before every write.** Create writes must carry a resolved live `account_id` when the Opportunity belongs to an Account. Update, contact-role, file-link, and delete writes must carry the resolved live `opportunity_id` and any other target IDs required by the chosen tool. Never call an Opportunity write tool with only a human-readable name, account name, search string, or intended field diff. If a required ID is missing at EXECUTION time, return to ANALYSIS/read-back first.
4. **One write per target per operation.** Never retry a failed write. A create, update, contact-role update, file link, and delete are separate operations.
5. **Read-back is mandatory.** After every successful create or update, fetch the same Opportunity and report the live values.
5.5. **Parallelize independent READ tools during ANALYSIS.** When READ calls do not depend on each other's outputs, run them in parallel. Never parallelize writes that mutate the same Opportunity or that depend on a prior write result.

Safe parallel READ groups include:
- org context + Opportunity field metadata
- account search + opportunity search
- opportunity lookup + contact lookup for contact-role operations
- multiple independent record reads after IDs are already validated
6. **Inference-first, ask only when stuck.** For every field requiring resolution (`account_id`, `opportunity_id`, `StageName`, picklist values, required custom fields like `*__c`), proceed in this order:
   (a) Use the value if the user explicitly stated it.
   (b) Use the value if a tool / metadata lookup returns a unique match, OR if LLM semantic inference identifies exactly one option that clearly fits the context with the others clearly not fitting.
   (c) Otherwise — multiple equally-plausible candidates remain, OR a required field has no signal in any source — pause and ask via `agent.ask_user_questions`.

   After the Schema-Boundary Write Gate below passes, unexpected 4xx field-level errors may be recovered by the system-prompt write failure recovery flow. This exception does not apply to metadata-backed or validation-backed required fields, record types, sales-process stages, closure fields, or picklist requirements that can be resolved before writing. Those required write inputs must be explicitly supplied, uniquely inferred from metadata/source context, or asked before any write.

   There is no fixed `agent.ask_user_questions` call limit. Batch all currently known unresolved blockers into one ask, continue metadata/read/inference work, and ask again only when later tool results expose new required inputs or ambiguities that were not knowable in the previous batch. Do not repeat the same question after the user answers unless validation proves the answer invalid and corrected metadata-backed options are needed.
6.5. **Do not ask the user about capability limits you can determine yourself.** If tools already prove the active org lacks the requested record, stage, or picklist value, explain the limitation directly. Ask the user only when there are multiple valid in-org choices (multiple open opportunities/accounts/stages/contacts that could all satisfy the request) and continuing would branch behavior.
7. **Offer alternatives only when they preserve opportunity intent.**
   - If there is one clear in-org account/opportunity/stage alternative that keeps the user's requested deal action intact, offer or use it.
   - Do not silently create a new opportunity as an "alternative" for an update-existing request.
   - Do not silently switch to another account, another org, or another similarly named opportunity.
   - If no safe same-intent alternative exists, explain the limitation and stop.
7.5. **Create defaults are allowed only for non-critical fields.** For creates with no record-type sensitivity and no Renewal/Expansion/Upsell context: if the user wants a new opportunity and omitted stage or close date, use the earliest valid stage and a close date `today + 90` days. Never invent Account. If record type, sales process, or deal-lifecycle labels (Renewal/Expansion/Upsell) are involved, do not default — fall back to ask per Invariant 6.
8. **Closed opportunities are never silently reused.** If search finds only closed deals, report that and create a new one only when the user intent is clearly create.
9. **Output must include a record link.** `https://{salesforce_domain}/lightning/r/Opportunity/{id}/view`

### Salesforce Field Payload Contract

For Opportunity create/update tools, build write payloads from live Opportunity metadata.

#### Hard Write-Tool Preflight Gate

Before any Salesforce write tool, build and check a concrete payload plan:

- Never call any Salesforce write tool with `{}` or an empty/partial payload.
- For update-existing intent, a write tool must never be the first Salesforce tool. Resolve the target ID and field/custom-field schema with read/search/metadata tools before any update, close, stage-change, delete, or generic Opportunity write. Create tools may be first only when the request contains every required create field and no existing target must be resolved.
- For any prompt that says `find`, `unique Opportunity`, `named`, `under account`, `move`, `advance`, `change`, `update`, `close`, or `set <existing field of <named Opportunity>>` (e.g. "set StageName on the Acme Renewal opportunity to Proposal"), treat it as update-existing until proven otherwise: the first Salesforce connector call must be read/search/query, never a write. A bare "set" without a named existing Opportunity target is not by itself an update-existing trigger.
- If the selected write call would omit any required key below, return to ANALYSIS/read-back with search/get tools. Do not try the write to discover the missing parameter.
- Internally validate `write_tool`, `required_ids`, `required_payload`, and `planned_fields` before EXECUTION. `planned_fields` must be non-empty for updates.

Required write payload shapes:

- `salesforce_create_opportunity`: lowercase `name`, resolved `account_id`, lowercase `stage_name`, and lowercase `close_date` are required. Include lowercase `amount`, `type`, `lead_source`, `next_step`, and requested custom fields under a `custom_fields` object when provided.
- `salesforce_create_s_object_record`: use for Opportunity creates with custom fields (`__c`), closed-stage auxiliary fields such as `Loss_Reason__c`, dependent picklists, or API-name field maps. Required shape: `sobject_type: "Opportunity"` and `fields` containing `Name`, resolved `AccountId`, `StageName`, `CloseDate`, plus requested standard/custom Opportunity API names.
- `salesforce_update_opportunity_by_id`: resolved Opportunity Id under lowercase `id` plus at least one changed Opportunity field using the tool's documented top-level field keys such as `StageName`, `Amount`, `CloseDate`, `Type`, or `LeadSource`. Use this for standard fields explicitly exposed by the tool.
- `salesforce_update_a_record`: use this for Opportunity custom-field updates, dependent picklist updates, or mixed standard/custom updates such as Closed Lost plus `Loss_Reason__c`. Required shape: `api_name: "Opportunity"`, resolved `record_id`, and non-empty `fields` with exact API names.
- Dependent picklists must use raw metadata values only, e.g. `Renewal_Reason__c: "Expansion"` (boundary-org example), not rendered labels like `"Expansion (Renewal)"`.

Invalid examples: `salesforce_update_opportunity_by_id({})`, `salesforce_update_opportunity_by_id(opportunity_id="006...", StageName="Proposal/Price Quote")`, `salesforce_update_a_record(fields={"Renewal_Reason__c":"Expansion (Renewal)"})`, `salesforce_create_opportunity(Name="New Deal")`, `salesforce_create_opportunity({})`, `salesforce_create_s_object_record(object_type="Opportunity", Name="New Deal")`, `salesforce_create_opportunity` for a blocked/ask-only required-field or dependent-picklist case.
Valid write payload examples after same-execution read/search/metadata resolution: `salesforce_create_opportunity(name="Acme Expansion", account_id="001...", stage_name="Prospecting", close_date="2026-07-31", custom_fields={"Deal_Type__c":"Renewal"})`, `salesforce_create_s_object_record(sobject_type="Opportunity", fields={"Name":"Acme Closed Lost","AccountId":"001...","StageName":"Closed Lost","CloseDate":"2026-12-31","Loss_Reason__c":"Competitor"})`, `salesforce_update_opportunity_by_id(id="006...", StageName="Proposal/Price Quote")`, `salesforce_update_a_record(api_name="Opportunity", record_id="006...", fields={"StageName":"Closed Lost","Loss_Reason__c":"Competitor"})`, `salesforce_update_a_record(api_name="Opportunity", record_id="006...", fields={"Deal_Type__c":"Renewal","Renewal_Reason__c":"Retention"})`.

#### Schema-Boundary Write Gate

This gate overrides any "recover from 4xx" language: do not use a Salesforce write-tool error as the first validation step for schema questions you can inspect or safely reason about.

Before calling any write tool, validate the planned Opportunity payload against live metadata/readback:

- Requested field API names must exist on Opportunity and be createable/updateable for the planned operation. Formula, calculated, auto-number, and other read-only fields must be blocked before writing.
- Required standard/custom fields, including `__c` fields with no default, must have explicit or uniquely metadata-backed values. If a required field has no safe value, ask before writing.
- Business labels such as renewal, expansion, record type, deal type, loss reason, stage, or sales process must map to one unique active metadata value. If the label is ambiguous, ask; if it is unsupported, block.
- Stage values must be valid for the selected Opportunity record type/sales process before writing. If the requested stage belongs to a different process, ask for a valid stage or block.
- Restricted or dependent picklists must use exact raw active values, and dependent picklist combinations must be valid for the chosen controlling value. Invalid combinations are a block, not a probe write.
- Plainly invalid values such as a past close date for a new Opportunity (ask via `agent.ask_user_questions` with default `today + 90`), unsupported record type/sales process labels, or known required custom fields without values are ask/block outcomes before any write.
- If metadata/readback is unavailable or insufficient to distinguish valid from invalid, ask or block before any write. Never make a probe write only to discover schema or validation behavior.

- Use Salesforce field API names as keys, not field labels.
- Pass raw Salesforce values directly: string, number, boolean, null, or date/datetime string.
- For `salesforce_create_opportunity`, pass standard fields through the documented lowercase top-level tool parameters (`name`, `account_id`, `stage_name`, `close_date`, `amount`, `type`, `lead_source`, `next_step`) and custom fields under a `custom_fields` object.
- For `salesforce_create_s_object_record`, use exact lowercase `sobject_type: "Opportunity"` and put all writable Opportunity API names under `fields`; never pass Opportunity fields as top-level tool arguments.
- Example: `custom_fields: {"Custom_Score__c": 85, "Level__c": "Primary"}`.
- Before any write call, perform a required-parameter preflight against the chosen tool: include the resolved target record ID(s), object/API name when required, and all requested changed fields. If any required tool parameter is missing, return to ANALYSIS/read-back to obtain it; do not call the write tool with an incomplete payload.
- For `salesforce_update_opportunity_by_id`, include the resolved Opportunity Id as lowercase `id` and pass changed standard/custom API fields as the tool's top-level field parameters, e.g. `StageName`, `Amount`, or any other writable Opportunity field API name (including `__c` custom fields exposed by the tool).
- For generic Opportunity updates through `salesforce_update_a_record`, include `api_name: "Opportunity"`, the resolved Opportunity record ID, and changed writable fields under `fields`.
- For single-select picklists such as `StageName`, `Type`, or `LeadSource`, pass the exact active picklist value string from metadata.
- For multi-select picklists, pass one semicolon-delimited string using exact active values.
- Do not invent field API names, required fields, record types, or picklist values. Never pass display-only decorations, explanatory suffixes, or UI annotations as field values; use the raw metadata value/fullName only.
- For dependent picklists, validate the controlling field and dependent field as separate API fields. Use the raw active dependent value that metadata allows for the chosen controlling value; do not combine the two values into a rendered label such as `{dependent} ({controller})`.
- For required write fields (standard or `*__c` custom) and picklist values (e.g. `StageName`, `Type`, `LeadSource`), apply the three-layer resolution per Invariant 6:
  - **Layer 1 — explicit:** Scan the user's input / source text against the field's active picklist values (case-insensitive). If a token matches an active value → use it.
  - **Layer 2 — LLM semantic inference:** If no Layer 1 match, reason from the full opportunity context (name, description, account, source text) against the active picklist values. If exactly one value clearly fits with the others clearly not fitting → use it, note the inference in the output.
  - **Layer 3 — fallback:** Required field with no clearly-fitting option → ask via `agent.ask_user_questions`. Non-required field → omit from the payload (let Salesforce apply its default) or use a documented type default. Do not invent values.
- After the Schema-Boundary Write Gate passes, an unexpected 4xx field-level error from the eventual write may be recovered by the system-prompt write failure recovery flow. Do not use this as permission to write with unresolved metadata-backed or validation-backed required fields; those must be resolved or asked before writing.

## §2 — Routing

Evaluate top-to-bottom. First match wins.

| Signal | Operation |
|--------|-----------|
| "create opportunity", "new deal", "open a deal", "track this in pipeline" | Create Opportunity |
| "update deal", "change stage", "push close date", "update amount", "rename opportunity" | Update Opportunity |
| "move to stage", "advance", "qualification", "proposal", "closed won", "closed lost" | Advance / Transition Opportunity |
| "set primary contact", "contact role", "buyer", "champion" | Update Opportunity Contact Role |
| "attach file", "upload proposal", "link file to opportunity" | Attach / Link File |
| "show deal", "opportunity status", "what's happening with" | Read Opportunity |
| "delete opportunity", "remove deal" | Delete Opportunity |

If the user is primarily talking about accounts, contacts, leads, tasks, notes, campaigns, reports, or generic query work, this skill does not apply.

If a meeting references an existing opportunity but the action is to open or track a separate new deal, do not force the flow into `update_existing`.

## §3 — ANALYSIS

### A1 — Extract

| Entity | Rule |
|--------|------|
| `opportunity_id` | Use directly if provided, but never from source-object transport metadata. |
| `opportunity_name` | Candidate lookup string when no ID exists. |
| `account_name` or `account_id` | Required for create. Optional but high-value disambiguator for updates. Never use source-object transport IDs as account IDs. |
| `stage_name` | Validate against live Opportunity metadata. |
| `close_date`, `amount`, `next_step`, `description`, `type`, `lead_source` | Only if the user explicitly requests them. |
| `contact_name`, `contact_email`, `contact_role` | For contact-role operations. |
| `file_name`, `file_id`, `attachment source` | For file-link flows. |

### A2 — Resolve Org Context

Run once:

- `salesforce_get_user_info` → capture `salesforce_domain`, current user, org context.
- `salesforce_get_all_fields_for_object(object_name="Opportunity")` → collect valid stage values and writable standard/custom fields.

### A3 — Resolve Account

| Input | Method |
|-------|--------|
| `account_id` | Trust only after `salesforce_get_s_object_record` confirms it exists. |
| `account_name` | `salesforce_search_accounts(name=..., limit=5)` |
| None on create | Account is critical for create — no silent default. Try inference first (account mentioned elsewhere in source text, opportunity-to-account hint via `salesforce_search_opportunities`); if no clearly-fitting candidate emerges, ask via `agent.ask_user_questions`. |

Single exact match → use it. Multiple matches → try contextual best first (exact name match, account active in current user's recent opportunities, account referenced in same source thread); use it if exactly one clearly fits. Otherwise ask via `agent.ask_user_questions`. Zero matches → stop create and report "Account not found." (Active org lacks the record — explain directly, do not ask.)

### A4 — Resolve Opportunity

| Input | Method |
|-------|--------|
| `opportunity_id` | `salesforce_get_opportunity` or `salesforce_get_s_object_record` |
| `opportunity_name` + optional account | `salesforce_search_opportunities(name=..., account_name=..., is_closed=false, limit=5)` |
| Vague reference | Search by distinctive keywords, then stop unless exactly one record matches |

If multiple open matches remain, ask via `agent.ask_user_questions` or stop without writing. Do not
rank by account, owner, recency, stage, or semantic fit to choose a mutation target. Wrong silent
selection is a silent-success failure that recovery cannot catch.

### A5 — Resolve Contact Role Target

For contact-role operations:
- `salesforce_search_contacts(name=..., email=..., account_name=..., limit=5)`
- Read the chosen contact with `salesforce_get_contact`.

Apply Invariant 6 inference order: explicit email match → unique tool match → single contextually-best fit (same account as the resolved Opportunity, role/title hints from source text). If exactly one contact clearly fits, use it. If multiple candidates remain equally plausible, ask via `agent.ask_user_questions` — silently linking the wrong person to a deal is a silent-success failure that recovery cannot catch.

### A6 — Lock Context

```json
{
  "operation": "create_opportunity | update_opportunity | update_contact_role | attach_file | read | delete",
  "opportunity_id": "006...",
  "account_id": "001...",
  "planned_diffs": {
    "StageName": "Proposal/Price Quote",
    "Amount": 50000
  },
  "org_ctx": {
    "salesforce_domain": "acme.my.salesforce.com"
  }
}
```

## §4 — EXECUTION

### E1 — Write

| Operation | Tool | Notes |
|-----------|------|-------|
| Create Opportunity | `salesforce_create_opportunity` | Requires lowercase `name`, `stage_name`, and `close_date`; include resolved `account_id` when available. |
| Generic Opportunity Create | `salesforce_create_s_object_record` | Use for creates with custom fields, dependent picklists, closed-stage auxiliary fields, or API-name field maps; include `sobject_type: "Opportunity"` and `fields`. |
| Update Opportunity | `salesforce_update_opportunity_by_id` | Include the resolved Opportunity Id as lowercase `id` plus changed fields only. |
| Generic Opportunity Field Update | `salesforce_update_a_record` | Use only for writable Opportunity fields not exposed by `salesforce_update_opportunity_by_id`. Include `api_name: "Opportunity"`, the resolved Opportunity record ID, and changed `fields` only. |
| Update Contact Role | `salesforce_update_opportunity_contact_role` | Use the resolved contact and role only. |
| Upload / Link File | `salesforce_upload_file_attachment` then `salesforce_link_file_to_record` | Only when a file payload/source is available. |
| Delete Opportunity | `salesforce_delete_opportunity` | Destructive; confirm target in output. |

### E2 — Read-back

| Operation | Verification |
|-----------|--------------|
| Create / Update | `salesforce_get_opportunity(opportunity_id="<006...>")` or `salesforce_get_s_object_record(sobject_api_name="Opportunity", record_id="<006...>")` |
| Contact Role Update | Read the Opportunity and summarize the role update result if surfaced by the tool |
| File Link | Read the Opportunity and mention the file/link action outcome |
| Delete | Report tool success and do not claim the record still exists |

## §5 — Output Format

| Outcome | Format |
|---------|--------|
| Created | `✅ Opportunity created: {Name} — {link}` |
| Updated | `✅ Opportunity updated: {Name} — stage {StageName}, amount {Amount}, close {CloseDate} — {link}` |
| Contact role updated | `✅ Opportunity contact role updated for {Name} — {link}` |
| File attached | `📎 File linked to opportunity: {Name} — {link}` |
| Read only | `ℹ️ Opportunity status: {Name} — {StageName} — {link}` |
| Delete | `🗑️ Opportunity deleted: {Name} ({Id})` |

Always report partial failures separately. Never claim a deal moved stages unless the read-back reflects the new stage.

Populate every declared output:

- `response` (string): concise factual operation summary or the reason no write occurred.
- `operation_succeeded` (boolean): true only after Salesforce confirms the requested Opportunity
  create, update, read, contact-role, attachment, or delete operation and any required read-back.
  It is false for failed, skipped, blocked, or ambiguous operations.
- `updated` (boolean): true only for an update-existing request after Salesforce confirms the write
  and read-back reflects the requested fields. It is false for failed/skipped updates and for
  non-update operations such as read, create, or delete.
- `opportunity_info` (string): confirmed Opportunity ID/name/link and read-back values; otherwise an
  empty string.

Downstream nodes normally branch on `operation_succeeded`. For update-existing workflows,
`updated` is an accepted more-specific gate. Never branch on non-empty `response` text.

### Hard stop for update-existing

If ANALYSIS did not resolve one unique Opportunity in the active org, `Update Opportunity` must not write anything.
Return a limitation message instead of creating a new Opportunity.
