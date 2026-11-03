---
name: workflow-inspect
description: Audit and diagnose the user's existing Zoom Workflows. Read from zoom-workflows.
---

# Workflow inspect — audit & diagnose

Operate on what already exists. Two jobs, both read-only: list, get definition, activities, and
get execution. Read `../workflow-core/references/lifecycle.md` for the tools, how to reach them on
this connection, and what each status means. A fix (re-running, resuming, reconnecting, or
updating) is a separate request the user makes after hearing the cause.

## Audit

List the user's deployed workflows and report plainly: which are live vs draft, what each triggers
on, and where each writes. Flag the common waste — duplicates that both fire, a draft the user thinks
is running, a workflow writing to a channel nobody watches.

## Diagnose an automation that didn't run

When the message points at something in the past that was expected and didn't arrive,
it's a diagnosis — not a build. Rebuilding hides the fault, leaves the broken one installed, and once
both are live the user gets everything twice. Hold off on offering a replacement until the cause is
known, or the user asks outright.

Work down this list; stop at the first thing that explains the symptom:

1. **Does it exist and is it published?** An undeployed or DRAFT workflow never fires — the single
   most common cause.
2. **Did it run at all?** Check execution history for the expected window. No execution → the
   trigger; a failed execution → a node.
3. **Waiting on a person?** `HITL_PENDING` means it ran and stopped for approval the user may not
   have given.
4. **Waiting on a connector?** `business_status=PENDING_AUTH` on a run means an app connection
   lapsed mid-run. Name the app and what reconnecting involves, and stop there. Re-running is a
   separate decision with real side effects — the user came to find out what happened, not to fire
   the workflow again.
5. **Ran but delivered nowhere useful?** Compare the write target in the definition against where the
   user was looking. Wrong channel and wrong recipient look identical to "didn't run".
6. **Paused on credit/license?** A `PENDING_CREDIT` (or "additional credits or a license upgrade")
   status means the run stopped at the credit/entitlement gate — it is not a resumable approval and
   `resume` does not fix it.
7. **Was there anything to act on?** A digest over a week with no matching meetings produces nothing
   — that's correct behavior, not a failure. Say so plainly.

Report what you found in plain language and name the specific fix. If it's a definition problem,
offer to change that workflow in place; on a yes, continue in `workflow-create`, which follows
`workflow-core`'s update procedure for the workflow you inspected, so no second copy is created. If none of the list explains it, say so directly rather than
guessing; ask for the exact date and what the user expected, then re-check that window.
