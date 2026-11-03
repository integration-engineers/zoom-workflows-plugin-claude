# PlanIR contract

You author a small **PlanIR** (JSON); the deterministic compiler (`scripts/compile_workflow.py`)
owns all FlowData shape, app scope, discovery flags, edge wiring, binding rewrite, and validation.
**Never hand-write FlowData.** The default palette emits exactly five node kinds: `trigger`,
`condition`, `guided_dp`, `full_dp`, and `custom_script`. A creation or semantic-update turn with the trusted
`allow_html_node: "true"` argument may add one `html` step when the ready brief explicitly
requests a hosted/rendered HTML page or shareable HTML page/link artifact; that step may feed one
terminal link-delivery DP only when the brief also requests sending or sharing the page link. Read
`html-node-creation-contract.md` before doing so. Two more step kinds, `voice_message` and
`sms_message`, add a platform mobile-notify node (an outbound phone call or a text) only when the
ready brief explicitly asks for one; see their contract below.

```json
{
  "name": "Auto Follow-up Email",
  "description": "optional one-line",
  "trigger": {
    "node_id": "<catalog trigger node_id>",
    "input_map": { "<required trigger setting>": "<value from the request>" },
    "config": { }
  },
  "steps": [
    {
      "id": "s1",
      "kind": "guided_dp",
      "intent": "Summarize the meeting and send the recap by Gmail.",
      "delivery_action": "send",
      "instruction_contract": {
        "version": 1,
        "role": "Evidence-grounded meeting follow-up assistant",
        "objective": "Create and send the requested concise follow-up from the completed meeting.",
        "inputs": [
          {
            "name": "meeting",
            "source": "{{trigger.meeting}}",
            "purpose": "Sole source for meeting facts, decisions, and action items"
          }
        ],
        "procedure": [
          "Extract only supported decisions and action items.",
          "Compose the requested recap and send it once to the grounded recipient."
        ],
        "outputs": ["Return the sent recap and provider-confirmed delivery status."],
        "missing_data_policy": "Mark unavailable facts as not stated; never invent them.",
        "evidence_policy": "Use the bound meeting as evidence and separate facts from interpretation.",
        "tool_policy": "Use only the selected Gmail capability required by this step.",
        "side_effect_policy": "Send exactly one email to the grounded recipient and report success only after provider confirmation.",
        "success_criteria": [
          "Every claimed fact is supported by the meeting.",
          "The delivery output reflects the observed provider result."
        ]
      },
      "capsule_id": "meeting_followup_email",
      "requested_apps": ["zm_gmail"],
      "outputs": [
        {
          "name": "response",
          "type": "string",
          "description": "Plain-language recap and delivery result"
        }
      ]
    },
    {
      "id": "s2",
      "kind": "full_dp",
      "intent": "Post the successful recap to the requested Slack destination.",
      "instruction_contract": {
        "version": 1,
        "role": "Slack delivery assistant",
        "objective": "Post the upstream recap once to the exact requested Slack destination.",
        "inputs": [
          {
            "name": "recap",
            "source": "{{s1.response}}",
            "purpose": "Complete message content to deliver without factual expansion"
          }
        ],
        "procedure": ["Resolve the exact destination, then post the recap once."],
        "outputs": ["Return the observed Slack delivery result."],
        "missing_data_policy": "Stop without posting if the destination is not uniquely resolved.",
        "evidence_policy": "Do not add claims that are absent from the upstream recap.",
        "tool_policy": "Use only Slack capabilities for this delivery.",
        "side_effect_policy": "Post once only after the destination is uniquely resolved.",
        "success_criteria": ["Report success only after the Slack tool confirms the post."]
      },
      "requested_apps": ["zm_slack"]
    },
    {
      "id": "c1",
      "kind": "condition",
      "determined_by_ai": false,
      "routes": [
        {
          "name": "Has results",
          "conditions": [
            { "key": "{{s1.response}}", "condition": "isNotEmpty", "value": "" }
          ]
        }
      ]
    }
  ],
  "edges": [
    ["trigger", "s1"],
    ["s1", "c1"],
    ["c1", "s2", "Has results"]
  ]
}
```

## Rules

## Bounded validation and completion

The generator uses one focused validation pass after PlanIR/compilation. A concrete structural or
semantic defect permits one targeted correction and one follow-up validation. Once the workflow parses,
required fields and bindings are valid, no placeholders or run-blocking capabilities remain, and the
output file is written, the agent must stop.

Do not repeat a passing validation, re-read the same construction source, rewrite a valid plan for
wording quality, or reopen planning because a non-critical presentation/share operation failed. A
non-critical failure is reported and the validated artifact is preserved. Only compiler rejection,
missing required output, or an unresolved run-blocking capability can reopen the single correction
pass.

