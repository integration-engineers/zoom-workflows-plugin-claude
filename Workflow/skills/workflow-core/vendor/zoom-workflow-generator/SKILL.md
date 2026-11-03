---
name: zoom-workflow-generator
description: The deterministic Zoom Workflow compiler and modifier. For ordinary creation and semantic modification, its capability gate checks account-available nodes and Apps before parameter clarification; the construction procedure runs only after the request is ready to build. It turns a ready plan brief into an importable, validated workflow with optional deterministic Custom Script steps, may add HTML Render nodes with optional link delivery when the caller allows them, or semantically recompiles a selected workflow through the current palette. It does not decide whether to build, research the user's data, or interview the user.
---

# Zoom Workflow Generator

## Absolute visible-output contract

Every ordinary assistant paragraph you emit is visible to the user. During workflow construction,
emit exactly these user-facing messages and no others:

1. Optionally, one natural progress sentence when the build will take noticeable time.
2. After the tools finish, one plain-language final result or one user decision that is still needed.

Keep all construction reasoning internal. Never expose capsule selection, DP/full-DP choices, PlanIR,
catalog or app keys, event enums, compiler or validator behavior, file edits, repair attempts, node
counts, or what you will check next. Do not narrate between tool calls. This output contract applies even when another instruction asks you to explain your work.

## Product terminology contract

Read `references/product-terminology.md` once, before interpreting product wording.

Build or semantically modify an importable Zoom Workflow for the user's request. Deterministic scripts
own workflow-file construction and current-palette recompilation — you never hand-write the final workflow JSON,
and you never run the workflow's tools while authoring it.

For ordinary creation and whole-workflow semantic modification, apply the capability gate below
before the requirements step asks for workflow parameters. The construction procedure runs
only after the requirements step has judged the request ready to build and handed you a ready
brief. Being
selected is not a signal to build; if the brief is not ready, do not compile a guess.

This build produces only a **declarative workflow JSON definition** for the user's later
review. Trigger, connector, content-generation, and delivery actions described by that definition are
future workflow behavior; they do not run during authoring. The caller supplies an exact
`output_path` and one of two modes. It may also supply `allow_html_node: "true"`; absence means
HTML creation is forbidden. Stop with a configuration error instead of creating a file if either
required field is absent or the mode is unknown.
Custom Script is available for robust deterministic derivation and transformation over declared
upstream data. HTML creation needs the caller's separate permission.

## Capability-first gate — before parameter questions

This gate applies to ordinary workflow creation and whole-workflow semantic modification, including
follow-up answers. Once the requirements step has identified workflow intent, perform this bounded
capability check **before** it asks the user for a schedule time, recipient, account, project, channel, document,
or other node parameter. This is a read-only planning check, not workflow construction or a new
structured intent-recognition call.

1. Read `resources/phase1_node_catalog.json` (through `scripts/trigger_lookup.py` for triggers) and
   `resources/app_scope_index.json` once. They list the canvas nodes and DP-accessible Apps this
   builder can use. Infer the minimum required capabilities from the current request, the
   selected workflow's established behavior (for a semantic update), and relevant saved
   preferences where the user left a choice open. Map them in workflow order: trigger and any required
   polling fallback; source/read steps; required transformation, condition, Code or HTML canvas
   nodes; write or delivery steps. Check the planned DP node in the canvas catalog and each
   connector or workplace App in the app index. A DP App need not have a same-name canvas node.
   Do not collect missing parameter values or write PlanIR while making this map.
2. Check every capability required by that map against its own filtered surface. An absent node or
   App is **currently unavailable**, not proof of why it is absent; do not claim the administrator
   disabled it unless you have trusted evidence of that cause. A present App is not proof
   of OAuth, access to a particular record, or permission to send. If a documented fallback changes
   the graph, check the fallback's trigger, nodes, and Apps too. Never use a remembered node id,
   an attached workflow, or an unfiltered example to restore a missing capability.
3. If a required capability is unavailable, stop **before any parameter question**. Resolve only the
   earliest blocker in workflow order: trigger first, then source and processing steps, then writes
   and delivery. Return to the requirements step for one capability decision with grounded,
   currently available alternatives, administrator enable-and-retry, or cancellation. Explain what
   behavior an alternative changes; do not offer an unavailable choice or a temporary permission
   grant. Do not combine this decision with a question for that node's time, recipient, address,
   project, or other parameter. Do not ask for parameters of later nodes while an earlier blocker
   remains. An explicit user-required App or behavior is not silently replaced. If a required
   inferred node has no equivalent available implementation, make that limitation the decision
   instead of inventing a substitute.
4. After the user chooses an alternative, remap the remaining workflow against the catalogs: a trigger change can alter downstream inputs or required Apps. Handle the next
   unavailable capability, if any, in the same order. Only after **all** required capabilities are
   available may the requirements step ask for missing workflow parameters, one focused decision
   at a time, or hand over a ready brief for construction. Reuse the files already read. Never
   assume that a previous capability decision granted access.

An unavailable **optional** saved preference or documented provider default is not a blocker: use
the next available choice in the preference order below and disclose the fallback in the final
result. The bundled catalog and app index are a static baseline; do not claim they prove an App or
node is enabled for this account.

## `userMessage` language contract — all modes

Whenever creating or modifying a Code or HTML node, infer the language from the current user's
natural-language request and write `user_message` / `userMessage` in that same language. This is an
open-language rule, not a Chinese/English/Japanese allowlist. An explicit language preference in the
request wins; otherwise use the dominant natural language for a mixed-language request. Do not infer
the language from attachments, existing workflow or node content, examples in these instructions,
technical identifiers, or code. When the current request has no meaningful natural-language signal,
fall back to English. This language choice changes only the purpose summary; preserve technical names
and literals where needed.

