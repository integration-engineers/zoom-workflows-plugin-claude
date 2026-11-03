# Generate Workflow HTML (HTML Render Node)

This describes the invariants an HTML render node (`zm.system.operators.html`) must satisfy. Read
it in full, with `html-node-creation-contract.md` and `zoom-brand-style-guide.md`, before writing or
changing an HTML node's template.

## Contents

1. Mock data
2. Generation principles
3. Template and sandbox rules
4. Pinned CDN allowlist
5. Data injection

Allowed slot types are `string`, `integer`, `number`, `boolean`, `object`, `array`, `null`, and
`unknown`.

## Mock data

Use these value shapes:

| Slot type | Preview value requirement |
|---|---|
| `string` | Non-empty, domain-realistic string |
| `integer` | Whole number |
| `number` | Integer or floating-point number |
| `boolean` | `true` or `false` |
| `array` | Non-empty array |
| `object` | Object with at least one key |
| `null` | `null` |
| `unknown` | Non-empty realistic string |

Match the slot semantics: `reportTitle` may be `Q3 2026 Sales Summary`, `attendeeCount` may be `28`,
and `ownerEmail` may be `alice@example.com`. Never use type names, `value`, `example`,
`placeholder`, empty arrays/objects, or zero for a count-like slot.

## Generation principles

1. Prefer display-first plain HTML, Tailwind, and inline SVG.
2. Use React or a chart library only when the page genuinely needs state or a real chart.
3. Prefer pinned UMD bundles. Never mix UMD React with an ESM React-consuming import.
4. Keep only scripts and libraries that render a requested element.
5. Generate the template at design time; HTML/Make performs no runtime AI work.

## Template and sandbox rules

1. Start with `<!DOCTYPE html>` and include `<html>`, `<head>`, `<body>`, and
   `<meta name="viewport" content="width=device-width, initial-scale=1">`.
2. Load Tailwind only from `https://cdn.tailwindcss.com` and use the Zoom semantic-token drop-in
   from the brand guide for Zoom-facing pages.
3. External scripts, styles, and images may use only the pinned hosts below. Inline `<script>` and
   `<style>` are allowed.
4. Never emit `<iframe>`, `<object>`, `<embed>`, `<frame>`, `<frameset>`, `<base>`, or `<form>`.
5. Never use `postMessage`, `parent`, `top`, `opener`, browser storage, cookies, workers,
   `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `sendBeacon`, `BroadcastChannel`, or
   `MessageChannel`.
6. Pick one module system per document. With UMD React, use a plain `<script>` block.
7. Write authored labels and headings in English.
8. Keep `slots`, `parameter`, `mock_data`, and placeholder names identical and restricted to
   `^[A-Za-z0-9_]+$`.

## Pinned CDN allowlist

Allowed hosts are `cdn.jsdelivr.net`, `esm.sh`, `unpkg.com`, and `cdn.tailwindcss.com`.

- Tailwind Play: `https://cdn.tailwindcss.com`
- React 18 UMD: `https://cdn.jsdelivr.net/npm/react@18.2.0/umd/react.production.min.js`
- ReactDOM 18 UMD: `https://cdn.jsdelivr.net/npm/react-dom@18.2.0/umd/react-dom.production.min.js`
- PropTypes UMD: `https://cdn.jsdelivr.net/npm/prop-types@15.8.1/prop-types.min.js`
- Recharts UMD: `https://cdn.jsdelivr.net/npm/recharts@2.12.7/umd/Recharts.min.js`
- Framer Motion UMD: `https://unpkg.com/framer-motion@11.3.19/dist/framer-motion.js`
- Lucide UMD: `https://cdn.jsdelivr.net/npm/lucide@0.439.0/dist/umd/lucide.min.js`
- D3 UMD: `https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js`

If a library is not listed, use Tailwind and inline SVG instead of inventing a URL.

## Data injection

The renderer performs only flat `${name}` and `$name` substitution for identifiers matching
`[A-Za-z_][A-Za-z0-9_]*`. It does not evaluate a template language.

- Never emit Velocity/Jinja directives, dot paths such as `${user.name}`, filters, calls,
  arithmetic, or ternaries inside placeholders.
- Every `${name}` must have one matching slot, parameter binding, and mock-data value.
- For lists, tables, branching, or computed display elements, inject a flat JSON string slot into
  an `application/json` island and render it with client-side JavaScript.
- Never use JavaScript template literals. Their `${...}` sequences are consumed as workflow slots;
  use string concatenation instead.
