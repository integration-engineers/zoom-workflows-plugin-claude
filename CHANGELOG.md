# Changelog

All notable changes to this plugin are documented in this file.

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