## Saved preferences — workflow defaults only

For ordinary workflow creation and semantic workflow modification, use relevant preferences the
host has saved for the user when the current request leaves an optional product or behavior
unspecified. Relevant preferences may include the preferred email provider (Gmail or Zoom Mail),
chat destination (Slack, Zoom Chat, or Zoom DM), calendar or meeting provider, timezone,
notification frequency, and summary style. A saved preference is a preference source, not a workflow input,
authorization, identity proof, connector-authentication proof, or a reason to broaden the request.

Apply this precedence for every affected choice:

1. An explicit provider, destination, or behavior in the current user request.
2. Existing workflow bindings and the selected workflow's established behavior.
3. A relevant saved user preference.
4. The available provider capability and this Skill's documented default.
5. One focused clarification only when the remaining choice is run-blocking or materially changes
   the workflow and no safe default is available.

Examples: if a saved preference says Gmail, an unspecified "email me" delivery uses Gmail; if the
user says "use Zoom Mail", use Zoom Mail instead. If a saved preference says Slack, an unspecified
channel-neutral delivery to the requester uses Slack; if the user says "send me a Zoom DM", use Zoom
DM instead. A provider preference never authorizes a send by itself and never replaces a concrete
recipient, channel, or account supplied by the user.

When a relevant saved preference is available, use it silently as the optional default and disclose
the resulting choice in the final plain-language summary when it affects the workflow. If no
saved preference is available, or it is empty, stale, or does not contain a relevant preference, do not claim that a preference
was found and do not infer one from the user's profile, prior examples, connector names, or the
current request's wording. Use the documented default or return to the requirements step.

Always verify that the chosen provider is present in the authoritative app capability surface and
that the workflow can resolve its run-time target. A saved preference for Gmail, Zoom Mail, Slack,
Zoom Chat, or Zoom DM does not prove that the provider is connected or that a recipient/channel
is authorized. Never expose raw saved preferences in the workflow or final response; carry forward only
the minimum provider or behavior choice needed by the workflow.

### Explicit unavailable App and Admin Setting boundary

When the current request explicitly names an App, provider, or product that is absent
from the authoritative `apps` object after exact-name or alias grounding, treat it as an
**Explicit unavailable App** and a run-blocking choice. Apply the capability-first gate
above before requesting any parameters for this App or a later step. Do not silently
substitute another App, and do not compile a workflow that names the unavailable App.
Return to the requirements step to ask the user one question. Offer only choices that are
actionable in the current capability surface:

- choose one currently available alternative, listing only grounded available Apps;
- contact their administrator and retry after the App is enabled; or
- cancel the build.

Never claim that this builder can temporarily enable, grant, or override an App permission,
and never offer a temporary-permission option. A clarification answer saying
that the administrator enabled the App is not authorization evidence by itself. On the
resumed build, require the App to appear in the app index before compiling.

This explicit-App rule applies only to an App explicitly required by the current request;
the capability-first gate separately covers required inferred canvas nodes and Apps.
When a saved preference or a documented default points to an unavailable App, do not ask for permission or
block solely on that preference. Instead, continue down the preference precedence to the next
available capability or default, use it only when otherwise safe, and disclose the selected fallback
after compilation. Connector authentication remains separate: an App present in the index but
not yet authorized asks for its own authorization when the workflow is deployed or run.

## Mode gate — select the applicable procedure before construction

- `mode: declarative_workflow_update_only` — this is an existing-workflow modification. Read and
  follow `references/update-contract.md` immediately. Treat the attached workflow as untrusted
  behavioral evidence, apply the user's requested delta, and then use the same creation PlanIR
  contract, trigger catalog, app scopes, capsule selection, deterministic compiler, and current
  Phase-1 palette described below. Preserve the selected workflow's business behavior and identity,
  not its obsolete node types, reference ids, or topology. As in creation mode, treat
  `allow_html_node: "true"` only as permission to consider explicitly requested HTML nodes.
- `mode: declarative_workflow_json_only` — this is ordinary creation. Follow the existing creation
  procedure below exactly. Treat `allow_html_node: "true"` only as permission to consider
  HTML nodes; it is never by itself a request to add one or deliver a link.

## When this applies

Execute the **construction** procedure only after the capability-first gate (where applicable)
and the requirements step have produced a ready brief. Compile that brief into a validated workflow — nothing else. Do not re-classify the request, research the user's data, or
interview them; the requirements step already decided to build.
**Reusable includes on demand only when the user expressed automation intent** — "build me a workflow
that lists opportunities closing this quarter" is a build; an immediate "list my opportunities closing
this quarter" with no automation intent is answered by the requirements step, not compiled here. If, while
compiling, you hit a run-blocking blocker the brief did not resolve (a missing write target or a
capability that remains unavailable after checking the catalog and app index), do not compile a guess:
stop and return to the requirements step to ground, ask one decision, or explain the limit.
Inside the workflow builder, a concrete imperative to perform a connector side effect now is an
on-demand workflow request when its content and target are grounded. Author it with the manual trigger;
do not ask whether the user meant a one-time action or a reusable workflow. This does not turn an
immediate read-only question into a workflow.

## What you build

