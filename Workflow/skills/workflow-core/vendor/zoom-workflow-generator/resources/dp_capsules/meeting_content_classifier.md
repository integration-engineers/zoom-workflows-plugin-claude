---
name: meeting_content_classifier
description:
  Classify and check whether one Zoom trigger-supplied meeting is non-empty, has usable summary or
  transcript content, and satisfies the user's explicit sales, customer, external, interview,
  support, or other content and participant eligibility rules before downstream actions. Emit a
  typed match result so writes and deliveries run only on the qualifying path. This capsule is
  read-only and never performs the downstream side effect itself.
version: "1.0"
tags:
  - meetings
  - classification
  - eligibility
  - workflow_planner
required_tools: []
---

# Meeting Content Classifier

## Purpose

Decide whether one trigger-supplied meeting satisfies the workflow request's explicit eligibility
rules before any downstream write or delivery runs. This step is a read-only entry gate. It does not
call tools, update records, create artifacts, send messages, or deliver notifications.

## Required input

Use the complete meeting object bound by the workflow trigger. Evaluate only fields and content that
are actually present in that object, including summary/transcript content, topic, host, participants,
and meeting metadata. Never fetch a different meeting or infer unavailable facts.

## Classification procedure

1. Read the exact eligibility and skip rules in the task-specific execution contract.
2. Check data usability first. An absent/non-object meeting, or a meeting without the content the
   request requires, does not match. For a summary-dependent workflow, require usable summary
   content; for transcript analysis, require usable transcript or equivalent supplied content.
3. Apply every user-requested content rule. Examples include sales/deal, interview, support,
   customer-success, incident, or project-review criteria. Require grounded evidence in the meeting
   topic, summary, transcript, or metadata; keywords alone are not sufficient when the surrounding
   content contradicts the classification.
4. Apply participant rules only when the user explicitly requested them. For an external-meeting
   rule, require grounded participant/account evidence that at least one relevant attendee is
   external. Do not silently turn a sales/content rule into an external-attendee rule, and do not use
   `is_internal` by itself to reject grounded customer or deal content unless external attendance is
   an explicit requirement.
5. If every explicit rule is satisfied, set `matched=true` and return a compact
   `meeting_context` containing only the grounded evidence and identifiers the downstream step needs.
   If any rule fails or remains ambiguous, set `matched=false`, explain the no-action reason in
   `response`, and leave `meeting_context` empty.

## Output contract

- `response` (string): concise classification result and grounded reason.
- `matched` (boolean): true only when the meeting has usable required content and satisfies every
  explicit eligibility rule.
- `meeting_context` (string): compact grounded classification evidence for the matched meeting;
  empty when `matched=false`.

## Guardrails

- Read-only: no tool calls and no side effects.
- Preserve the user's rule exactly; never add a stricter participant, account, or content filter.
- Ambiguous eligibility is a no-action result, not permission to write.
- Do not select a customer/account/opportunity, assignee, recipient, or external record here. Those
  resolutions belong to the gated downstream step and must follow that step's own uniqueness rules.
- A downstream write must be connected through a deterministic condition on `matched isTrue` and
  must bind `meeting_context`. It should also bind the original meeting object when it needs the
  full summary, transcript, participants, or metadata.
