---
name: zoom-workflows
description: >-
  Build, demo, test, deploy, run, list, inspect, or turn off Zoom Workflows through the connected
  Zoom MCP server. Use for recurring or event-driven work whose data or trigger is a Zoom product
  (after each meeting, before each meeting, a weekly digest of meetings or Zoom Chat), even without
  the words "Zoom Workflow", and for a workflow that did not run. The five Workflow shortcut prompts
  (this skill followed by, for example, "send meeting summary" or "my zoom zodiac") ask to deploy
  that pinned workflow and run it once.
---

# Zoom Workflows

This plugin builds and runs Zoom Workflows: automations that live in the user's Zoom account and
keep running after the conversation. Resolve every path below from the directory containing this
`SKILL.md`; `../../Workflow` is the plugin's Workflow tree, not the shell's current directory or a
`Workflow` folder inside `skills/`. If a relative read fails, locate this file and resolve from its
actual path before concluding that the builder is missing.

## The connection

Everything live goes through the connected **Zoom MCP server** (the Zoom connector):

- **Workflow operations** (list, inspect, test run, deploy, undeploy, resume) are capabilities
  behind its discovery gateway: `capabilities_discover` with `paths: ["workflow"]`, then
  `capabilities_describe` and the read or write invoker. Some connections expose the `workflow_*`
  tools directly instead. `../../Workflow/skills/workflow-core/references/lifecycle.md`,
  *Reaching the tools*, covers both. The absence of literal `workflow_*` names in the tool list
  does not mean Workflow is unavailable.
- **Meeting data** for a one-time run comes from the same server's own tools: `search` on the
  `zoom_meeting` datasource for the meeting, `get_meeting_assets` only when a hit cannot show what
  the run needs. `../../Workflow/skills/workflow-demo/references/hero-fast-path.md`, *Find a test
  meeting*, has the procedure.

The plugin declares one MCP server, `zoom`, at `https://mcp.zoom.us/mcp/zoom/streamable`: the same
server as the **Zoom for Claude** directory connector, so a user who has both sees one set of
tools. If no Zoom MCP tools are available, or the server is not connected or rejects a call, say so
before anything else and how to fix it, for the host you are running in. In Claude: connect Zoom
for Claude with your Zoom account (Claude's Settings → Connectors, or the plugin's Connectors tab),
then start a new conversation (in Claude Code, check `/mcp`); on a Team or Enterprise plan where it
is not listed, the Claude admin has to add it. In Codex or ChatGPT: connect this plugin's Zoom
connection with your Zoom account from the plugin's settings or when the host asks, then start a
new conversation; in a workspace where the plugin is not available, the workspace admin has to
enable it. Do not call Zoom APIs directly outside the connected MCP tools. The host owns OAuth; never read, print, or
cache tokens, or ask the user to paste them or a callback URL into chat.

## Scope

Take an automation request when its data or trigger is a Zoom product (meetings, recordings,
transcripts, Zoom Chat) or a connected app the generator indexes (Jira, Salesforce, and others in
`resources/app_scope_index.json`), and the vendored generator supports both what starts it (its
trigger catalog, `scripts/trigger_lookup.py --list`) and the apps its steps use (a phone call or
text to the user is the generator's own voice/SMS step, not an app). When either is missing, say
so and leave it to the host's own scheduling. A request the host's scheduled task already handles
stays there. If the user has said not to use Zoom Workflow, or `lifecycle.md`'s credit and license
section has moved this conversation off Workflow, use the host's scheduling instead.

A one-time question about Zoom content (find, summarize, answer) is not a workflow: answer it with
the Zoom MCP tools directly. If the user selected this plugin for a one-time write that the
connected tools cannot complete, check the generator's `SKILL.md` and `app_scope_index.json`; with
a grounded destination and content rule, build it through `workflow-create` as a manual-trigger
draft and say clearly that compiling the draft has not performed the write.

## Capability menu and shortcuts

When the user asks what this plugin can do, run
`../../Workflow/skills/workflow-demo/scripts/hero_context.py --quick-menu --markdown --host <host>`
(`codex` in Codex, `claude` in Claude Code) and reproduce the table it prints exactly, header row
included. Its wording is reviewed product copy (the Zodiac entertainment note is required), and
each prompt carries the host prefix so the user can copy it as is. Keep any summary of your own
outside the table. Do not load every template.

Then offer to start one: ask once with this host's question tool which shortcut to try, one option per
shortcut in menu order, each labelled with the shortcut's name and a few words from its row, and no
recommended default. If the tool allows fewer options than there are shortcuts, make the last option
"More…" and ask again with the rest. Picking an option is the same request as sending that
shortcut's prompt: match it with `--match` and follow the fast path, including its destination
question. A free-text answer is a new request. If the host has no question tool, put each prompt in
its own fenced code block under the table so it can be copied.

To tell whether a message is a shortcut, run the same script with `--match "<the user's message>"`
and the host flag. It accepts the host prefix or the bare suffix the host passes when this skill is
invoked.

- A returned `template` is an explicit request to **deploy that pinned workflow and run it once**.
- A returned `needs_destination` (a shortcut with several destinations, such as "send meeting
  summary" or "meeting reminders", sent without one) is still that shortcut; the fast path asks for
  the destination.

For either, read `../../Workflow/skills/workflow-demo/references/hero-fast-path.md` and follow its
shortcut procedure without asking again whether to deploy or run. Required inputs, live
entitlement, and trigger schemas still need checking; never invent a channel, phone number, or
event payload. An explicit demo request or a template picked from the demo menu also goes to the
fast path. A concrete automation request other than an exact shortcut goes to `workflow-create`,
even when it resembles a pinned example; a saved workflow goes to inspection.

## Routing

Read the child skill under `../../Workflow/skills/` for what the user came for:

- a concrete automation to create or change: `workflow-create/SKILL.md`;
- a saved workflow's status or runs, or a run that did not happen: `workflow-inspect/SKILL.md`;
- first contact, "what can this do", or a goal that is still unclear: `workflow-onboard/SKILL.md`.

Before any live Workflow call, read `../../Workflow/skills/workflow-core/references/lifecycle.md`
on its own.