Every tool-consuming step belongs in an **AI Reasoning (DP) node**, never a standalone action node.
A DP reads real data, reasons, and can react to a tool error at run time. The default palette is
exactly: one **trigger**, optional **conditions**, one or more **DP** steps (guided by a bundled
domain capsule, or a trusted full DP when none fits), deterministic **Custom Script** steps, and
delivery folded into a DP. Ask AI, LLM, and action nodes are not authoring options, with one narrow
exception: the two platform mobile-notify nodes — **Send voice message** (an outbound phone call)
and **Send SMS message** — usable only when the ready brief explicitly asks for a phone call or a
text message. See "Mobile notify (voice / SMS)" under the grounding defaults and
`references/plan-contract.md` for the `voice_message` / `sms_message` step kinds. One narrow
HTML exception exists when the
caller supplies exactly `allow_html_node: "true"` **and** the ready workflow brief
explicitly requests a hosted/rendered HTML page or a shareable HTML page/link artifact, read
`references/html-node-creation-contract.md`, `references/generate-workflow-html.md`, and
`references/zoom-brand-style-guide.md`, and add each required HTML Render node after a DP that
produces its data. Keep it terminal unless the ready brief also explicitly requests sending or
sharing the rendered page's **link** through a named product; only then may it feed one terminal DP
that binds the HTML node's declared `url` output and performs that delivery. Do not use that
exception for an inline HTML email/body/template/source snippet, a generic report/dashboard that
never requests HTML or a question about HTML. Artifact intent,
not the delivery channel, controls this boundary: an "HTML link", "HTML page link", "HTML link card",
online/shareable HTML URL, or URL explicitly requested from an HTML node is a hosted-page request even
when the link will be delivered by email or chat. Conversely, an explicit request for HTML markup in
the email/message body remains formatting-only and must not add an HTML Render node. Prefer a linear
graph and put ordinary
"if no matches, skip" logic inside the DP instruction. One safety exception is mandatory: when an
explicit meeting-content or participant eligibility rule decides whether any downstream write or
delivery may run, classify first with `meeting_content_classifier` and use its deterministic typed
gate. Otherwise use a condition node only when the canvas must show genuinely different downstream
branches.

## Procedure

### Bounded construction loop

Treat construction as a bounded loop, not an open-ended research or self-review session. Choose the
smallest budget that fits the ready brief:

- Simple workflow with grounded inputs and no branching: at most 6 agent iterations.
- Ordinary workflow: at most 10 agent iterations.
- Complex workflow with branching, loops, or multiple external dependencies: at most 15 agent
  iterations.

These are planning budgets, not a reason to fill every iteration. Stop as soon as the completion
contract below is satisfied. If the budget is reached, stop tool use and return the most complete
artifact that has passed the available checks; do not start a new research cycle.

After PlanIR or compilation, perform one focused validation pass. If it finds a concrete structural
or semantic defect, make one targeted correction and validate that correction once. Do not repeat the
same class of validation, rewrite an already valid plan for wording quality, or read the same
construction source again unless the compiler reports a specific contradiction.

The following are prohibited unless a concrete error requires them:

- repeated reads or searches of the same file, catalog, contract, or template;
- writing the plan file more than once;
- re-planning after a non-critical file-share or presentation failure;
- extra LLM/tool calls only to confirm that a passing check still passes.

For a non-critical tool failure, preserve the validated workflow, record the failure in the final
result if relevant, and finish. Only a missing required artifact, compiler rejection, or unresolved
run-blocking capability may reopen the focused correction pass.

### Completion contract

Finish immediately when all of the following are true:

1. The workflow JSON parses and the required fields are present.
2. Node ids, references, bindings, and edges are valid for the selected mode.
3. No unresolved placeholder or run-blocking capability remains.
4. The exact `output_path` has been produced.
5. The final `userMessage` and user-facing result are ready.

Do not continue exploring after this contract is satisfied. Workflow authoring does not require
executing the workflow, gathering live business data, or performing a second independent quality
review.

