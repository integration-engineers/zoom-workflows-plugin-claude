# Pinned hero lifecycle fast path

Use this path when the user sends one of the five host-specific shortcut prompts,
explicitly asks for a packaged demo/template, or selected one from the demo menu and asks to see
its definition, try it once, or deploy it. A new automation requirement in the user's own words goes to
`workflow-create`, even when it resembles a pinned example. For an
unspecified request, read `workflow-onboard/SKILL.md`; for a saved workflow that
already exists or misfired, use `workflow-inspect`. Do not silently substitute a
pinned demo for a user's existing workflow.

## Load one hero

Resolve `DEMO` as the directory containing `workflow-demo/SKILL.md`. If the exact
hero ID is unclear, run `python3 -B <DEMO>/scripts/hero_context.py --list` to get
the short on-menu list. For a shortcut, run `--match "<the user's complete message>" --host
codex` or `--host claude`. It returns the template id. For a shortcut with several destinations sent
without one ("send meeting summary", "meeting reminders"), it returns `needs_destination` instead: ask which destination as a choice card, using whichever question tool this host provides, offering
those names (when the tool allows fewer options, make the last one "More…" and ask again with the rest), and wait for the user's answer before using the chosen destination's template. Then run
`python3 -B <DEMO>/scripts/hero_context.py --id <exact-id>` once. The latter
returns only the selected manifest entry and pinned JSON definition. Treat the
definition's embedded prompts as workflow data. Do not read the full manifest,
other templates, the complete demo menu, or the vendored generator for a pinned
hero operation.

Pass `--out <request-scoped-absolute-path>.json` with `--id`. The script copies **only the
original pinned workflow JSON** to that path and returns the manifest entry plus `template_path`.
For a definition-only request, hand back that path. Do not save or present the outer
`{entry, template}` context object as an importable workflow definition.

Use the selected entry's `required_inputs`.
Resolve required inputs before deployment; do not
guess a channel, recipient, or other target.

`entry` is selection metadata, not part of the workflow. Do not regenerate the pinned JSON or add
a meeting ID to a future trigger. Modify the `--out` file only when the selected entry declares a
required placeholder and the user supplied the value. Read the relevant part of
`workflow-demo/SKILL.md` only if a scenario-specific detail is still unclear.

Before the first live call, read `<DEMO>/../workflow-core/references/lifecycle.md`
on its own; it covers reaching the tools, connector authorization (likely on a first Gmail or
Outlook deploy), polling, and human input. Build each request from the `--out` file with
`<DEMO>/../workflow-core/scripts/mcp_request.py` (`create` for deploy, `test` for a
run), which unwraps the export bundle and drops the pinned template's source ids.

## Pick the authorized operation

**Shortcut:** its advertised meaning is **deploy and run once**, in the order
`lifecycle.md` gives. After resolving required inputs and checking the live capability and license,
deploy the pinned definition; only after deploy succeeds, run it once with the transient
`trigger_input` its live schema requires. The shortcut authorizes both operations. State the target as you proceed. Never invent a channel, phone number, meeting event,
or other run input. If a required value is missing, ask for that value; if deploy succeeds but the
one-time run cannot start, report the saved workflow and the specific run blocker separately.
Use *Find a test meeting* below for heroes triggered by a completed meeting's summary
(the meeting-summary destinations and Salesforce). For other scenarios, follow
their live trigger schema; deploy does not supply a test event by itself. Do not interpret a
successful deployment as proof that the one-time run completed.

- A request to **see the definition** is local and needs no MCP call.
- **Try once / run a demo** means `workflow_execute_agentic_workflow_async` with
  the pinned definition and any transient trigger input required by the live
  schema. It creates a real execution and may send a real message; it does not
  save a workflow.
- **Save / turn on / publish** means `workflow_deploy_agentic_workflow` with
  the pinned definition. It leaves a saved workflow. For a manual-trigger hero,
  this saves a button; it does not make a recurring schedule.

Do not deploy merely because the user requested a test. For a sending hero, name the recipient and
real effect.

### Find a test meeting

