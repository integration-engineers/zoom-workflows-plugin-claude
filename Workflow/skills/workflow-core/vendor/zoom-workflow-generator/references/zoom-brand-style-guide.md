# Zoom Brand & Style Guide (Workflow HTML)

Brand foundation, design tokens, and component rules for on-brand Zoom HTML
reports — dashboards, meeting recaps, summaries, and other **read-first** pages
rendered by the HTML Render node.

Grounded in Zoom's production design system (`@zoom/react-ui`). Adapted for the
sandbox: **everything here is self-contained** — Tailwind Play CDN + inline
`<style>`/`<script>` only. No `@zoom/react-ui` import, no Google Fonts, no build
step, no network. Paste the drop-in block once and write normal Tailwind
utilities with Zoom token names.

---

## 0. Drop-in setup (paste into `<head>`, once)

This declares the Zoom semantic tokens as (a) CSS variables that flip for dark
mode and (b) Tailwind Play color aliases, so `bg-fill-primary`,
`text-text-stronger-neutral`, `border-border-subtle-neutral`, etc. work exactly
like they do in the product.

```html
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    darkMode: 'class',
    theme: { extend: {
      fontFamily: { sans: ['-apple-system','BlinkMacSystemFont','Segoe UI','Roboto','Helvetica Neue','Arial','Noto Sans','sans-serif'] },
      colors: {
        'bg-default':'var(--bg-default)','bg-neutral':'var(--bg-neutral)','bg-darker-neutral':'var(--bg-darker-neutral)',
        'fill-default':'var(--fill-default)','fill-subtler-neutral':'var(--fill-subtler-neutral)','fill-subtle-neutral':'var(--fill-subtle-neutral)','fill-neutral':'var(--fill-neutral)',
        'fill-subtler-primary':'var(--fill-subtler-primary)','fill-primary':'var(--fill-primary)','fill-primary-hover':'var(--fill-primary-hover)',
        'fill-subtler-error':'var(--fill-subtler-error)','fill-error':'var(--fill-error)',
        'fill-subtler-warning':'var(--fill-subtler-warning)','fill-warning':'var(--fill-warning)',
        'fill-subtler-success':'var(--fill-subtler-success)','fill-success':'var(--fill-success)',
        'text-neutral':'var(--text-neutral)','text-strong-neutral':'var(--text-strong-neutral)','text-stronger-neutral':'var(--text-stronger-neutral)',
        'text-primary':'var(--text-primary)','text-error':'var(--text-error)','text-warning':'var(--text-warning)','text-success':'var(--text-success)',
        'border-subtle-neutral':'var(--border-subtle-neutral)','border-neutral':'var(--border-neutral)',
        'border-subtle-primary':'var(--border-subtle-primary)','border-primary':'var(--border-primary)',
        'inverse-default':'var(--inverse-default)'
      }
    } }
  };
</script>
<style>
  :root {
    --bg-default:#fff; --bg-neutral:#fcfdfd; --bg-darker-neutral:#f1f4f6;
    --fill-default:#fff; --fill-subtler-neutral:#f7f9fa; --fill-subtle-neutral:#f1f4f6; --fill-neutral:#686f79;
    --fill-subtler-primary:#f2f8ff; --fill-primary:#0d6bde; --fill-primary-hover:#2057b1;
    --fill-subtler-error:#fff2f5; --fill-error:#da1639;
    --fill-subtler-warning:#fff9f2; --fill-warning:#b36200;
    --fill-subtler-success:#f2fff6; --fill-success:#247f40;
    --text-neutral:#686f79; --text-strong-neutral:#555b62; --text-stronger-neutral:#2a2b2d;
    --text-primary:#0d6bde; --text-error:#da1639; --text-warning:#b36200; --text-success:#247f40;
    --border-subtle-neutral:#dfe3e8; --border-neutral:#939ba4;
    --border-subtle-primary:#a8ccf8; --border-primary:#4b96f1;
    --inverse-default:#ffffff;
    --radius:0.5rem;
    --shadow-sm:0 4px 8px 0 #00000014,0 2px 4px 0 #00000014;
    --shadow-md:0 12px 24px 0 #00000014,0 6px 12px 0 #00000014;
  }
  .dark {
    --bg-default:#131619; --bg-neutral:#1d1e20; --bg-darker-neutral:#040506;
    --fill-default:#222325; --fill-subtler-neutral:#2a2b2d; --fill-subtle-neutral:#313235; --fill-neutral:#939ba4;
    --fill-subtler-primary:#1a2a52; --fill-primary:#599ef2; --fill-primary-hover:#2057b1;
    --fill-subtler-error:#54171a; --fill-error:#ff6682;
    --fill-subtler-warning:#4d2d0e; --fill-warning:#c28030;
    --fill-subtler-success:#123019; --fill-success:#48ad67;
    --text-neutral:#939ba4; --text-strong-neutral:#dfe3e8; --text-stronger-neutral:#f7f9fa;
    --text-primary:#599ef2; --text-error:#ff6682; --text-warning:#c28030; --text-success:#48ad67;
    --border-subtle-neutral:#313235; --border-neutral:#686f79;
    --border-subtle-primary:#213c77; --border-primary:#0d6bde;
    --inverse-default:#131619;
  }
  @media (prefers-color-scheme: dark) { :root:not(.light-forced) { color-scheme: dark; } }
</style>
```