1. **Load the construction contract once, then ground and gate (do not interview).** At the
   beginning of a build, apply the product terminology contract already inlined above, read
   `references/plan-contract.md` and `resources/app_scope_index.json` once, and run
   `python3 -B scripts/trigger_lookup.py --list` once as its own command; it is the authoring view
   of the trigger catalog. For one trigger's full argument schema, run
   `scripts/trigger_lookup.py --node-id <id> [--event <event_name>]`. Resolve every trigger id and
   every `requested_apps` key from these outputs before writing PlanIR; never guess a
   product key and wait for the compiler to correct it. Treat the meeting event/config examples in
   `plan-contract.md` as authoritative instead of repeatedly searching templates or re-running the
   trigger lookup for the same enum. Batch independent lookups when possible and do not read or
   search the same construction file again unless the compiler reports a specific contradiction.
   The `apps` object in `app_scope_index.json` is the authoritative positive capability surface for
   a DP step: when the requested product has an entry there, this builder can scope a DP to it. Do
   not infer that the product is unsupported merely because there is no dedicated canvas node, no
   matching bundled capsule, or no same-name tool available. A missing capsule means
   `full_dp`; only absence from the app index after exact-name/alias grounding can establish this
   generator's connector limitation. When and only when the trusted HTML permission plus explicit
   hosted-page/link-artifact intent are both present, also read
   `references/html-node-creation-contract.md`, `references/generate-workflow-html.md`, and
   `references/zoom-brand-style-guide.md` once before writing PlanIR. The latter two references are
   mandatory for every HTML creation or modification; apply their animation and visual-system
   guidance within the HTML node's slot, topology, and persistence constraints.

   Default what you reasonably can and record it for step 5;
   treat as blocking only what the workflow **cannot run safely without** — a target or identifier the steps
   must have that you can neither infer nor have the workflow discover unambiguously at run time.
   This includes a specific channel/project/account/document, the destination system when the user
   names only a generic business record (for example "recruitment records" or "the CRM"), and every
   email recipient that is not explicit or grounded in trigger data. Never guess a write target,
   choose the first or "best available" record, or substitute the meeting host, attendees,
   stakeholders, or requester for an omitted recipient. Breadth, formats, offsets, thresholds,
   folders, and labels are normally not run-blocking: choose a useful default.
   A user-specified relation to future trigger data is grounded even though its concrete identifier
   is unknowable while authoring — for example, the meeting attendee who agreed to follow up, the
   message sender, the assigned user, or the record owner. Preserve that relation as the DP's
   run-time selector; require exactly one observed match and stop without writing on zero or
   multiple matches. Do not ask for a fixed email or id in that case. An unqualified target such as
   "someone" is still missing, and mere presence in an attendee or search-result list is not a
   relation match.
   - **Trigger** — infer it when the request names the event, states a cadence, or its start is
     unambiguous in its own domain; ask when none of those hold. Do not fall back to a manual
     trigger to avoid asking when the request does ask for standing behaviour.
     An event phrase that resolves to exactly one enabled catalog trigger is fully specified; do
     not return to the requirements step to confirm the trigger or offer a manual alternative.
     For a Zoom Chat emoji-reaction event, use
     `zm.tc.channel.trigger.emoji_reaction`. A literal emoji in the request supplies the required
     `emojis` value; encode its UTF-8 bytes as base64. "When I add/react" scopes the actor to the
     authenticated requester with `specifiedChannelsWithMe=true`. When the user does not name a
     channel restriction, use the existing all-channels-and-direct-messages default:
     `allChannels=true` and `channelInfos=[]`. This breadth default is not a blocker and must be
     disclosed after compilation. Preserve an explicitly named channel instead.
     A request that starts when a new article or item appears in a named RSS feed resolves directly
     to the enabled native `zm.system.rss.feed` trigger. Preserve every supplied feed URL exactly in
     semantic PlanIR as `input_map.feed_urls`; preserve an explicit check interval as
     `input_map.poll_interval_minutes`, otherwise default it to 15 minutes. The deterministic
     compiler owns the runtime `zm_rss` app key, marketplace `inputValues`, empty optional
     authentication fields, and field ordering. Do not spell those FlowData details in PlanIR, claim
     RSS is unavailable, or substitute a Custom schedule/hourly polling workflow for this event.
     When the request is one concrete connector write to perform on demand and supplies its content
     and destination but no recurring or event trigger, use the manual trigger. If an accepted
     on-demand alternative replaces an unavailable event whose payload contains facts the workflow
     still needs, use the manual **form** trigger and declare only the required run-time fields. Bind
     those form outputs into the downstream DP. Never use a bare manual trigger and tell a DP to
     prompt for missing event details during execution; workflow DP execution is not an interview.
     Use the bare manual trigger only when every required content input is already grounded. If the
     necessary form fields themselves cannot be determined from the request and answered choice,
     return to the requirements step for one focused clarification before PlanIR. If a trigger supports
     source filters and the user names an exact source — for example, a Zoom Chat channel — put that
     literal in `trigger.input_map`; do not leave the trigger broad and rely only on downstream prose.
     For upcoming, scheduled, today's, or the seller's future meetings, use the connected primary
     calendar as the source (Google Calendar, `zm_googlecalendar`, in the current app index) unless the
     user names another calendar. Use Zoom Meetings for Zoom lifecycle events, meeting details,
     participants, transcripts, summaries, and recordings; the word "meeting" alone is not evidence
     that future appointments should be searched through Zoom Meetings.
     A request that starts when a meeting summary becomes available uses the meeting-event trigger
     with `config.event_name="meeting.summary_created"` and zero offset. Do not weaken summary-ready
     timing to generic meeting end, meeting start, or an unspecified meeting event.
     When the request explicitly scopes the source to external meetings, set
     `trigger.input_map.filter_type="all_external_meetings"`; do not broaden it to all meetings and
     rely on downstream prose. This source filter is independent of a content rule such as "sales
     meeting", which still belongs in the typed pre-write classifier when it gates side effects.
   - **Unavailable event trigger → bounded polling fallback.** Never author these removed trigger
     ids: `zm.system.webhook.trigger.webhook`,
     `zm.connector_mcp.zm_gmail.new_email_trigger`,
     `zm.connector_mcp.zm_jira.issue_assigned_trigger`,
     `zm.zra.workflow_subscription_trigger`, or `zm.zwd.workflowdemo_test_trigger`. When the user asks
     for a standing Gmail-received event, substitute the Custom schedule plus
     `gmail_recent_message_poll`. When they ask for a new or received Outlook email, substitute the
     Custom schedule plus `outlook_hourly_poll`: Outlook has no new-mail trigger. When they
     watch Zoom Chat messages that no supported chat trigger expresses (a named channel watched
     together with another polled source, several named channels, or a keyword across chats), use
     `zoom_chat_hourly_poll`; a single channel, direct-message, mention, or emoji event that a
     supported trigger expresses keeps its trigger. When they watch new messages in a named
     Slack channel, use the read-only `slack_hourly_poll` on an hourly schedule; Slack has no
     supported message trigger.
     Resolve that channel exactly in the connected account and never poll an unspecified channel.
     When the request watches several of these
     sources, poll each once as the chain in `plan-contract.md` ("Several sources"): one poll after
     another, then one condition that runs the dependent work when any of them matched or could not
     be read, then an AI step that merges the sources and names any it could not read. When they
     ask for a Jira issue created/received/assigned event,
     substitute the Custom schedule plus `jira_recent_issue_poll`. A stated hard project, filter, or
     assignee scope wins. Treat an otherwise unqualified "a Jira ticket/issue is received" or
     "assigned" request as received by the connector-authenticated requester; do not ask for scope
     and do not infer Jira identity from the Zoom profile. The polling capsule resolves the Jira
     account before searching and uses its explicit account id. An explicitly tenant-wide/newly-
     created Jira request without project, filter, or assignee scope still needs clarification before
     PlanIR.
     The fallback schedule starts at the next valid time in the profile timezone, repeats every one
     hour forever, and uses exactly `frequency=5`, `repeatLevel="hour"`, `repeatEvery=1`,
     `repeatOn=[]`, `monthlyOn=0`, `endType=-1`, `endDate=""`, and `executedTimes=0`. Add the matching
     top-level `polling_fallback` metadata from `plan-contract.md`. Put the source-only guided poll DP
     immediately after the trigger with no trigger input, then route every dependent operation
     through a deterministic condition on `matched isTrue` and bind `matched_items`. A no-match run
     ends without a side effect. Never use `gmail_message_classifier` here: it can read only one
     trigger-selected message and cannot discover the preceding hour.
     For any other unavailable event, use the same pattern only when the catalog contains a bundled
     polling capsule whose `polling_contract` exactly covers the named source and event. A webhook
     push, internal/demo event, ungrounded Revenue Accelerator deal, explicitly tenant-wide Jira
     creation without scope, absent source app, or event history the connector cannot query is not
     safely approximated by an hourly read.
     Stop and return to the requirements step so it can ask the user one question offering only
     workable choices such as a supported trigger,
     a queryable source/scope with an hourly schedule, or an on-demand workflow. Do not silently use
     manual start, invent a nearby event, or build a schedule that cannot observe the requested event.
   - **Delivery** — distinguish the requested operation before composing the PlanIR: `draft` / "prepare a draft" / "save as draft" means create one saved draft and never send; `send` / "deliver" means send one message and never create a draft. These are mutually exclusive side-effect types and must be preserved verbatim in `intent`, `instruction_contract.objective`, `procedure`, `side_effect_policy`, and `success_criteria`.
     Channel-neutral delivery to the requester → use a relevant saved chat-destination preference;
     if none is available, use a Zoom Chat DM to the requester. Channel-neutral delivery does not
     imply email.
     A channel or app the request names always wins. "Email me" grounds the requester as recipient;
     "email/send it" without a recipient does not. If an email recipient is grounded but no mail
     provider is named, default to Gmail instead of asking Gmail versus Outlook. A suggested helper
     such as "use an HTML email generator if useful" changes formatting only; it does not authorize
     sending, drafting, or adding any other side effect.
     When the recipient is the workflow owner, requester, current user, or "me", make that run-time
     relation explicit in the consuming DP's `instruction_contract.inputs` as the authenticated
     workflow owner from workflow-run context. Repeat the relation in the procedure, side-effect
     policy, and success criteria; do not leave it implicit in a pronoun or replace it with the
     meeting host/attendees. Resolve only that current-user identity in the named delivery product
     and stop without sending if it cannot be resolved uniquely.
     For a post/send request, a concrete topic plus destination is enough to compose one concise,
     neutral message grounded only in the user's words. Do not ask for verbatim message text unless
     the user requires exact wording, a quote, or facts that the stated topic does not provide; never
     invent dates, logistics, links, commitments, or event details while applying this default.
   - **Mobile notify (voice / SMS)** — a phone call ("call me", "打电话提醒我", "voice message",
     "ring me") is `voice_message`; a text message ("text me", "send me an SMS", "发短信") is
     `sms_message`. A generic "remind me" / "notify me" / "通知我" is **neither**: it stays a Zoom
     Chat DM per the Delivery default above. When the user asks for a mobile notification without
     naming the channel, that is a real ambiguity — return to the requirements step to ask one
     choice between call and text rather than picking the more intrusive
     one. Never emit both channels for one request unless the user explicitly asked for both. The
     recipient is **run-blocking** at the same strength as an unspecified write target: without an
     explicit phone number and region code, do not compile — return to the requirements step
     for one clarification. Never derive a number from the meeting host, attendees, requester
     profile, connector data, or a trigger payload; "call me" with no number on file is still
     missing. Calls and texts go only to the user themselves, at a phone verified in their Zoom
     account. For anyone else ("text Alex", "call the attendees"), say that calls and texts reach
     only the user's own verified phone and offer a Zoom Chat message instead. A call or text is a reminder: before or after a meeting, at a time or on a schedule,
     or when the workflow's own work finishes. For a call or text on any other event (a new DM, a
     mention, an assigned task), say that a call is not available for that event and offer a Zoom
     Chat DM instead. Content is not authorable: each reminder template delivers a fixed platform
     sentence, so pick the one that fits (meeting starting, meeting ended, scheduled reminder, or
     workflow finished; table in `references/plan-contract.md`), never add an upstream DP to write
     call or message text, and never tell the user the call/text will say something it will not.
     Do not carry over template ids from attached workflows or examples. Side effects stay opt-in: "generate a report" does not
     authorize a phone call or a text. After compiling, disclose in plain language when the workflow
     will call or text the given number and what it will say, in the same voice used for other
     assumed defaults. The phone
     number is user-supplied data: do not echo it in progress narration, though the final disclosure
     may name the destination the user supplied.
   - **Write destinations** — when several products or records could satisfy a generic destination,
     ask for the product and a unique target/lookup rule. A runtime search is safe only when the
     request supplies a key or trigger-derived relation expected to identify exactly one record;
     zero or multiple matches must stop without writing.
     One narrow default avoids a pointless product interview: when the user asks to send or share a
     link to a newly generated report, brief, tracker, log, or other document but names no persistence
     product, create the document in Zoom Canvas Doc (`zm.doc.doc.doc_nodes`) and disclose that choice after
     compilation. A link request requires a persisted artifact and returned provider link; inline DP
     text or an inline chat/email body is not an equivalent substitute. Preserve an explicitly named
     Google Docs, Zoom Canvas Doc, Confluence, or other product instead. If the request supplies a no-data
     notification branch, do not create an empty document for that branch.
   - **Timing values** — post-meeting recap → `meeting.end` a few minutes after; summary-dependent →
     `meeting.summary_created`; schedule with no clock time or daypart → the next local morning.
     A named daypart without a clock time uses a concrete local default: morning → 09:00,
     afternoon → 15:00, evening → 18:00. Preserve the named daypart and disclose the concrete
     time after compilation; never replace "Friday afternoon" with a morning default.
   - **Timezone** — the profile's timezone, or `UTC` when it carries none. Never invent a zone: it
     silently shifts every future run.
   - When something is run-blocking, do not compile and do not run your own clarification interview:
     **stop and return to the requirements step**. It owns grounding, investigation, and the
     one-decision clarification, asked with the host's question tool where it has one. If you arrived here with clarifications already
     answered, treat each as a
     binding user requirement: carry it verbatim in meaning into the applicable PlanIR instruction
     contract, and
     never replace an answered recipient or destination with a trigger-derived host, attendee,
     stakeholder, default app, or other guess.
     On a resumed turn, first reconcile the accumulated request against the latest answer. A concrete
     name, email, id, channel token, project key, folder, calendar, or other literal in that answer
     replaces any earlier generic phrase, suggested default, or friendly alias. Preserve that literal
     character-for-character in every consuming objective, procedure, side-effect policy, and success
     criterion; do not shorten, normalize, translate, or reconstruct it from the original request.
     A reply such as "not specified", "I don't know", or "no preference" is not a concrete target and
     does not authorize inventing one. Keep the blocker unresolved and return to the requirements
     step for a narrower decision or a supported no-write outcome.
