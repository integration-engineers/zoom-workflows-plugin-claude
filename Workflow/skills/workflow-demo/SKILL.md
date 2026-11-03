---
name: workflow-demo
description: The pinned hero menu and first-try demos. Read from zoom-workflows or workflow-onboard.
---

# Workflow demo — the curated hero menu

Resolve `WORKFLOW_ROOT` as the absolute directory two levels above this `SKILL.md`
(`Workflow/`). Use it for bundled templates regardless of the user's working directory.

If the user explicitly selected a demo/template from the menu and wants its definition,
one-time test, or deployment, use `references/hero-fast-path.md` instead of
reading the rest of this menu. Return here only for a scenario-specific detail
that the selected manifest entry and fast path do not resolve.

This skill owns first-try examples and their pinned templates, in two layers: an instant win and
the broader menu. Use it for exploration, a requested demo, or a follow-up that explicitly selects
one of its examples. A fresh user requirement goes to `workflow-create`, even if a pinned
definition could be reused to implement it.

The line to `workflow-create` is **demo intent vs. the user's own automation requirement**.
Template similarity alone does not move a requirement into this demo skill.

## When they ask what this can do

The entry skill shows the shortcut menu. Then, in one line each, what you can do with a workflow once it exists:

- **Run** — try one once against their account, without publishing it
- **Deploy** — turn it on so it runs on its own trigger from then on
- **Manage** — list what they have, check whether a run fired, and turn one off

Two things to get right when rendering this:

- **Say the licence plainly.** A user who finds out about ZoomMate only after choosing is worse off
  than one who saw it in the table. Mark the paid rows, don't bury it.
- **Offer anything off-menu too.** The table is what ships pinned; the builder handles a custom
  automation on request, so close by saying so rather than implying the list is the limit.

Only entries returned by `--quick-menu` appear in this table.

## Packaged catalog and shortcut menu

`<WORKFLOW_ROOT>/hero-templates/manifest.json` lists five `shortcuts`. Four name one template;
"send meeting summary" names one template per destination. Every template `hero_context.py`
returns is live; offer exactly what it returns.

Every delivery hero targets the user themselves: their inbox, DM, docs, phone, or their own
Salesforce opportunities. The horoscope is an on-demand result for the user and has no send or
publish node.

## Layer 1 — the first win (license-free)

The fastest path to "oh, this actually works": meeting summaries and action items after every
meeting. It is one scenario with one template per destination, so the only question is where they
want it. Slack asks which channel and Confluence which space; the others need nothing beyond
connecting the app.

**Have one concrete offer ready, and size it to the question.** A full menu makes someone choose
before they believe any of it works, so when an offer is warranted, make it this one: *"After each of
your meetings, I can email you the summary and action items automatically — free, no credits. Want me
to set that up?"* The rest of the menu is what "what else" is for.

How much room that offer gets depends on what was asked:

- **They asked to set up an automation** — this is the answer. Give the offer and stop for a reply.
- **They asked something broader that Zoom answers in other ways too** ("what can you do with my
  meetings", "what can you do") — automation is *one* of the answers, not the answer. Other
  capabilities — reading a past meeting, its recording, its transcript, searching across meetings —
  are equally valid replies and belong in the same response. Contribute a sentence and leave the
  rest of their answer intact; taking the whole reply hides options the user asked about.

The test: if the user could reasonably have meant something a sibling capability does right now,
you are contributing, not answering.

Ask which destination unless they named one, then use that destination's pinned template.
Setting it up deploys it (`../workflow-core/references/lifecycle.md`); a request only to try it
runs a test without deploying. The Gmail and Outlook templates are zero-config: the recipient binds
to `{{ROOT.sysWorkflowCreator.email}}`, which the backend resolves to the workflow owner at run
time, and both send without a confirmation card. Neither uses AI or costs credit.

Connecting the mailbox is the one prerequisite. Say so in the same breath as the offer — a consent
screen the user was told about reads as setup; the same screen unannounced reads as a failure.

Deploy it as `../workflow-core/references/lifecycle.md` describes, naming the recipient and the
real effect of the deployed trigger.

## Layer 2 — role-tailored expansion (on "what else?")

When the user has seen a win and keeps engaging — "what else can it do", "anything for my role" —
tour the richer heroes. From `<WORKFLOW_ROOT>/hero-templates/manifest.json`:

| # | Template | 3P | Asks the user for |
|---|---|---|---|
| 2 | Meeting chat → Slack | Slack | nothing |
| 3 | Meeting reminders: Phone Call, Gmail, Outlook, Zoom Chat, or Slack | depends on channel | which channel; a phone number for Phone Call |
| 4 | Customer meetings → Salesforce opportunity update | Salesforce | nothing |
| 5 | Work-Style Horoscope from recent Zoom activity | — | nothing |

All four are ZoomMate and list 10 credits per run. Someone whose meetings run on in-meeting chat wants #2;
someone who keeps missing meeting starts wants #3; a seller who updates the CRM by hand wants #4.

**#5 is on demand.** Its shortcut prompt follows `references/hero-fast-path.md`: deploy the
pinned definition (a manual-trigger button), then run it once. Otherwise load the pinned
`zoom-zodiac.json` rather than compiling a replacement when the user asks for a zodiac-inspired
work-style reflection. Its manual trigger runs one Deep Reasoning node over the workflow creator's own
three most recent meetings, using their meeting summaries, recordings, and transcripts. The output is four sentences,
or a plain no-activity result when no meetings are found. The workflow does not create an
image or HTML card or send a message, and deploying it saves a button rather than a recurring trigger. When the user asks to save it as a button they can
press later, deploy this same pinned manual-trigger definition; test and deploy are distinct live
operations.

**#3 reminds the user fifteen minutes before each meeting** on the channel they pick. Phone Call
places a voice call that reads out the meeting title. It calls only the user's own phone, verified in
their Zoom account (Zoom Profile → Phone); ask for that number and its calling code before deploying
(`required_inputs`) and never reuse a number from elsewhere. Gmail, Outlook, Zoom Chat
and Slack send the meeting essentials: overview, invitees, agenda, preparation checklist, and join link.

**#4 reads each completed meeting and updates the matching Salesforce opportunity.** It skips
meetings that are not sales meetings. After a successful update, it DMs the user what changed. It
needs the Salesforce connector authorized.

**#2 forwards each meeting's chat to the user in Slack** after the meeting ends. The chat is read
from the Zoom Chat channel named after the meeting topic. It needs the Slack connector authorized.

**Once the user asks to save or turn on a hero, deploy its pinned template right here.** The five
shortcut prompts ask for both deploy and one run; follow `references/hero-fast-path.md`.
For a request to try
one once, use the test operation with that same definition. For #5, deploy saves a manual-trigger
workflow; it does not create a recurring trigger. Only hand off to `workflow-create` if
the user states a new automation requirement rather than continuing with the selected demo.

## Template-first, always

A hero deploys from its pinned JSON — it does not go through generation. That's the whole point: what
the user sees must work, so it can't depend on a generate step landing. Don't hand-generate a substitute and
present it as the pinned hero. Scope every deployed workflow by *rule* ("the most recent meeting
in this series"), never a hardcoded meeting ID.

## Tone

Light and quick — this is often a first impression. "Your Zoom recordings," not "meeting assets."
If something breaks, one sentence on what's next.