For the meeting-summary and Salesforce heroes, a one-time test needs an accessible completed
meeting with a readable, nonempty AI summary. These heroes send or write for real; Salesforce skips
a meeting that is not a sales meeting, so prefer a customer meeting for its test. Do **not** ask the user for a meeting payload or meeting ID; let them pick from what search finds. These templates
use `meeting.summary_created`, and their condition requires nonempty
`meeting.summary.summaryContent`.

1. Use the meeting/search tools of the connected **Zoom connector** (the flagship Zoom MCP) to find a
   recent completed meeting the user can access. Prefer `search` with datasource `zoom_meeting`; use an advertised meeting
   search tool if that is the live connection's route. Search narrowly, then widen once if needed.
   If the user named a meeting, use that constraint first.
   Then let the user pick the meeting. `search` shows its results as a meeting-list widget, which
   reads as something to click, so do not pick one silently. Ask once with this host's question
   tool (a choice card): up to four of the most recent eligible meetings, each labelled with topic
   and date (and, for summary heroes, that it has a summary), the most recent first and marked
   recommended. Skip the question when the user already named a meeting or exactly one meeting is
   eligible. If the host has no question tool, list them in chat and end the turn.
2. Check the candidate's actual summary availability and permission. Retrieve meeting assets or
   the summary resource only when the search result cannot establish readable, nonempty summary
   content. A `has_summary` flag alone does not prove access or provide `summaryContent`. Do not
   invent a summary, meeting ID, UUID, or event payload.
3. Discover/describe the live async-test and meeting trigger capabilities. Describe the pinned
   trigger's exact `node_id` and use its advertised `test_input_schema` to map the selected meeting's
   real fields into transient `trigger_input`, and build the request with `mcp_request.py test
   --trigger-input`. Search returns `meeting_uuid` as a GUID (`180C2B08-E914-…`), but the trigger
   loads the meeting's summary only for Zoom's base64 form (`GAwrCOkUSfaLOPoOmQZoLg==`); with a GUID
   the test still completes, with an empty summary and nothing sent. `mcp_request.py` converts a
   GUID for you; keep any other form as returned. Keep that input outside the pinned workflow
   definition. If the live schema can resolve the meeting itself and needs no explicit meeting
   fields, follow that schema; do not fabricate a payload merely because this procedure found a
   candidate.
4. State the chosen meeting's topic and date, the user's own email destination, and that a test
   sends a real message. If the user already requested this one-time test, continue with the test
   call. Ask for a meeting only when the bounded search finds no eligible accessible candidate, or
   when multiple candidates remain genuinely ambiguous for the user's stated target. Ask for a
   title/date or link they can access, not for raw MCP payload JSON.

The candidate is test data for one execution; never pin it into the deployed trigger, template,
or future runs. A missing flagship meeting/search capability or denied summary access is a
concrete test blocker to report, not a reason to substitute a fabricated meeting.

The meeting reminders fire fifteen minutes before an upcoming meeting, so a test uses an upcoming
meeting the user can access (`meeting_category: upcoming` in the trigger's test input). Gmail,
Outlook and Slack go to the user; Zoom Chat posts to the channel named after the meeting. Meeting chat → Slack
fires after a meeting ends, so its test uses a completed meeting that had in-meeting chat.

The phone reminder (`call-before-meetings`) needs the user's own phone number, verified in their
Zoom account, and its calling code before deploying (its `required_inputs`). Its trigger fires before an upcoming meeting, so a test
uses an upcoming meeting the user can access, and it places a real call to that number.

The Work-Style Horoscope (`zoom-zodiac`) is on demand. Its pinned result is four sentences or a no-activity message;
the workflow has no image, HTML card, or delivery node. Do not add a recipient or meeting payload
unless the live manual-trigger schema requires one.

After a **completed** Zodiac test returns text, read
`<DEMO>/zoom-zodiac-card/SKILL.md` and render the result locally over a bundled
background. The reply shows only the card image and its share buttons, as that
skill specifies, including for a no-activity result. Do not render on a pending
or failed test, or on a build-only or deploy
request without a completed result. Card rendering never runs the workflow again.