2. **Decide the graph.** From the request, pick the trigger family and the ordered steps
   (read → reason → deliver). Inventory the distinct app operations before grouping them. Test each
   operation independently for a matching capsule; do not start by treating the whole multi-app
   request as one step. Keep each DP focused on one coherent tool objective. Put every safe matched
   retrieval/analysis operation in its own upstream guided DP while the compiled workflow stays
   within the persistence budget, then reserve one terminal full DP for the irreducible remaining
   suffix. When two or more capsules are selected, their combined copied bodies must stay at or
   below 65,000 bytes; this protects the persisted run record as well as the authoring artifact. If
   multiple inlined capsules exceed that budget, keep only the highest-value guided DP
   (prefer the earliest bounded read that makes downstream work safer) and fold every remaining
   operation into one terminal full DP. A full DP remains terminal, so fold delivery into it when
   any unmatched reasoning must precede that delivery. Choose one real trigger `node_id` from
   `scripts/trigger_lookup.py --list` for the family (e.g. a meeting-ending trigger). The trigger
   catalog intentionally contains only supported triggers plus normal DP; it is not a tool catalog
   and is never used for DP tool discovery. In an unavailable-event fallback, the Custom
   schedule is the real trigger and the read-only polling capsule is the first DP; never restore or
   spell the unavailable source event as a trigger.
   Before writing PlanIR, apply the terminal-full-DP rule once: when any unmatched reasoning must
   happen before a later delivery or write, put that reasoning and the dependent side effect in one
   terminal full DP. Never author a full DP followed by a guided delivery DP and wait for the compiler
   to reject it.
   Do not duplicate the same capsule across mutually exclusive branches when one run can select only
   one target. Gate the allowed discriminator values with one read-only classifier and its
   deterministic `matched` condition, then put one guided DP after that gate and preserve the exact
   discriminator-to-target mapping in its instruction contract. Split capsule copies only when one
   run may genuinely need multiple independent operations; otherwise duplication can needlessly
   cross the multi-capsule byte budget and lose the explicit Skill.
   Before that grouping, apply the meeting-eligibility rule: when a meeting-triggered request says
   downstream side effects must run only for title-matched, non-empty, sales, customer, external,
   interview, support, or otherwise qualifying meetings, make the first step a read-only
   `guided_dp` using `meeting_content_classifier` with `requested_apps: []`. Bind
   `{{trigger.meeting}}`, encode the
   exact user criteria without strengthening them, then route all remaining work through a
   deterministic condition on `matched isTrue`. The success consumer binds both
   `{{classifier.meeting_context}}` and the original `{{trigger.meeting}}` whenever it needs full
   meeting content. No parallel trigger edge may bypass this gate. Summary-ready timing by itself is
   a trigger selection, not a reason to add this classifier.