- **Trigger.** Pick one real `node_id` from `scripts/trigger_lookup.py --list` for the request's trigger family
  (meeting → `zm.meeting.meeting.meeting_event`; grounded on demand →
  `zm.system.manual.trigger_manually`; on-demand run-time input →
  `zm.system.manual.trigger_form`; schedule → `zm.system.scheduler.trigger.scheduler`). Put request-specific trigger settings in
  `trigger.input_map`; the compiler fills only schema-required defaults and copies the catalog
  `output_schema`, so `{{trigger.<field>}}` resolves against declared outputs.
  A concrete on-demand connector write with grounded content and destination and no event/cadence uses
  the bare manual trigger. An accepted on-demand alternative for an unavailable event uses the manual
  form trigger whenever downstream behavior needs facts that the missing event would have supplied.
  Declare the smallest required form field set, bind `{{trigger.<field>}}` into the downstream DP, and
  let the form collect those values when the user runs the workflow. Never author a bare manual trigger
  whose DP instruction says to ask or prompt for missing run-time details. If the form fields cannot be
  enumerated from the ready brief, clarify before PlanIR. When the selected trigger exposes a source
  filter and the request names an exact source, populate that filter rather than emitting the schema
  default; for example, a named Zoom Chat source channel becomes
  `"filterParam": [{"channelName": "<exact literal>"}]`. Keep the destination separate from the trigger source.
  For future appointments described as upcoming, scheduled, today's, or the seller's meetings, read
  the connected primary calendar (`zm_googlecalendar` in the current index) unless the user names a
  different calendar. Use Zoom Meetings as a source for Zoom lifecycle events, meeting details,
  participants, transcripts, summaries, and recordings, not as the default future-calendar store.
  An explicit external-meeting scope uses
  `trigger.input_map.filter_type="all_external_meetings"`. This is a supported trigger source filter;
  never broaden it to `all_meetings` and hope a downstream write-capable DP filters it later.
  - **A meeting trigger must carry its event in `trigger.config`** — the request's timing is business
    meaning, not a canvas detail, and the catalog declares no default for it. Use the shape the shipped
    templates use: `{"event_name": "<event>", "event_config": {"<field>": <number>}}`. Use
    `time_offset` for `meeting.start`, `meeting.end`, and `meeting.summary_created`; it is minutes
    relative to the event and carries real intent (a pre-meeting briefing uses `meeting.start` with
    `-15`; a post-meeting recap uses `meeting.end` with `3`; summary-ready flows use `0`). Use `time`
    for `meeting.participant_joined_late` and `meeting.participant_left_early`; it is the late/early
    threshold in minutes.
    A request that explicitly starts when its summary becomes available must use
    `event_name="meeting.summary_created"` with `time_offset=0`; `meeting.end` does not guarantee that
    the summary exists yet.
  - For a schedule, always provide the concrete `startsOn`, `frequency`, `repeatLevel`, `repeatEvery`,
    `repeatOn`, `monthlyOn`, `endType`, `endDate`, `executedTimes`, and IANA `timezone` values implied by
    the request. Never leave a scheduled trigger empty or invent a past `startsOn` value.
    The current schedule trigger declares no runtime output fields: it controls execution order only.
    Never invent or bind fields such as `{{trigger.scheduled_time}}` or `{{trigger.current_time}}`.
    When a downstream DP needs no declared trigger payload, use `instruction_contract.inputs: []`
    and let its execution contract use the supported workflow-run context.
  - Daily: `frequency=0`, `repeatLevel="day"`, `repeatEvery=1`, `repeatOn=[]`.
  - One weekday weekly: `frequency=1`, `repeatLevel="week"`, `repeatEvery=1`, and `repeatOn` uses
    `1=Sunday, 2=Monday, …, 7=Saturday`.
  - Every weekday: `frequency=2`, `repeatLevel="week"`, `repeatEvery=1`, `repeatOn=[]`.
  - For an unbounded recurring schedule: `monthlyOn=0`, `endType=-1`, `endDate=""`,
    `executedTimes=0`. `startsOn` is the next occurrence in `YYYY-MM-DD HH:mm:ss`.
  - **RSS feed.** "When a new article/item appears in this RSS feed" uses the native
    `zm.system.rss.feed` trigger, never Custom schedule. Give the compiler semantic PlanIR only:
    ```json
    {
      "trigger": {
        "node_id": "zm.system.rss.feed",
        "input_map": {
          "feed_urls": ["<exact http-or-https feed URL>"],
          "poll_interval_minutes": 15
        }
      }
    }
    ```
    Preserve all supplied feed URLs in order and preserve an explicit positive interval; otherwise
    use 15 minutes. Do not author `appKey`, `inputValues`, `difftype`, credentials, `fedUrl`, or
    `timerValue`: the compiler deterministically emits that runtime shape.
  - **Unavailable event polling.** The webhook, Gmail-received, Jira-assigned, Revenue Accelerator
    deal-closed, and Workflowdemo test trigger ids are not authoring options. An unavailable event
    may become a schedule only when a bundled read-only polling capsule can query the exact source
    and event semantics:
    - a new or received Gmail email: `gmail_recent_message_poll`;
    - a new or received Outlook email: `outlook_hourly_poll` (Outlook has no new-mail
      trigger);
    - a created, received, or assigned Jira issue: `jira_recent_issue_poll`;
    - new messages in one named Slack channel: `slack_hourly_poll` (Slack has no
      supported channel-message trigger). The poll resolves that channel with the
      connected account's read-only channel list, reads its prior-hour history, and
      reports no match for an unreadable or ambiguous channel; it never posts.
    - Zoom Chat messages that no supported Zoom Chat trigger expresses: a named channel watched
      together with another polled source, several named channels, or a keyword or phrase across
      chats: `zoom_chat_hourly_poll`. A single channel-message, direct-message, mention, or
      emoji-reaction event that a supported trigger expresses keeps that trigger. The poll needs a
      named channel or an explicit keyword; with neither, ask which channel to watch.

    For one source, use this exact trigger shape
    (with a concrete future `startsOn` and the profile IANA timezone) and top-level marker:
    ```json
    {
      "polling_fallback": {
        "poll_step_id": "s1",
        "source_app": "zm_gmail",
        "window_minutes": 60
      },
      "trigger": {
        "node_id": "zm.system.scheduler.trigger.scheduler",
        "input_map": {
          "startsOn": "<next valid YYYY-MM-DD HH:mm:ss>",
          "frequency": 5,
          "repeatLevel": "hour",
          "repeatEvery": 1,
          "repeatOn": [],
          "monthlyOn": 0,
          "endType": -1,
          "endDate": "",
          "executedTimes": 0,
          "timezone": "<profile IANA timezone or UTC>"
        },
        "config": {}
      }
    }
    ```
    `s1` must be the first step and a `guided_dp` using the source's polling capsule with exactly
    that one `requested_apps` entry. Its versioned instruction contract has `inputs: []`, preserves
    the user's event/filter semantics, and is read-only. Every dependent step routes through a
    deterministic condition on `{{s1.matched}}` with `isTrue` and binds
    `{{s1.matched_items}}`; no match ends quietly. For Jira, "my" or "assigned to me" grounds the
    connector-authenticated Jira requester. The capsule must resolve that account first and use its
    explicit Jira account id rather than inferring identity from the Zoom profile. An unqualified "a
    Jira ticket/issue is received" or "assigned" request also defaults to that requester and must not
    ask for scope; a stated project, filter, or assignee still wins. Only an explicitly
    tenant-wide/newly-created issue request without a hard
    scope returns to the requirements step for one clarification. If no exact polling capsule or
    queryable scope exists, ask rather than inventing a trigger, silently using manual start, or
    approximating a push-only/internal event.

    **Several sources.** When the request watches more than one of these sources ("when new mail
    arrives in Gmail or Outlook", "new messages in Outlook and in #support"), poll each source once,
    in the order the request names them, as one chain: the schedule connects only to the first
    poll, each poll connects only to the next, and the last poll connects only to one deterministic
    condition. That condition's success route tests every poll's `matched` with `isTrue`, and every
    item but the last carries `"join": "or"`, so the dependent work runs when any source found
    something. `polling_fallback` becomes a list with one entry per poll, in step order, each with
    its own `source_app`; two polls never watch the same app. Every dependent step sits on that
    success route and binds every poll's `matched_items`. No poll reads another poll's output.
    The step on that success route is a `guided_dp` or `full_dp` that merges the sources, never a
    Custom Script: the compiler adds each poll's `read_succeeded` output, extends the condition so it
    also opens when a source could not be read, and tells that step to name any source it could not
    read and to send nothing when no source found anything. Leave those additions to the compiler.
    ```json
    {
      "polling_fallback": [
        {"poll_step_id": "s1", "source_app": "zm_gmail", "window_minutes": 60},
        {"poll_step_id": "s2", "source_app": "zm_outlook", "window_minutes": 60}
      ],
      "steps": [
        {"id": "s1", "kind": "guided_dp", "capsule_id": "gmail_recent_message_poll",
         "requested_apps": ["zm_gmail"], "instruction_contract": {"version": 1, "inputs": [], "...": "..."}},
        {"id": "s2", "kind": "guided_dp", "capsule_id": "outlook_hourly_poll",
         "requested_apps": ["zm_outlook"], "instruction_contract": {"version": 1, "inputs": [], "...": "..."}},
        {"id": "c1", "kind": "condition", "determined_by_ai": false, "routes": [
          {"name": "New messages", "conditions": [
            {"key": "{{s1.matched}}", "condition": "isTrue", "value": "", "join": "or"},
            {"key": "{{s2.matched}}", "condition": "isTrue", "value": ""}]}]},
        {"id": "s3", "kind": "full_dp", "...": "binds {{s1.matched_items}} and {{s2.matched_items}}"}
      ],
      "edges": [["trigger", "s1"], ["s1", "s2"], ["s2", "c1"], ["c1", "s3", "New messages"]]
    }
    ```
- **Bindings.** Reference upstream data by **logical id** (`trigger`, `s1`, …) and a field declared
  in that producer's `output_schema`. Bind a declared object as a whole (`{{trigger.meeting}}`) or a
  declared scalar directly (`{{trigger.key}}`); never invent a nested path such as
  `{{trigger.meeting.summary_content}}`. The compiler rewrites logical ids to the emitted
  `reference_id`s and rejects undeclared or nested output paths. When behavior depends on a nested
  property, bind the whole object to a DP and make the DP inspect that property. Keep ordinary
  no-data/skip logic in that DP instead of building a condition over a nested path.
  Exception: when an explicit meeting-content or participant eligibility rule gates downstream
  writes, bind the whole meeting to `meeting_content_classifier`, then gate the success path on its
  typed `matched` output as described below.
- **Execution instruction contract.** Keep `intent` as one short operation summary for capsule
  selection and compatibility, and add `instruction_contract.version: 1` to every DP step. The
  compiler validates and renders this object into the persisted DP `task_prompt`; never put this
  structure in FlowData yourself. `intent` is a lexical retrieval key for `scripts/select_skill.py`
  and is never shown to the user. Write it in English regardless of the request's language.
  `objective`, `procedure`, `success_criteria`, and `userMessage` are unaffected and continue to
  follow their own language rules, including preserving user-supplied literals verbatim.
  - `delivery_action`: optional for mail-delivery DPs and must be exactly `draft` or `send`. `draft`
    means create one saved draft and never send; `send` means send one email and never create a
    draft. Preserve the selected action unchanged in the intent, objective, procedure,
    side-effect policy, and success criteria. The compiler rejects contradictory action wording.
  - `role`: the function this DP serves, not a broad persona.
  - `objective`: one outcome this step must accomplish.
  - `inputs`: an array of `{name, source, purpose}` objects. Use logical whole-object bindings in
    `source`; use `[]` only when the step genuinely has no upstream payload and works from the
    workflow-run context plus selected apps.
  - `procedure`: a short ordered array of task-specific operations. Do not restate a guided
    capsule's reusable manual.
  - `outputs`: a short array defining the user-visible format or result requirements. Typed output
    names, types, and descriptions remain in the step-level `outputs`; the compiler renders that
    schema into the same instruction so prose and machine contract stay aligned.
  - `missing_data_policy`, `evidence_policy`, `tool_policy`, and `side_effect_policy`: one concise,
    explicit rule each. Never guess missing facts, broaden evidence, or authorize an unrequested
    write merely to fill these fields.
  - `success_criteria`: a short array of observable completion checks. A write succeeds only after
    its tool result confirms it.
  Use exactly these fields for version 1; the compiler rejects unknown contract and input fields so
  a misspelled requirement is never silently discarded. Keep `intent` and `objective` aligned to the
  same outcome. Preserve every exact quantity, time window, stop condition, exclusion, quality gate,
  recipient, destination, and branch criterion stated by the user across turns.
  The compiler rejects every DP step without `instruction_contract`; version 1 is the only supported
  authoring contract. Do not compile or migrate legacy intent-only PlanIR implicitly.
- **Intent fidelity.** Preserve the request's eligibility, filter, and skip conditions without adding
  stricter gates. A domain/content rule such as "sales meeting" or "deal-risk content" is not an
  external-attendee requirement: participant metadata such as `is_internal` may support contextual
  reasoning but must not by itself exclude otherwise grounded customer, account, Opportunity, or deal
  evidence. Add a participant-based restriction only when the user explicitly requested it. If a
  capsule would narrow the user's included scope, that capsule does not fit; choose another capsule or
  use `full_dp`.
- **`guided_dp`.** For a tool-consuming step that matches a capsule (`scripts/select_skill.py`).
  Set `capsule_id` and the complete `requested_apps` for that step (use `[]` only for a genuinely
  tool-free capsule). The compiler rejects a capsule whose app scope does not cover every requested
  app, inlines the copied capsule (`md_content`), pins the capsule's app scope, and enables run-time
  tool discovery. A candidate also does not fit when its prescribed side effects conflict with the
  user's request or its cataloged incompatible-intent phrases match the step. This is the default
  for tool-consuming work. Never use the first or "best available" record as a write target: a
  supplied identifier, exactly one search match, or exactly one match for a user-specified relation
  to future trigger data is required. For a relation such as the meeting attendee who agreed to
  follow up, preserve the relation in the DP contract and resolve it from observed run-time data;
  do not require a fixed email while authoring, infer the match from list membership alone, or write
  when zero or multiple records match. When the selected candidate exposes
  a `downstream_contract`, any dependent step must sit behind a deterministic condition on
  `success_output isTrue` (or one of its operation-specific `alternate_success_outputs`) and bind
  every field in `payload_outputs`; direct edges, AI-determined routes, and prose-based success
  checks are invalid.
  Incoming-Gmail automations with semantic match criteria and a conditional downstream write use
  the read-only `gmail_message_classifier` capsule, branch on `matched isTrue`, bind
  `message_details`, and place the write in the success-only consumer. Classification and the
  conditional write must not share one full DP.
  Google Sheets automations with an exact spreadsheet/tab and a row-dependent downstream write use
  the read-only `google_sheets_row_classifier` capsule, branch on `matched isTrue`, bind
  `matched_rows`, and place the write in the success-only consumer. Missing or ambiguous spreadsheet
  identity, a missing tab, unreadable values, and zero qualifying rows all produce `matched=false`;
  they never authorize a write from plausible or inferred rows.
  Meeting-triggered automations whose downstream writes depend on explicit meeting-title,
  meeting-content, or participant eligibility use
  the read-only `meeting_content_classifier` as the first step. Bind `{{trigger.meeting}}`, set
  `requested_apps: []`, preserve the exact title/content/participant criteria in its instruction contract,
  branch on `matched isTrue`, and bind `meeting_context` into the success consumer. Bind the original
  meeting object there too when full content is needed. The trigger must have no parallel path that
  bypasses this gate. Summary availability alone selects `meeting.summary_created`; it does not by
  itself require a classification DP.
  Confluence page operations use the `confluence_page_ops` capsule. Preserve whether the request
  means an in-page update or a new child page: posting on/in/to an existing page or at a named spot,
  section, or heading is an update; only an explicit new/child-page request authorizes child-page
  creation. Bare "under <page>" hierarchy wording is ambiguous without surrounding mode evidence and
  must return to the requirements step for clarification rather than defaulting to create. An update reads the
  exact page immediately before writing, preserves its complete body and representation, increments
  the current version by one, performs one update, and reads the page back.
  When meeting title, content, or participants determine whether or which Confluence target may be
  written, `meeting_content_classifier` must run first and feed its mandatory deterministic
  `matched isTrue` condition. Place `confluence_page_ops` only on that success path; classification
  and the first conditional Confluence write never share one DP. When mutually exclusive meeting
  titles map to different pages, use one success-path Confluence DP and keep the exact title-to-page
  mapping in its instruction contract; do not clone the capsule once per title.
- **Decompose before full DP.** Test each distinct app operation for a capsule independently. Emit
  safe matched retrieval/analysis work as upstream guided DPs and pass their typed outputs forward.
  Use a terminal full DP only for the remaining suffix that no capsule can own; do not collapse the
  whole multi-app request first and thereby hide valid capsule matches. This is subject to the
  compiler's 175,000-byte persistence budget: copied capsule bodies are intentionally
  self-contained. If the compiled graph is
  oversized, keep only the highest-value guided DP (prefer the earliest bounded read) and fold all
  remaining operations into one terminal full DP. `select_skill.py` returns each candidate's
  `body_bytes`; keep the selected-body sum at or below 160,000 bytes to reserve approximately 15,000
  bytes for graph structure. In addition, when the graph selects two or more capsules, their
  combined copied bodies must not exceed 65,000 bytes. The compiler remains authoritative. Never
  truncate a capsule body to make it fit.
  Do not duplicate the same capsule across mutually exclusive branches when one run can select only
  one target. Gate the allowed discriminator values with one read-only classifier and its
  deterministic `matched` condition, then use one guided DP whose instruction contract retains the
  exact discriminator-to-target mapping. Split capsule copies only when one run may genuinely need
  multiple independent operations; otherwise duplication can cross the multi-capsule byte budget
  and lose the explicit Skill.
- **`full_dp`.** When no capsule fits: set `requested_apps` to the canonical `app_key`s the DP will
  need (from `resources/app_scope_index.json`) and write a complete `instruction_contract` with
  exact tool guidance. An app listed in the index is supported as a full-DP scope even when the
  generator has no matching capsule or dedicated canvas node; do not refuse or substitute another
  product for that reason.
  Trigger provenance does not grant the DP that trigger's product tools. Include the source app when
  the DP must resolve or enrich a trigger identifier beyond its declared outputs. For example, a
  Jira-assignment notification that must contain a canonical ticket link needs both `zm_jira` and
  the delivery app; the issue key alone never authorizes inventing a Jira tenant hostname. When a
  requested link is core, fail without sending an incomplete notification if it cannot be resolved.
  For pure reasoning/formatting over trigger or upstream data, set `requested_apps: []`; the empty
  explicit scope blocks tools, and no delivery/write may be invented just to supply an app. Trusted;
  keep it terminal, except that a deterministic Custom Script or narrowly authorized terminal
  HTML renderers may consume its declared output. When it performs several requested writes,
  require tool-confirmed success for each prerequisite before the next side effect. Continue with a
  failure-notification write only when the user explicitly requested that fallback, and never say
  the same downstream action is both success-only and allowed after failure; contradictory policies
  are rejected.
- **Every product needs a step that actually holds its tools.** A `guided_dp` takes its app scope from
  its capsule, so it can only touch that capsule's apps. If the request names a product that no capsule
  covers — Zoom Chat, Slack, and Google Sheets have none — give that product its **own
  `full_dp`** with the app in `requested_apps`. Never borrow an unrelated capsule for it, and never fold
  its action into another step's `intent`: a Jira-capsule step told to "also send a Zoom Chat direct
  message" is instructed to do something it has no tool for, and it will fail at run time. One request
  therefore often needs one step per product: e.g. read-and-reason in a capsule step, then delivery to an
  uncovered product in its own `full_dp`.
- **`custom_script`.** Use when required information is not directly available but can be accurately
  and deterministically derived from declared system variables or upstream node outputs through
  procedural computation, extraction, parsing, normalization, filtering, aggregation, calculation,
  restructuring, escaping, or serialization. Prefer it when downstream correctness materially
  depends on the derived value. Do not use it for connector access, subjective or semantic judgment,
  missing external facts, or uncertain inference. Read `references/custom-script-authoring.md`
  before authoring its PlanIR and complete Python program. Declare every input and output with a type
  and description. Add `user_message`: one trimmed, non-empty sentence using the language selected
  by the root Skill's `userMessage` language contract, with no Markdown, newline, node id, or
  implementation detail and at most 200 characters. It must describe the node's current purpose
  after generation, not repeat the user's request or history.
  Every Custom Script must additionally declare required `code_succeeded`
  (`boolean`) and `error_message` (`string`) outputs and follow the fail-open runtime contract. Any
  downstream write or delivery that depends on accuracy-critical derived data must be gated on
  `code_succeeded isTrue`.
- **`condition`.** Prefer folding ordinary skip/filter logic into the DP, except for the mandatory
  pre-write meeting eligibility gate above. For a real visual branch,
  provide 1–6 named `routes`, each with one or more Workflow condition objects (`key`, `condition`,
  `value`, optional `join`), and set `determined_by_ai`. A condition edge is a three-item tuple
  `[source, target, branch]`; `branch` must be a route name or `Default`. Conditions are structural
  and are not looked up in the node catalog. Use only `eq`, `neq`, `gt`, `lt`, `gte`, `lte`,
  `contains`, `notContains`, `isIn`, `isNotIn`, `startWith`, `notStartWith`, `endWith`,
  `notEndWith`, `isEmpty`, `isNotEmpty`, `isTrue`, or `isFalse`; the compiler normalizes common
  aliases such as `equals` to `eq` and rejects everything else. Gate a downstream write on a typed
  boolean (`isTrue`), never on non-empty prose. In a primary-delivery/fallback graph,
  `fallback_required` is true only when usable content exists and primary delivery failed; it is
  false for both no-data and successful-delivery outcomes.
- **`html` (narrow creation exception).** Only when the caller's `allow_html_node` argument and explicit
  hosted/rendered-HTML-page or shareable-HTML-link intent both exist, set top-level
  `html_node_requested: true` and add one or more `html` steps using
  `html-node-creation-contract.md`, `generate-workflow-html.md`, and
  `zoom-brand-style-guide.md`. Each step requires `user_message` under the same current-purpose,
  single-line, language-selection, and 200-character contract as Custom Script. It may only present declared upstream
  output. Keep it terminal unless the user also explicitly requested delivery of the rendered
  page's **link** through a named product. For that case only, connect the HTML node directly to one
  terminal DP whose `instruction_contract.inputs` binds `{{html_step_id.url}}`; the DP must stop
  without sending when that URL is unavailable and must report success only after the named product
  confirms delivery. This exact canvas-safe binding is also the serialized binding; do not add
  filters or runtime-envelope segments such as `.output.url` or `.response.output.url`, because
  the editor renders those forms as `Unknown Variable`. The compiler appends a required delivery-DP
  execution contract that rewrites known legacy render-route prefixes to
  `/aic/?embedded=true#/aic/render/` while preserving the scheme, authority, and artifact token. Do
  not bind `fileId` or `content` as a substitute for the shareable link. Do not use HTML for inline
  email/body/template text, ordinary conversation, a
  generic report without HTML intent. "HTML link", "HTML page
  link", "HTML link card", online/shareable HTML URL, and a URL explicitly requested from an HTML
  node all select the hosted artifact path even when email or chat is the delivery product. Without
  that gate, HTML remains outside the palette and `compile_workflow.py` rejects it.
- **`voice_message` / `sms_message` (mobile notify).** Add a platform mobile-notify node only when
  the ready brief explicitly asks for a phone call or a text message. Both kinds take the identical
  body; only `kind` changes:

  ```json
  {
    "id": "call_me",
    "kind": "voice_message",
    "template_id": "tpl_8f3a9c2d1b7e4a6f",
    "recipient": { "phone_number": "4155550123", "region_code": "+1" },
    "variables": {
      "user.displayName": "{{ROOT.sysWorkflowCreator.display_name}}",
      "meeting.title": "{{trigger.meeting.meeting_topic}}",
      "meeting.start_time": "in 10 minutes",
      "meeting.url": "by going to your Zoom Workplace app or refer to your meeting information details"
    }
  }
  ```

  The platform speaks or texts a fixed sentence per template; the step only fills its variables.
  Pick the template whose sentence fits the request:

  | Template | `template_id` | Fits | Sentence |
  |---|---|---|---|
  | Meeting Start Reminder | `tpl_8f3a9c2d1b7e4a6f` | before a meeting (`meeting.start`, negative `time_offset`) | `Hi {{user.displayName}}, your meeting {{meeting.title}} is starting at {{meeting.start_time}}. Join here: {{meeting.url}}` |
  | Meeting End Reminder | `tpl_c4d91e7a2b5f8a03` | after a meeting (`meeting.end`, `meeting.summary_created`) | `Hi {{user.displayName}}, your meeting {{meeting.title}} ended at {{meeting.end_time}}. Here is a recap of your action items: {{Summary or Message URL}}` |
  | Scheduled Reminder | `tpl_3e8f1a6b9c2d4f70` | a reminder at a time or on a schedule | `Reminder: It's time for the event: {{workflow.name}}. View details at: {{workflow.url}}` |
  | Workflow Success Reminder | `tpl_d7c2a5e9f4b1a863` (default) | the workflow's other work finished | `Success! Workflow '{{workflow.name}}' has been completed. View results at: {{workflow.url}}` |

  Compiler-enforced facts (a rejection here is not a schema you may work around):

  - `template_id` is one of the ids above. Never invent one and never carry one over from an
    attached workflow or example;
  - `variables` declares exactly the chosen template's keys — a missing key leaves a literal
    placeholder in the delivered message, an extra key is silently dropped by the platform;
  - a variable value is a literal, `{{ROOT.sysWorkflowCreator.display_name}}` (the workflow owner's
    name), a declared top-level output of an upstream node, or one field the trigger declares
    inside a top-level output (`{{trigger.meeting.meeting_topic}}`; see `trigger_lookup.py
    --node-id` `nested_output_fields`);
  - `phone_number` is digits with an optional leading `+`; `region_code` carries the `+` (`+1`,
    `+86`);
  - the step is terminal (both nodes declare no outputs) and may follow a trigger, a condition
    branch, a guided DP, a Custom Script, or a full DP.

  Parameter sourcing (the part that is wrong without being stated):

  - The user's own name: `{{ROOT.sysWorkflowCreator.display_name}}`.
  - Meeting title: `{{trigger.meeting.meeting_topic}}` under a meeting trigger.
  - Times are spoken as written: give a relative literal that matches the offset ("in 10 minutes",
    "a few minutes ago"), not a raw timestamp binding.
  - `meeting.url`: the trigger declares no join link; use the literal in the example above.
  - `workflow.name` — default to the compiled workflow's own name; for a Scheduled Reminder, the
    event the user wants to be reminded of. Preserve a name the user stated.
  - URLs (`workflow.url`, `Summary or Message URL`) — the run URL is not knowable while authoring.
    Emit `""` unless the user supplied a concrete URL or an upstream node declares a URL output worth
    binding (`{{dp1.report_url}}`). Never invent a hostname or reconstruct a link from an id.

  Content is not authorable beyond these variables: never add an upstream DP whose purpose is to
  write the call or message text, and never tell the user the call/text will say something it will
  not.
- **Composition.** Use trigger/read → DP → Custom Script when deterministic derivation is needed;
  append HTML only under its separate narrow creation gate. Custom Script owns accuracy-sensitive
  procedural transformation and safe serialization, but never emits HTML elements. HTML exclusively
  owns markup and display construction.
- **Do NOT** emit action / Ask AI / LLM nodes. Connector access and semantic reasoning stay in DP;
  deterministic local derivation uses Custom Script.
- **Outputs.** A DP always declares a `response` output (the compiler guarantees it). Every explicit
  output in newly authored PlanIR must have a meaningful non-empty description. Capsule
  `typed_outputs` are mandatory and the compiler merges them with PlanIR outputs without allowing
  their types to be changed or dropped. Declare any additional typed output when a downstream step
  binds it. Because the compiler requires `response` to begin with a compact execution receipt,
  never bind `response` to an HTML slot that the template parses as JSON. For structured HTML,
  declare and bind a separate DP output whose value is only the valid JSON payload. The compiler
  rejects JSON-parsed HTML slots bound to the receipt-prefixed `response`. The receipt appears before
  long-form content: observed outcome, concrete source/read evidence, and every attempted write's
  provider, operation, resolved target, provider-confirmed status, and returned id/URL when one was
  supplied. Add a terse `Checks:` list marking every core requested section, field, constraint, and
  required sink `OK` or `MISSING`; this is the bounded content proof when a long artifact body is
  truncated downstream. Never hide a failed core check to shorten the receipt. When no write ran,
  state that explicitly with the reason.
- **Side effects.** Author only operations the user requested. "Generate", "prepare", or "create a
  plan/report/brief" produces DP output; it does not authorize email, chat, document/record creation,
  or an external update. A named formatting/helper capability does not authorize delivery. But an
  explicit request to send/share the generated artifact's **link** does authorize and require
  persistence: use the named document product, or default an unnamed report/brief/tracker/log link to
  Zoom Canvas Doc (`zm.doc.doc.doc_nodes`). An explicitly requested hosted HTML page/link/card or HTML-node
  URL already names the HTML Render artifact surface, so preserve it and never substitute Zoom Canvas Doc.
  Include the named document app or delivery app in the consuming DP as applicable, require a
  provider-returned link before delivery, and never substitute inline response or message text for
  the link. A requested
  no-data notification branch creates no empty document. An email
  without an explicit or trigger-grounded recipient and a generic write destination with more than
  one possible product/record require clarification before PlanIR. A semantic relation to future
  trigger data is trigger-grounded: resolve exactly one match at run time and perform no write on
  zero or multiple matches instead of asking for its not-yet-known fixed identifier. A clarification answer is part of
  the user request: encode that exact recipient/destination in the consuming DP instruction contract and never
  replace it with the meeting host, attendees, stakeholders, or another trigger-derived default. A concrete
  identifier from a clarification reply also replaces the earlier placeholder or suggested default: copy it
  character-for-character into every consuming objective, procedure, side-effect policy, and success criterion,
  and remove the superseded target from those fields. Do not compile until this fidelity check passes.
  Answers such as "not specified", "unknown", "I don't know", and "no preference" do not replace a
  required destination or recipient. Return that unresolved blocker to the requirements step instead
  of encoding the non-answer as a target or inventing a nearby name.
  A send/post request that supplies a concrete topic and destination may use a concise neutral message
  drafted only from those words; exact prose is not a missing payload unless the request requires
  verbatim wording, a quote, or additional unstated facts. Do not invent dates, links, logistics,
  commitments, or event details.
  A workflow-owner/requester/current-user recipient is a grounded run-time relation. Represent it as
  a distinct instruction input sourced from the authenticated workflow owner in workflow-run context,
  and repeat that exact relation in the procedure, side-effect policy, and success criteria. Do not
  leave only an ambiguous pronoun or substitute a meeting participant. When the request specifies a
  target field/section format or omission rule, repeat it in Output requirements and observable
  Success criteria so the saved workflow carries a verifiable formatting contract.

## Compiler outcomes

`compile_workflow.py` returns `{"status": "compiled" | "rejected", ...}`. Use its existing command
unchanged for ordinary turns. Add `--allow-html-node` only for a trusted-gated creation or update PlanIR containing
the explicitly requested HTML step or steps:
- `compiled` — a valid FlowData workflow plus `candidate_digest`, the SHA-256 digest of the
  exact serialized bytes saved for sharing (share that saved file unchanged).
- `rejected` — structural findings (fix the PlanIR and recompile).
- A persistence-budget rejection is repaired by keeping at most the highest-value guided DP and
  replacing the remaining suffix with one terminal full DP.
Essential missing details are returned to the requirements step for one clarification before
PlanIR is written; the compiler does not conduct an interview.
