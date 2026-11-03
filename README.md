# Zoom Workflows

Build, test, deploy, run, list, inspect and turn off **Zoom Workflows** from Claude. A Zoom Workflow
is an automation that lives in your Zoom account and runs on its trigger, for example "after each
meeting, email me the summary" or "before each meeting, remind me in Slack".

## Requirements

- A Zoom account with Workflow access.
- The **Zoom for Claude** connector, connected with your own Zoom account. The plugin declares the
  same server (`https://mcp.zoom.us/mcp/zoom/streamable`), so Claude shows one set of Zoom tools.
- Python 3.9 or later, to compile a new custom workflow locally.

## Try it

Ask "what can you do with Zoom Workflows?" for five shortcuts: send meeting summary, meeting
reminders, meeting chat to Slack, update Salesforce after a customer meeting, and My Zoom Zodiac.
Or describe your own automation in plain words.

## What the plugin runs, sends and fetches

- **Zoom MCP server.** All Zoom access goes through the declared Zoom server, signed in as you:
  workflow list, definition, test run, deploy and turn off, through the server's Workflow tools,
  plus meeting search and meeting assets (such as an AI summary) to pick the meeting a one-time test
  uses. The plugin calls no other Zoom API and never reads or stores your OAuth tokens.
- **Local scripts.** Bundled Python scripts run on your machine. They compile a workflow
  definition from the plan Claude writes, prepare MCP request bodies, and render the Zodiac card
  image. They make no network calls.
- **One optional download.** The Zodiac card needs the Pillow imaging library. If it is not
  installed, the skill creates a temporary virtual environment outside the plugin and installs
  Pillow from PyPI.
- **Real effects.** A test run is a real execution and a deployed workflow runs on its trigger. They
  can send email (Gmail, Outlook), post to Slack or Zoom Chat, save to Google Docs, OneDrive or
  Confluence, update Salesforce, or call your own verified phone, as the workflow defines. Claude names the target before it deploys or runs; sending a shortcut
  prompt asks it to deploy that workflow and run it once.
  Third-party apps inside a workflow ask for their own authorization in Zoom the first time.

## Data handling

Workflow definitions, runs and their data live in your Zoom account and follow Zoom's privacy
policy (https://explore.zoom.us/en/privacy/). The plugin keeps no data of its own. Generated
workflow files and Zodiac cards are written to your local working directory or Claude's outputs
folder, and nothing is uploaded or shared unless you choose to. The Zodiac share buttons only open
X or LinkedIn in your browser with the text filled in.

## Cost

Each user's first 10 workflow runs are free, with no license required. After that, meeting
summaries to Gmail or Outlook stay free, and the other shortcuts use 10 ZoomMate credits per run,
which needs a ZoomMate license.

## Connectors

See [CONNECTORS.md](CONNECTORS.md). The plugin declares one MCP server, `zoom`, in
[`.mcp.json`](.mcp.json). Authorization is managed by Claude through the Zoom for Claude connector,
so there is no token to set. Without the connection, Claude can still plan a workflow and compile
its definition locally; testing and deploying need the connection.

## Structure

```text
Zoom Workflows Plugin for Claude/
├── .claude-plugin/plugin.json
├── .mcp.json
├── AGENTS.md
├── CHANGELOG.md
├── CONNECTORS.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── skills/
│   └── zoom-workflows/
└── Workflow/
    ├── hero-templates/
    └── skills/
        ├── workflow-onboard/
        ├── workflow-demo/
        │   └── zoom-zodiac-card/
        ├── workflow-create/
        ├── workflow-core/
        │   ├── adapters/
        │   ├── references/
        │   ├── scripts/
        │   └── vendor/zoom-workflow-generator/
        └── workflow-inspect/
```

[AGENTS.md](AGENTS.md) is a discovery file for agent tools that read it, and
[CHANGELOG.md](CHANGELOG.md) lists release notes.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Support

Zoom: https://support.zoom.com

## License

Licensed under the MIT License. See LICENSE.