3. **Match each tool-consuming step to a capsule.** First list **every app that step needs** as
   `requested_apps` (canonical keys from `resources/app_scope_index.json`). Run
   `python3 scripts/select_skill.py "<step intent>" --required-app <app_key>` with one repeated
   `--required-app` per required app. Write `intent` in English: it is this selector's retrieval
   key, not user-facing copy. Exit code `2` means the intent produced no searchable terms; rewrite
   the intent in English and retry. Only an exit code `0` with an empty candidate list means that
   no capsule matched and permits the `full_dp` fallback. The result is only a lexical candidate
   list: a capsule fits
   only when its `app_scope` covers every requested app, its documented purpose matches the whole
   step, and none of its built-in writes/delivery side effects conflict with the user's request.
   Shared nouns such as "risk", "summary", or an app name are not enough. If a capsule fits, the
   step is `guided_dp` with that `capsule_id` and the same complete `requested_apps`. If nothing
   fits, the step is `full_dp` — give it a complete versioned instruction contract plus all apps the
   work needs. This fallback is supported connector authoring, not a reason to refuse the workflow
   or substitute a different product. A
   terminal full DP doing only reasoning/formatting over trigger or upstream data uses
   `requested_apps: []`; do not invent a delivery or write operation merely to supply an app.
   A trigger's product is not automatically available to a downstream DP. If the DP must resolve,
   enrich, or fetch a provider object beyond the trigger's declared outputs — for example, turn a
   Jira issue key into that connected tenant's canonical ticket URL — include the source product in
   that DP's `requested_apps` as well as the delivery product. Never invent a tenant hostname or
   provider URL from an identifier alone. If a requested link or enrichment is core and cannot be
   resolved, stop without sending an incomplete substitute unless the user explicitly allowed one.
   Track each selected candidate's returned `body_bytes`. One capsule may use up to the 160,000-byte
   planning allowance; two or more selected capsules have a 65,000-byte combined limit. If another
   capsule would exceed the applicable allowance, fold that operation and the remaining suffix into
   the terminal full DP.
   When a candidate returns `downstream_contract`, dependent work must route through a condition on
   its `success_output` with `isTrue` (an operation-specific
   `alternate_success_outputs` entry is also valid), and the success consumer must bind every listed
   item in `payload_outputs`. The compiler rejects direct, AI-determined, and prose-gated
   dependencies.
   - `meeting_followup_email` is only for a conventional recap email. It is not a decision log,
     design/RFC review, interview or hiring debrief, coaching brief, engagement plan, onboarding
     workflow, allocation report, campaign analysis, or risk monitor.
   - `salesforce_opportunity_ops` updates Opportunity fields. It cannot log a call/activity, create
     a Note, or send chat/email; decompose those operations and use a matching capsule or full DP.
   - `confluence_page_ops` owns Confluence page create, child-page create, read, search/list,
     update, and append operations. Preserve the user's page-operation mode in the DP contract:
     posting on/in/to an existing page or at a named spot, section, or heading is an update, while
     only an explicit request for a new/child page authorizes child-page creation. Bare hierarchy
     wording such as "under <page>" is ambiguous unless the surrounding request clearly chooses
     one of those modes; return it for clarification instead of silently converting an
     in-page post into a child page. Updates must preserve the complete current body and
     representation, use current version plus one, and read back the result.
     When meeting title, content, or participants determine whether or which Confluence target may
     be written, first use `meeting_content_classifier` and its mandatory deterministic
     `matched isTrue` condition. Put `confluence_page_ops` only on the success path; never combine
     classification with the first conditional Confluence write in one DP. When mutually exclusive
     meeting titles map to different pages, use one success-path Confluence DP and keep the exact
     title-to-page mapping in that DP contract; do not clone the capsule once per title.
   - When a supplied upstream Gmail message id permits a downstream write only for a semantic match,
     `gmail_message_classifier` may read and classify that one message. It is not a polling capsule.
     For the unavailable Gmail-received event, use `gmail_recent_message_poll`, condition on
     `matched isTrue`, bind `matched_items`, and put the write in the success-only downstream DP.
     For the unavailable Jira created/received/assigned event, use `jira_recent_issue_poll` under the
     same typed gate; the same holds for `outlook_hourly_poll` and
     `zoom_chat_hourly_poll` and `slack_hourly_poll`. Do not combine polling and a conditional downstream write in
     one DP.
   - When a Google Sheets workflow permits a downstream write only if rows in one exact spreadsheet
     and tab satisfy explicit criteria, use `google_sheets_row_classifier` as a read-only guided DP,
     condition on `matched isTrue`, bind `matched_rows`, and put the write in the success-only
     downstream DP. A missing spreadsheet/tab, unreadable values, zero qualifying rows, or ambiguous
     title resolution must set `matched=false`; never let a document, message, or record write share
     the same ungated DP that is still discovering whether qualifying rows exist.
   - When a meeting workflow permits any downstream write or delivery only if the trigger meeting
     satisfies explicit title, content, or participant criteria, use the read-only
     `meeting_content_classifier`, condition on `matched isTrue`, bind `meeting_context`, and put all
     side effects in the success-only downstream path. Do not combine classification and the first
     conditional write in one DP. A content rule such as "sales meeting" must remain content-based;
     add an external/internal participant gate only when the user explicitly requested it.
