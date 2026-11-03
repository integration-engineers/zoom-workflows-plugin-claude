---
name: zoom_chat_hourly_poll
description: "Read-only one-hour polling fallback for a Zoom Chat event request that no supported trigger covers, such as new messages in a named channel inside a digest that also watches other sources, or messages matching a keyword across chats. Reads a bounded Zoom Chat scope, applies the user's event criteria, and emits a typed match result for a separately gated downstream step. Use only after the Custom schedule trigger; never send, reply, react, pin, edit, or delete a message."
version: "1.0"
tags:
  - zoom_chat
  - polling
  - recent messages
  - read only
  - workflow_planner
required_tools:
  - zm.aic.tool.resolve_entity
  - zm.aic.tool.fetch_messages_by_session_and_time
  - zm.aic.tool.search_chat
  - zm.tc.message.team_chat_msg_deep_links_get
---

# Zoom Chat Recent-Message Poll

## Purpose and boundary

This capsule replaces an unavailable Zoom Chat event with a bounded read on each hourly schedule. It
is a detector only. It never performs the user's downstream delivery or write.

- Run only after `zm.system.scheduler.trigger.scheduler` configured to repeat every one hour.
- Treat the DP execution instant as the end of a half-open window: `[run time - 60 minutes, run
  time)`. Use each message's own sent timestamp, never a date mentioned in the message text. Take
  the run time from the epoch milliseconds of the current-time context, which are UTC, and compare in
  UTC; never convert the displayed local clock through its zone abbreviation, which can name more
  than one zone.
- Every read needs a hard Zoom Chat scope: one or more channels the request names, or an explicit
  keyword or phrase to search for. A request that watches every chat with no named channel and no
  keyword is not safely scoped and must have been clarified before compilation.
- The only allowed operations are the four read tools in this capsule. Never send, reply, react,
  pin, edit, forward, or delete a message, and never create or change a channel.

## Procedure

1. For each named channel, remove only a leading `#` and surrounding punctuation, keep the rest of
   the name exactly, and call `resolve_entity(channel, names=[<name>])`. Wait for the observation
   before any read that uses it. A channel that does not resolve to exactly one channel makes the read
   incomplete; never substitute a similar channel.
2. Read each resolved channel with
   `fetch_messages_by_session_and_time(sessions=["<resolved channel_id exactly as returned>"],
   time=720)`. `sessions` is a list of strings. If the read returns an error or no message list,
   retry once with the same id; if the id contains `@` and the retry fails, make one read with the
   bare id formed by stripping everything from `@` onward.
3. For a keyword or phrase with no named channel, call `search_chat(query=<the exact keyword or
   phrase>, start_time=<window start>, end_time=<run time>, sort_by_time="desc")`. With a named
   channel, filter that channel's messages by the keyword instead; unscoped search results are not
   evidence for a named channel.
4. Filter the observations to the exact half-open 60-minute window. Discard messages whose sent
   timestamp is missing or cannot be parsed; do not infer it from ordering. When the request watches
   other people's messages ("someone posts", "a teammate asks"), exclude messages the requester sent.
5. Apply only the user's stated matching criteria (sender, keyword, question, mention, attachment).
   Deduplicate results within this run by message id.
6. When the downstream step needs a link to a message, call `team_chat_msg_deep_links_get` for the
   matched messages only; never build a link by hand.
7. Emit `matched=true` only when at least one observed message survives both the time window and the
   requested criteria. Otherwise emit `matched=false` and an empty `matched_items` value.
8. Put only grounded fields needed by downstream work in `matched_items`, including each message id,
   channel name, and sent timestamp. Preserve sender, text, and link facts only when the request
   needs them.

## Failure and output contract

- An unresolved or ambiguous channel, a failed read after the retries above, a missing hard scope,
  or unparseable timestamps are not matches. Set `matched=false`, make no write, and explain the read
  failure compactly in `response`.
- `matched_items` is a compact machine-readable string containing the qualifying messages. It must
  be empty when `matched=false`.
- A downstream operation must be behind a deterministic `matched isTrue` condition and must bind
  `matched_items`. A no-match run ends without a downstream side effect.
