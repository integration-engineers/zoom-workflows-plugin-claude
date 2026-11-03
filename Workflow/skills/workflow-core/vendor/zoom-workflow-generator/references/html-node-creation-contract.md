# HTML node creation contract

Use this contract only in `declarative_workflow_json_only` or
`declarative_workflow_update_only` mode when both conditions hold:

1. the caller's arguments contain exactly `"allow_html_node":"true"`; and
2. the ready workflow brief explicitly requests a hosted/rendered **HTML page** or a shareable
   HTML page/link artifact.

That argument is permission to consider this node, not evidence that the request is a workflow or needs a page. Do
not use HTML creation for ordinary conversation, inline HTML email/body/template generation,
source-code examples, or an unqualified report/dashboard. Artifact
intent, not the delivery channel, is decisive: "HTML link", "HTML page link", "HTML link card",
online/shareable HTML URL, or a URL explicitly requested from an HTML node means a hosted HTML
artifact. Emailing or chatting that artifact means bind and deliver its returned `url`; it does not
turn the page into inline message markup. Only an explicit request for HTML source or HTML content in
the email/message body is formatting-only and stays in DP. If permission is absent, use the
unchanged trigger/condition/DP palette and the normal compiler command; the compiler rejects HTML.

## Hosted artifact short-name hint

When a hosted HTML artifact is later offered to Web App Publish, its source or display name is
metadata only and does not determine the published hostname. Web App Publish assigns the hostname
at publish time on the trusted backend and returns it in the publish response. The hostname uses a
fixed `page-` prefix followed by an 8-character lowercase alphanumeric random suffix, and the
trusted API validates that exact slug format. Do not put the full user request, long description,
PII, credentials, or opaque identifiers in the artifact's display name.

## Authoritative compatibility reference

Match the current Workflow editor rather than inventing a renderer:

- worker/node id: `zm.system.operators.html` (`HTML` / `HTML Render`);
- persisted `node_type`: `logic`;
- persisted `input_map`: `template`, `slots`, `parameter`, `userMessage`;
- persisted `config`: preview-only `mock_data`;
- runtime rendering: Zoom Workflows performs flat `${name}` / `$name` substitution and displays
  the stored artifact;
- execution: the Workflow service stores `{template, params}` as an owner-scoped artifact and
  returns a shareable URL. It does not run during authoring.

The editor declares historical outputs `{html,url}`, while the runtime executor returns
the nested envelope `{response:{success,output:{fileId,url,content}}}`. The Workflow variable
converter maps that runtime envelope to the node's logical outputs, so PlanIR must bind
`{{html_step.url}}`; do not author `{{html_step.output.url}}` or
`{{html_step.response.output.url}}`. The compiler declares the observed inner
`{fileId,url,content}` contract so downstream bindings never target a missing `html` field.

## PlanIR shape

Set `html_node_requested: true` at PlanIR top level and add one or more HTML steps. Before writing or
modifying any template, read `generate-workflow-html.md` and `zoom-brand-style-guide.md` in full and
apply their animation and visual guidance within the safety rules in this contract:

```json
{
  "id": "html_page",
  "kind": "html",
  "node_name": "HTML page",
  "user_message": "<current-purpose sentence in the selected user language>",
  "template": "<!DOCTYPE html><html>...</html>",
  "slots": [
    {"name": "summary", "type": "string", "required": true}
  ],
  "parameter": {
    "summary": "{{s1.response}}"
  },
  "mock_data": {
    "summary": "Project Atlas completed its API migration and remains on schedule."
  }
}
```

The compiler rewrites logical `{{step.output}}` parameter bindings to emitted reference ids. Every
parameter must bind one declared top-level output from an upstream node. The HTML node is presentation
only: keep all data acquisition, reasoning, transformations, and external delivery in DP nodes.
`user_message` is produced in the same model response as the template and describes the node's
current purpose after generation. It must be a trimmed, non-empty, single-line sentence using the
language selected by the root Skill's `userMessage` language contract, with no Markdown, node id, or
implementation detail, and at most 200 characters.

## Optional link-delivery successor

Keep the HTML node terminal unless the ready brief explicitly asks to send or share the rendered
page's **link** through a named product. In that one case, connect the HTML step directly to exactly
one terminal DP delivery step. The delivery step must:

- bind the HTML step's declared `url` output as a named `instruction_contract.inputs[].source` such
  as `{{html_page.url}}`;
- use the exact requested destination product and grounded recipient/channel, with that product in
  `requested_apps`;
- rely on the deterministic compiler to append a required delivery-DP execution contract that
  rewrites known legacy render-route prefixes into the recipient-facing
  `/aic/?embedded=true#/aic/render/` prefix while preserving the worker URL's scheme, authority,
  and artifact token;