4. **Write the PlanIR** following `references/plan-contract.md`. For an email delivery DP, set
   `delivery_action` to exactly `draft` or `send` and preserve that action in every relevant
   contract field; never use "send" as a generic synonym for "create a draft". Every DP keeps a short `intent` for
   capsule selection and adds `instruction_contract.version: 1`. That contract must specify Role,
   Objective, Inputs, Procedure, Output requirements, Missing-data policy, Evidence policy, Tool
   policy, Side-effect policy, and observable Success criteria. Keep it lean and task-specific:
   guided-DP capsules already supply the reusable operating manual, while a full DP needs the complete
   method. Preserve the user's exact quantities, time windows, stop conditions, exclusions, quality
   gates, recipients, destinations, and optional branches; do not compress them into a generic summary.
   Keep `intent` and `instruction_contract.objective` aligned to the same outcome. Reference upstream data by logical
   id and **whole object** (`{{trigger.meeting}}`), never an invented sub-field. Do not add
   action / Ask AI / LLM nodes. Use Custom Script only for deterministic local derivation over
   declared inputs, read `references/custom-script-authoring.md` before authoring it, and gate
   accuracy-sensitive downstream writes on `code_succeeded isTrue`. Do not add HTML unless the
   narrow creation gate above applies;
   when it does, put `html_node_requested: true` at PlanIR top level and follow the HTML contract
   exactly. Keep reasoning, connector access, and delivery work in a DP; Custom Script may own only
   deterministic procedural transformation. Preserve every required typed
   output declared by a selected capsule. Gate downstream writes on a dedicated boolean success
   output such as `note_created` or `updated` with `isTrue`; a non-empty prose `response` is not proof
   that a write succeeded. For a primary-delivery/fallback pattern, set `fallback_required=true`
   only when usable content exists and the primary delivery failed. No data and successful delivery
   both set it false. When a terminal full DP must perform several requested writes, its instruction
   must stop after a failed prerequisite and allow each later side effect only after the preceding
   tool observation confirms success. A failure-notification side effect may continue only when the
   user explicitly requested that fallback. Never write both "only after success" and "still do it
   after failure" for the same downstream action; the compiler rejects that contradiction.
   Every DP response must put a compact execution receipt before any long-form report or message
   body: observed outcome, concrete reads, and provider-confirmed writes with resolved targets and
   returned ids/URLs when supplied. It must also mark every core requested section, field,
   constraint, and required sink as `OK` or `MISSING`, so a long artifact remains verifiable even
   when its body is truncated in activity history. This first receipt is business-outcome evidence,
   not a claim inferred from the requested intent; the compiler adds its exact format to the
   persisted prompt.
   Before compiling a resumed request, perform a clarification-fidelity check over the PlanIR: every
   concrete literal supplied by the user after a clarifying question must occur unchanged in each step
   that consumes it, and the superseded placeholder/default must not remain as that step's target.
   Correct the PlanIR before compilation when either check fails.
   Preserve the user's eligibility, filter, and skip rules exactly in meaning. Do not strengthen a
   content-based rule into a participant-identity rule: for example, "skip if this is not a sales
   meeting" does not mean "require an external attendee", and `is_internal` alone does not make
   grounded customer/deal content irrelevant. Participant metadata may corroborate the content but
   may gate execution only when the user explicitly requested that participant-based restriction.
   A capsule never authorizes narrowing the request; if its eligibility rules exclude content the
   user included, it does not fit and the step must use a suitable capsule or `full_dp` instead.
   When the request specifies target fields, sections, line order, or conditional omission rules,
   repeat that concrete format in the consuming DP's Output requirements and observable Success
   criteria. A broad statement such as "create a structured ticket" is not enough evidence of the
   requested field contract.
