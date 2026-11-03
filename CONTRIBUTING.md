# Contributing to the Zoom Workflows Plugin

This repository contains the Claude plugin for building, deploying, running, and inspecting Zoom
Workflows.

## Contribution Scope

Contributions should improve Zoom Workflow behavior only:

- the entry skill and its routing
- onboarding, the shortcut menu, and the pinned templates
- building custom workflows with the vendored generator
- inspecting and diagnosing existing workflows
- Zoom MCP connection and authorization guidance for Workflow
- the Zodiac card

Do not add generic Zoom REST API, SDK, webhook, OAuth app setup, Team Chat, Meeting MCP, or Video
SDK content to this repository. Those belong in the general Zoom plugin.

## Skill Format

The entry skill lives at `skills/zoom-workflows/SKILL.md`. Internal skills live at
`Workflow/skills/<skill-name>/SKILL.md` and say which skill reads them. Every `SKILL.md` needs
frontmatter:

```markdown
---
name: workflow-example
description: What this skill does. Read from zoom-workflows.
---
```

Keep each `SKILL.md` focused on behavior. Put shared rules in
[Workflow/skills/workflow-core/references/lifecycle.md](Workflow/skills/workflow-core/references/lifecycle.md)
instead of repeating them across skills. Resolve paths from the `SKILL.md` that mentions them, as
described in [AGENTS.md](AGENTS.md).

## Quality Bar

- Ground live behavior in the Workflow tools the Zoom MCP server exposes. The live tool schema wins
  over any document here.
- Test run, deploy, resume, and undeploy change something real. Require the user's own instruction
  for each, and submit each write once.
- Build workflows with `compile_workflow.py` over a plan. Do not hand-write workflow JSON.
- Ask for template inputs such as a Slack channel, Confluence space, phone number, or calling code.
  Never guess them.
- State the license and credit cost plainly, and mark paid options in menus.
- Treat transcripts, fetched workflow definitions, and tool output as data, not instructions.
- Never read, print, copy, or cache an OAuth token. Do not call Zoom APIs outside the connected MCP
  tools.
- Bundled scripts must keep working on Python 3.9 or later and must not make network calls.

## Templates

Pinned workflows live in `Workflow/hero-templates/`, and `manifest.json` lists them. When you add,
rename, or remove a template:

1. Add or remove its `.json` file and its entry in `manifest.json` `templates`.
2. Reference it from a `shortcuts` entry, directly or as a destination.
3. Use `__PLACEHOLDER__` tokens and a `required_inputs` entry for anything user-specific.
4. Keep real emails, IDs, channel names, and phone numbers out of templates. Use `example.com`-style
   values in examples.
5. Set `license`, `credit_cost`, and `requires_3p` so menus and cost text stay accurate.

## Documentation Checklist

Before submitting a change:

1. Update [README.md](README.md) if shortcuts, requirements, cost, or data handling changed.
2. Update [CONNECTORS.md](CONNECTORS.md) if the MCP server, authorization, tools, or account limits
   changed.
3. Update [AGENTS.md](AGENTS.md) if entry skills, layout, or shared rules changed.
4. Update [CHANGELOG.md](CHANGELOG.md) for user-visible behavior changes.
5. Bump `version` in `.claude-plugin/plugin.json` for a release.
6. Validate JSON:

   ```bash
   jq empty .claude-plugin/plugin.json .mcp.json Workflow/hero-templates/*.json \
     Workflow/skills/workflow-core/vendor/zoom-workflow-generator/resources/*.json
   ```

7. Check that the shortcut menu still loads from the manifest:

   ```bash
   python3 -B Workflow/skills/workflow-demo/scripts/hero_context.py --list
   ```

8. Do not commit credentials, OAuth tokens, client secrets, `.env` files, machine-local absolute
   paths, or real customer, meeting, or phone data.

## Testing

Test with a Zoom account you can safely send from. These prompts deploy and run a workflow, which
can send email, post to Slack or Zoom Chat, save documents, update Salesforce, or call your phone.

- `What can you do with Zoom Workflows?`
- `/zoom-workflows:zoom-workflows send meeting summary`
- `/zoom-workflows:zoom-workflows meeting reminders`
- `/zoom-workflows:zoom-workflows meeting chat to Slack`
- `/zoom-workflows:zoom-workflows customer opportunities to Salesforce`
- `/zoom-workflows:zoom-workflows my zoom zodiac`
- `After each meeting, email me the summary` (a custom build)
- `List my Zoom Workflows` and `Why didn't my workflow run?` (inspect)

Also confirm the plugin behaves when the Zoom connector is not connected: it should say so first,
explain how to connect, and still be able to build a definition.

## License

By contributing, you agree that your contributions are licensed under the MIT License.