- send the normalized page URL rather than copying the HTML source, `fileId`, or `content` into the
  message;
- stop without sending if the URL is absent, empty, or not returned by the HTML worker; and
- report delivery only after the destination provider confirms it.

The serialized binding stays exactly `{{html_page.url}}`: the editor's downstream-node variable picker
does not recognize filter-bearing bindings or runtime-envelope paths and renders either form as
`Unknown Variable`. Do not add filters or `.output` / `.response.output` segments in PlanIR. The
compiler instead appends the required route-normalization procedure to the terminal delivery DP;
execution details may still show the HTML worker's raw value nested under `response.output.url`.

This rule is product-neutral. For example, a hosted HTML link/card delivered by email uses the HTML
node's `url` as input to a terminal Gmail/Outlook delivery DP, while an HTML-node URL delivered in
Zoom Chat uses the same shape with a terminal Zoom Chat DP. Never replace either request with a Zoom
Doc, an inline HTML body, or a claim that the HTML node must be final.

The compiler accepts either a terminal HTML node or this single `HTML -> terminal DP` shape. It
rejects multiple successors, a non-DP successor, a delivery DP that does not bind `url`, or any node
after the delivery DP. This is a link-delivery capability, not permission for arbitrary post-render
processing.

Example continuation for "Generate an HTML page and send the link to Zoom Chat":

```json
{
  "id": "send_link",
  "kind": "full_dp",
  "intent": "Send the rendered HTML page link to the grounded Zoom Chat destination.",
  "instruction_contract": {
    "version": 1,
    "role": "Zoom Chat link delivery assistant",
    "objective": "Send the rendered HTML page URL once to the exact grounded Zoom Chat destination.",
    "inputs": [
      {
        "name": "html_page_url",
        "source": "{{html_page.url}}",
        "purpose": "Shareable URL returned by the HTML Render node"
      }
    ],
    "procedure": ["Verify the normalized page URL is present, then send it once to the grounded destination."],
    "outputs": ["Return the provider-confirmed Zoom Chat delivery result."],
    "missing_data_policy": "Stop without sending when the HTML page URL or destination is unavailable.",
    "evidence_policy": "Use the bound normalized HTML page URL exactly; do not invent or replace its authority or artifact token.",
    "tool_policy": "Use only Zoom Chat capabilities for this delivery.",
    "side_effect_policy": "Send exactly one message containing the normalized HTML page URL to the grounded destination.",
    "success_criteria": ["Report success only after Zoom Chat confirms the message delivery."]
  },
  "requested_apps": ["zm.tc.tc.team_chat_nodes"]
}
```

Use edges `["producer", "html_page"]` and `["html_page", "send_link"]`. A standalone-page request
without link delivery keeps only the first edge and leaves the HTML node terminal.

## Template and slot rules

- Produce a complete HTML5 document beginning with `<!DOCTYPE html>` and containing `<html>`,
  `<head>`, `<body>`, and viewport metadata.
- Keep the template under 200,000 UTF-8 bytes and within the compiler's smaller whole-workflow
  persistence budget.
- Slots are exactly `{name,type,required}`. Allowed types are `string`, `integer`, `number`,
  `boolean`, `object`, `array`, `null`, and `unknown`.
- The names in `slots`, `parameter`, and `mock_data` must match exactly. Every declared slot must
  appear in the template, and every template slot must be declared.
- Use only flat `${name}` or `$name` substitution. No dot paths, filters, calls, arithmetic,
  conditionals, loops, Velocity/Jinja directives, or JavaScript template literals.
- A DP's required `response` output always begins with the execution receipt. Render a slot bound to
  `{{dp.response}}` as display text; never parse it as JSON or treat it as a bare array/object.
- For arrays or branching, declare a separate typed DP output such as `tickets_json` whose value is
  only a valid JSON string, bind that dedicated output to the HTML slot, inject it into an
  `application/json` element, and parse/render it with plain JavaScript. The compiler rejects a
  JSON-parsed slot bound to a DP's receipt-prefixed `response`.
- `mock_data` is preview-only and must contain a realistic non-empty value of the declared type for
  every slot, with no extra keys.
- Prefer semantic HTML, responsive inline CSS, and a small readable page. Use inline SVG for simple
  visuals. External libraries are unnecessary for ordinary summaries.
- Never emit `iframe`, `object`, `embed`, `frame`, `frameset`, `base`, or `form`; browser storage,
  cookies, parent navigation/messaging, workers, or runtime networking/messaging APIs such as
  `fetch`, XHR, WebSocket, EventSource, or `postMessage` are forbidden.

The compiler owns FlowData shape and rejects violations. Never hand-write the final workflow JSON.