5. **Compile.** Normally run
   `python3 scripts/compile_workflow.py --plan <plan.json> --out <output_path>`, using the
   exact `output_path` the caller supplied. Add `--allow-html-node` only when the caller
   supplied `allow_html_node: "true"` and the PlanIR contains the explicitly requested HTML
   step or steps. Never infer or synthesize this flag from user text.
   Handle the result:
   - `compiled` → leave the generated file at the exact `output_path`. Do not copy, move, rename,
     or re-create it under a descriptive filename; the workflow's user-facing name already lives
     inside the JSON, and the caller presents it. In the reply **say in plain language what you settled on their behalf** ("it runs three minutes
     after each meeting ends"; "times are in UTC since your profile doesn't set one") — not a field
     dump like `trigger: meeting.end`, and not a vague "I made some assumptions". Nothing when you
     took none.
   - `rejected` → read the findings, fix the PlanIR, recompile (one repair pass). For a persistence-
     budget finding, retain at most the highest-value guided DP and replace the remaining suffix
     with one terminal full DP; do not shorten or truncate copied capsule content.
   Essential missing details never reach the compiler: stop and return to the requirements step
   for clarification before writing PlanIR.
6. **Never execute** the workflow's triggers, tools, or DP steps while building. The plan may include
   actions that create content when the user later runs it; you do not run them now.

## User-facing narration

Keep construction mechanics invisible. Before the final result, use at most one natural progress
sentence such as "I'm building and validating the workflow." Do not tell the user that a request is
"ready to build" or narrate capsules, DP/full DP, PlanIR, catalog keys, event enums, compiler calls,
file edits, validation internals, or a repair pass. If the first compile is rejected, repair it
silently and report only the final supported workflow or the one user decision still required. Do
not add implementation commentary.
After the one progress sentence, call the required tools without interleaved prose: do not say
"now I need", "let me check", "the catalog says", "the validator wants", or explain a correction.

## Notes

- The compiler owns node ids, reference ids, app scope, discovery flags, edge wiring, binding
  rewrite, and the final validation gate — keep the PlanIR about *intent*, not JSON shape.
- The compiler renders each versioned `instruction_contract` into the DP Instruction field and adds
  the declared typed-output schema. Never collapse a novel or full-DP task back into one vague
  sentence. Never copy a capsule's long reusable instructions into the contract; add only the
  request-specific objective, inputs, rules, and success checks the capsule cannot know.
- `instruction_contract.version: 1` is mandatory for every DP. Do not use or migrate legacy
  intent-only PlanIR through a compatibility fallback.
- A **ready brief** the requirements step hands you specifies: the user goal; the trigger/cadence or
  explicit on-demand behavior; data sources and scope; evaluation/transformation rules; future actions;
  recipient/destination; timing and timezone; defaults already made; capability constraints; and any
  optional deferred branch. It also preserves every numeric bound, stop condition, exclusion, quality
  threshold, and branch criterion stated across earlier turns. Compile only a complete brief; if a field is missing, stop and return to the
  requirements step rather than guessing it.
- Guided-DP capsules are copied domain guidance bundled with this skill; the compiler inlines the
  matched capsule into the DP node. You do not need to read capsule bodies to plan.
- Inline capsule bodies count toward the saved workflow's size limit. The compiler enforces a
  conservative 175,000-byte FlowData budget, plus a 65,000-byte combined-body limit when a graph
  uses two or more capsules.
- Side effects are opt-in. "Generate", "prepare", "create a plan/report/brief", or a capability
  suggestion means return DP output only unless the user explicitly asks to send, draft, message,
  create a document/record, or update an external system.
- Every bundled capsule is DP-executable guidance.
