---
name: jira_recent_issue_poll
description: "Read-only one-hour polling fallback for a Jira issue event request that has no supported trigger. Searches a bounded Jira scope for issues created or assigned during the latest hourly window and emits a typed match result for a separately gated downstream step. Use only immediately after the Custom schedule trigger; never create, edit, assign, transition, comment on, or delete an issue."
version: "1.1"
tags:
  - jira
  - polling
  - recent issues
  - read only
  - workflow_planner
required_tools:
  - zm.connector_mcp.zm_jira.jira_get_current_user
  - zm.connector_mcp.zm_jira.jira_find_users
  - zm.connector_mcp.zm_jira.jira_search_for_issues_using_jql_post
  - zm.connector_mcp.zm_jira.jira_get_issue
---

# Jira Recent-Issue Poll

## Purpose and boundary

This capsule replaces an unavailable Jira event trigger with a bounded read on each hourly schedule.
It is a detector only. It never performs the user's downstream delivery or Jira write.

- Run only after `zm.system.scheduler.trigger.scheduler` configured to repeat every one hour.
- Treat the DP execution instant as the end of a half-open window: `[run time - 60 minutes, run
  time)`. Use Jira creation, update, and assignment-history timestamps, never dates mentioned in issue
  text.
- Every search needs a hard Jira scope. A stated project/filter is a scope. "Assigned to me", "my
  received tickets", or an otherwise unqualified "a Jira ticket/issue is received" or "assigned"
  request is scoped to the connector-authenticated Jira user. Resolve that user with
  `jira_get_current_user` before searching and use the returned Jira account id explicitly; never
  infer Jira identity from the workflow requester's Zoom profile. A named assignee must resolve to
  exactly one active Jira user before search. An explicitly tenant-wide request for newly created
  issues across unspecified projects is not safely scoped and must have been clarified before
  compilation.
- The only allowed Jira operations are the four read tools in this capsule. Never create, edit,
  assign, transition, comment on, watch, link, log work on, or delete an issue.

## Procedure

1. Resolve the Jira identity before any issue search:
   - for "me" or an otherwise unqualified received/assigned request, call
     `jira_get_current_user` and require one active Jira account with a non-empty account id;
   - for a named assignee, call `jira_find_users` and require exactly one active match;
   - do not claim a completed read when identity resolution is unavailable, ambiguous, or fails.
2. Translate the requested event without broadening it:
   - new/created issue: query issues created in the last hour within the grounded project, filter, or
     assignee scope;
   - assigned to me/my received issue, plus an unqualified received/assigned request: require current
     assignee equal to the resolved connector Jira account id and either initial assignment at issue
     creation or an assignee change to that same account in the last hour;
   - assigned to a named person: resolve exactly one Jira user, then require that assignee and an
     assignment change in the last hour.
3. For an assignment event, use a two-stage read contract:
   - call `jira_search_for_issues_using_jql_post` with the explicit resolved Jira account id and
     `updated >= <window-start>` only to retrieve bounded candidates; request `expand=changelog` and
     a non-empty `fields` array containing at least key, summary, assignee, created, and updated;
   - paginate until `isLast=true`; a missing terminal page or any business/transport error makes the
     read incomplete even when the outer tool call reports success;
   - for each candidate, inspect the expanded changelog. If the search result omits a complete
     changelog, call `jira_get_issue` for that key with `expand=changelog`;
   - accept a candidate when either one changelog item changes the assignee to the resolved account id
     inside `[run time - 60 minutes, run time)`, or the issue was created inside that window already
     assigned to the resolved account and its complete changelog contains no assignee transition. An
     empty changelog alone is insufficient without the in-window creation timestamp and matching
     current assignee. `updated` is a candidate selector only and is never assignment proof.
4. For a created event, call `jira_search_for_issues_using_jql_post` with non-empty bounded JQL and a
   non-empty minimum `fields` array, paginate to `isLast=true`, and enforce the half-open window from
   the returned creation timestamps.
5. Apply only the user's stated project, issue type, status, label, text, or assignee criteria.
   Deduplicate results within this run by Jira issue key.
6. Set `read_succeeded=true` only after identity, query acceptance, pagination, and required history
   checks all complete. Emit `matched=true` only when `read_succeeded=true` and at least one observed
   issue satisfies the event, window, and all stated criteria. A successful complete zero-result read
   uses `read_succeeded=true`, `matched=false`, and an empty `matched_items` value.

## Failure and output contract

- Zero or multiple user resolutions, missing hard scope, unsupported event history, authorization
  failure, connector failure, a business-error payload, incomplete pagination, or an incomplete time
  window are unverified reads, not successful no-match results. Set `read_succeeded=false` and
  `matched=false`, make no write, and begin `response` with `Outcome: PARTIAL` or `Outcome: FAILED`.
- A verified complete read with no qualifying issues sets `read_succeeded=true`, `matched=false`, and
  begins `response` with `Outcome: NO_ACTION`.
- `matched_items` is a compact machine-readable string containing grounded qualifying issue fields.
  It must be empty when `matched=false`. Never invent a Jira tenant URL from an issue key.
- A downstream operation must be behind a deterministic `matched isTrue` condition and must bind
  `matched_items`. A no-match run ends without a downstream side effect.
