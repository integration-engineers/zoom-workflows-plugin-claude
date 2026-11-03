# Product terminology contract

Apply this contract before interpreting product names or writing any user-visible workflow content.

## Product and capability model

Zoom Canvas Doc is the complete product name for the document surface. Accept `Zoom Docs`,
`Zoom Doc`, and `Zoom Canvas` as input aliases for that surface. Always emit `Zoom Canvas Doc` in
Builder-owned app labels, node descriptions, workflow metadata, task prompts, and user-visible
responses. `Doc` and `document` remain valid object terms when they are not used as the product name.

`Zoom AI Companion` requires contextual grounding rather than a global replacement. Brand context
maps to `Zoom AI`; agentic AI surface context maps to `ZoomMate`.

## Legacy input and current output

| Legacy wording accepted from the user | Builder-owned current wording | Stable identity to preserve |
| --- | --- | --- |
| Zoom Docs, Zoom Doc, Zoom Canvas | Zoom Canvas Doc | `zm.doc.*`, `zm.doc.doc.doc_nodes`, and existing `zoom_doc` tool/schema names |
| Zoom Team Chat, Team Chat | Zoom Chat | `zm.tc.*`, `zm.tc.tc.team_chat_nodes` |
| Deep Reasoning | AI Reasoning | `deep_reasoning`, `zm.aic.agent.deep_reasoning` |
| Zoom AI Companion (brand context) | Zoom AI | existing `zm.aic.*` identifiers |
| Zoom AI Companion (agentic AI surface context) | ZoomMate | existing ZoomMate identifiers and configuration names |
| Health Care | Zoom Clinical Notes | existing health and clinical node, tool, and schema identifiers |

Legacy wording is input-only compatibility context. In the final response, workflow metadata, node
labels, app labels, descriptions, and generated task prompts, use only the current wording above.
The existing AI node `node_name` value is a field-specific exception: keep `AI reasoning`; do not
change that field solely to capitalize "Reasoning". Use `AI Reasoning` in ordinary Builder prose.

## Preservation rules

- Preserve the raw user request exactly. Interpret legacy product mentions; never rewrite the request.
- Preserve user-authored literals character-for-character, including titles, message bodies, channel
  names, and quoted text that contains legacy wording.
- Preserve all IDs, app keys, node types, enums, event names, schema keys, binding paths, tool function
  names, and persisted workflow identity.
- For a semantic workflow update, write current mutable display labels in the new revision. Do not
  migrate stored workflow history. For a surgical Code or HTML edit, preserve every unrelated field.
