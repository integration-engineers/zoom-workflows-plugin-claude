---
name: workflow-onboard
description: First contact and unclear Workflow goals — pitch, license fit, and a first demo. Read from zoom-workflows.
---

# Workflow onboard

The front door. One line of pitch, make sure the connection works, find out what the
user's license can actually do, then route. Don't build here.

**One-line pitch:** describe what should happen around your meetings, and we can build a Zoom
Workflow for preparation, follow-through, or shareable intelligence. A live workflow is turned on
only when you ask for deployment.

## Route on intent

Route by **why the user came**: exploring an example, creating their own automation, or inspecting
an existing one. Similarity to a packaged template is an implementation detail, not a routing rule.

- **"What can this do"** → show the shortcut menu as the entry skill describes.
- **Explore or demo** — first install, "show me a workflow demo", "not sure where to start", or an
  explicit choice of a demo/template from the menu →
  **go to `workflow-demo`.** Lead with one visible win (a first-try summary to the user's own email, or
  Zoom Zodiac — the high-wow one). If they come back with "what else / anything for my role",
  escalate to demo's richer menu (meeting chat to Slack, meeting reminders, Salesforce). Don't make them describe a spec first.
- **A concrete automation, a change to a saved workflow, or a saved workflow that misbehaved** —
  once the user names one, continue in `workflow-create` (new or changed) or `workflow-inspect`
  (misbehaved) with what you learned here. A request does
  not become a demo merely because a pinned template could help implement it.

## Check the active connection only when the task needs it

Use the Workflow tools advertised by the active Zoom MCP connection; the host's Zoom connector owns
sign-in. Do not request tokens or callback URLs in chat, attempt browser extraction, or substitute a
direct API call.

Building a *local* definition needs no token. So a missing or unreachable connection blocks demo
test-runs and deploys, and blocks nothing about designing or explaining a workflow. When you hit
that wall, say which step is blocked and what unblocks it — don't turn the front door into an OAuth
checklist.

## Hand off with context

When you route, carry what you already know — connection state and any outcome the
user named — so the next skill doesn't re-ask. Re-asking reads as if the front door did nothing.