Then: `<body class="font-sans bg-bg-neutral text-text-stronger-neutral">`. For a
dark report, add `class="dark"` to `<html>`. Default (no class) = light.

> **Opacity modifiers won't work** on these tokens (`bg-fill-primary/50` → no
> effect) because the values are hex, not `rgb(... / <alpha-value>)`. Need a
> tint? Use a dedicated `subtler` token or an arbitrary `bg-[#0e72ed1f]`.

---

## 1. Brand foundation

- **Zoom Blue is the brand.** One confident blue carries the page; everything
  else is neutral grey. Blue = brand moments, primary action, key metric accent,
  links, section markers. Don't spray it everywhere — a report is mostly calm
  neutrals with blue doing the pointing.
- **Brand hues** (marks & hero accents only):
  | Hex | Role |
  |---|---|
  | `#0E72ED` | **Zoom Blue** — the recognizable brand hue (logo lockup, hero accent) |
  | `#0B5CFF` | Logo gradient blue — only inside the Zoom logo mark / gradients |
  | `#0d6bde` | `fill-primary` — the AA-safe solid blue for buttons/fills on white (product default) |
- **Voice for report copy:** clear, warm, direct. Say what happened and what's
  next. No hype, no filler. Titles are plain nouns ("Meeting Recap", "Weekly
  Pipeline"), not slogans.
- **Logo:** only render a Zoom logo if the upstream data provides one. Never
  invent, recolor, or stretch it. Reports usually need no logo — a kicker label
  + title is enough.

---

## 2. Color tokens (semantic)

Use the **token names** (via the drop-in), not raw hex, so light/dark just work.
Raw values shown for reference / inline SVG fills.

**Surfaces & text** (light → dark):
| Token | Role | Light | Dark |
|---|---|---|---|
| `bg-neutral` | page background | `#fcfdfd` | `#1d1e20` |
| `fill-default` | card / panel surface | `#ffffff` | `#222325` |
| `fill-subtler-neutral` | zebra row, subtle panel | `#f7f9fa` | `#2a2b2d` |
| `fill-subtle-neutral` | table header, chips | `#f1f4f6` | `#313235` |
| `text-stronger-neutral` | headings, primary text | `#2a2b2d` | `#f7f9fa` |
| `text-strong-neutral` | body text | `#555b62` | `#dfe3e8` |
| `text-neutral` | muted labels, timestamps | `#686f79` | `#939ba4` |
| `border-subtle-neutral` | dividers, card border | `#dfe3e8` | `#313235` |

**Accent & status** (`fill-*` = solid, `text-*` = on light surface, `fill-subtler-*` = tint bg):
| Meaning | `fill` (L / D) | `text` (L / D) | tint bg `fill-subtler` (L / D) |
|---|---|---|---|
| Primary | `#0d6bde` / `#599ef2` | `#0d6bde` / `#599ef2` | `#f2f8ff` / `#1a2a52` |
| Success | `#247f40` / `#48ad67` | `#247f40` / `#48ad67` | `#f2fff6` / `#123019` |
| Warning | `#b36200` / `#c28030` | `#b36200` / `#c28030` | `#fff9f2` / `#4d2d0e` |
| Error | `#da1639` / `#ff6682` | `#da1639` / `#ff6682` | `#fff2f5` / `#54171a` |

Categorical / chart accents (data series, tags — pick in this order):
`#0E72ED` blue → `#9053C2` purple → `#007C7C` teal → `#FF5F0F` orange →
`#B36200` amber → `#247F40` green. All from the Zoom palette.

**Rules**
- Never pure black text — darkest text is `#2a2b2d`. Never pure `#000` fills.
- Status color = meaning, not decoration. Don't paint a neutral KPI red.
- One accent hue dominates a page. Multiple accents only when encoding distinct
  categories (chart series, tag types).

---

## 3. Typography

System font stack (no web-font load in the sandbox — this is the exact stack
`@zoom/react-ui` ships): set once via `font-sans` on `<body>`.

**Scale** (screen, read-first):
| Role | Size / line-height | Weight | Utility |
|---|---|---|---|
| Page title (H1) | 28px / 1.25 | 700 | `text-3xl font-bold` |
| Section (H2) | 20px / 1.3 | 600 | `text-xl font-semibold` |
| Sub-section (H3) | 16px / 1.4 | 600 | `text-base font-semibold` |
| Body | 14px / 1.6 | 400 | `text-sm` |
| Small / muted | 12px / 1.5 | 400 | `text-xs text-text-neutral` |
| Kicker label | 12px uppercase, `tracking-wider` | 600 | `text-xs font-semibold uppercase tracking-wider text-text-primary` |
| Metric number | 30–36px / 1.1 | 700 | `text-4xl font-bold` |

- Headings in `text-stronger-neutral`, body in `text-strong-neutral`, meta in
  `text-neutral`.
- Headings carry more top than bottom margin (e.g. `mt-8 mb-3`) so the following
  block reads as attached.
- Code/mono: `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`, 13px,
  on `fill-subtle-neutral`.
- **CJK copy:** bump body line-height to 1.7; don't `break-all`; long CJK titles
  may drop to 24px.

---

## 4. Space, radius, elevation

- **Spacing scale** (Tailwind default, 4px base): `1 2 3 4 6 8 12 16` →
  `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`px. Stay on it.
- **Card padding:** 24px desktop (`p-6`), 16px tight/mobile (`p-4`).
- **Section gap:** 24–32px (`space-y-6` / `space-y-8`). **Card gap in grids:** 16px (`gap-4`).
- **Radius:** `--radius` = `0.5rem` (8px). Cards/buttons `rounded-lg`, chips/badges `rounded-md`, pills `rounded-full`.
- **Elevation:** reports are flat-first. Use `border border-border-subtle-neutral` to
  separate cards, not shadow. Reserve `shadow-sm` (`--shadow-sm`) for one
  floating element (e.g. a sticky header) at most. No heavy shadows, no glows.

---

## 5. Components (report building blocks)

**Page shell**
```html
<body class="font-sans bg-bg-neutral text-text-stronger-neutral">
  <main class="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-10">…</main>
</body>
```
`max-w-3xl` (768px) for recap/summary reading; `max-w-5xl` for dashboards.

**Header** — kicker + title + meta (skip if no context to show):
```html
<header class="mb-8">
  <p class="text-xs font-semibold uppercase tracking-wider text-text-primary">Meeting Recap</p>
  <h1 class="mt-1 text-3xl font-bold text-text-stronger-neutral">${reportTitle}</h1>
  <p class="mt-2 text-sm text-text-neutral">${meetingDate} · ${attendeeCount} attendees</p>
</header>
```

**Card** — the default container:
```html
<section class="rounded-lg border border-border-subtle-neutral bg-fill-default p-6">…</section>
```

**Stat / KPI tile** — accent the number, label it quietly:
```html
<div class="rounded-lg border border-border-subtle-neutral bg-fill-default p-6">
  <p class="text-xs font-semibold uppercase tracking-wider text-text-neutral">Action Items</p>
  <p class="mt-2 text-4xl font-bold text-text-stronger-neutral">${actionItemCount}</p>
  <p class="mt-1 text-xs text-text-success">▲ 3 vs. last meeting</p>
</div>
```
Grid them: `grid grid-cols-2 gap-4 sm:grid-cols-4`.

**Callout** — left border in a status color + tint background:
```html
<div class="rounded-lg border-l-4 border-fill-warning bg-fill-subtler-warning p-4">
  <p class="text-xs font-semibold uppercase tracking-wider text-text-warning">Decision Needed</p>
  <p class="mt-1 text-sm text-text-strong-neutral">${calloutBody}</p>
</div>
```

**Badge / tag** — small, tinted, status-colored:
```html
<span class="inline-flex items-center rounded-md bg-fill-subtler-success px-2 py-0.5 text-xs font-medium text-text-success">Completed</span>
```

**Button / link** (reports rarely need buttons; links are common). No `<form>`.
```html
<a href="${detailUrl}" class="inline-flex items-center rounded-lg bg-fill-primary px-4 py-2 text-sm font-semibold text-inverse-default hover:bg-fill-primary-hover">View details</a>
<a href="${detailUrl}" class="text-sm font-medium text-text-primary hover:underline">Open in Zoom →</a>
```

**Data table** — header on `fill-subtle-neutral`, subtle row borders, optional zebra:
```html
<table class="w-full border-collapse text-sm">
  <thead>
    <tr class="bg-fill-subtle-neutral text-left text-text-strong-neutral">
      <th class="px-4 py-2 font-semibold">Owner</th><th class="px-4 py-2 font-semibold">Task</th><th class="px-4 py-2 font-semibold">Status</th>
    </tr>
  </thead>
  <tbody>
    <tr class="border-b border-border-subtle-neutral"><td class="px-4 py-2">…</td>…</tr>
  </tbody>
</table>
```
Keep tables ≤4–5 columns; on narrow widths prefer stacked cards.

---

## 6. Read-first layout patterns

**Dashboard** — glanceable, metric-led. KPI tile row up top, then charts/tables.
`max-w-5xl`, `grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3`. Lead with
the number that matters; blue accents the hero metric only.

**Meeting recap** — narrative, scannable. `max-w-3xl`, single column, generous
`space-y-8`: Summary → Key decisions (callouts) → Action items (table/list with
owner + due) → Attendees. Kicker "Meeting Recap".

**Report / summary** — document-like. `max-w-3xl`, clear H1/H2 hierarchy, tables
and callouts to break up prose. TL;DR callout at top when the report is long.

For all three: front-load the conclusion, keep one accent, let whitespace carry
the structure.

---

## 7. Charts

Charts need real component state → use **Recharts UMD** or **D3 UMD** (both on
the allowlist). Apply the brand series order from §2. Axes/grid in
`text-neutral`/`border-subtle-neutral` values; never rainbow. Prefer one bold
blue series + neutral comparison series. Keep chart chrome minimal — no heavy
gridlines, no 3D, no drop shadows. Label directly over legends when few series.

---

## 8. Anti-patterns

- Rainbow palettes / an accent per card. One blue leads; status colors mean
  status; extra hues only encode categories.
- Pure black (`#000`) text or fills.
- Heavy shadows, glows, gradients on content cards (gradients only inside a Zoom
  logo mark).
- Opacity modifiers (`/50`) on the hex tokens — silently no-op. Use a `subtler`
  token or arbitrary `#rrggbbaa`.
- Web-font `<link>` to Google Fonts (blocked by the allowlist) — use the system
  stack.
- Dense tables (>5 cols) on a narrow report — stack into cards.
- Decorative accent color on a metric that isn't actually good/bad.
- Inventing a logo, sender, or footer the data didn't provide.
- Walls of centered text — center only titles/hero KPIs; body stays left.
```
