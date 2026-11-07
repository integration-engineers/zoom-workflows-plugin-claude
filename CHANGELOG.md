# Changelog

All notable changes to this plugin are documented in this file.

## 0.3.21

- Listing icon at `.claude-plugin/icon.png` (512 x 512 PNG) and `privacyPolicyUrl` in the manifest.
- Phone calls and texts reach only the user's own phone verified in their Zoom account: when a
  request names someone else, the plugin says so before asking for anything and offers a Zoom Chat
  message to that person instead of asking for their number.
- Connection steps for Codex and ChatGPT alongside the Claude steps in the entry skill.

## 0.3.19

- Long runs: a run that is still `RUNNING` with no error is working, not stuck. The agent polls for
  about five minutes, then offers to follow the run in the background or keep waiting.
- A Deep Reasoning step's result is read from the fields its `output_schema` declares.

## 0.3.18

- First release in this repository; earlier development history is not included.
- Entry skill `zoom-workflows` for building, demoing, testing, deploying, running, listing,
  inspecting, and turning off Zoom Workflows through the Zoom MCP server.
- Internal skills: `workflow-onboard`, `workflow-demo` (with `zoom-zodiac-card`), `workflow-create`,
  `workflow-core`, and `workflow-inspect`.
- Five shortcut workflows backed by 14 pinned templates: meeting summary delivery (Gmail, Outlook,
  Slack, Confluence, Google Docs, OneDrive), meeting reminders (phone call, Gmail, Outlook, Zoom
  Chat, Slack), meeting chat to Slack, Salesforce opportunity update, and My Zoom Zodiac.
- Vendored `zoom-workflow-generator` with the node catalog, app scope index, and capsules, plus
  local scripts to compile and update workflow definitions and to prepare MCP request bodies.
- `.mcp.json` registers the `zoom` server at `https://mcp.zoom.us/mcp/zoom/streamable`, the same
  server as the Zoom for Claude connector. Authorization is managed by the host.
- Host adapters for Claude Code and Codex under `Workflow/skills/workflow-core/adapters/`.
- Added `AGENTS.md`, `CONNECTORS.md`, `CONTRIBUTING.md`, and this changelog.
