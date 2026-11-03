---
name: zoom_chat
description: "Use for every Zoom Chat operation. WRITE: send DM, post to channel, reply, create channel, add users to channel, mute/unmute channel, archive/unarchive channel. READ: search messages, fetch channel history (a meeting's in-meeting chat is a Zoom Chat channel named after the meeting topic), list my mentions, list my sent. Triggers: DM, message, post, reply, create channel, add to channel, mute, archive, find chat, mentions of me, catch up."
version: "2.0"
tags:
  - zoom_chat
  - workflow_planner
required_tools:
  - zm.aic.tool.resolve_entity
  - zm.aic.tool.search_chat
  - zm.aic.tool.fetch_messages_by_session_and_time
  - zm.system.resource.unified_search
  - zm.tc.channel.create_chat_channel_node
  - zm.tc.channel.add_people_to_channel_node
  - zm.tc.channel.team_chat_channel_mute_status_update
  - zm.tc.channel.team_chat_channel_archive_status_update
  - zm.tc.channel.team_chat_channel_members_get
  - zm.tc.channel.team_chat_channel_mention_groups_get
  - zm.tc.message.send_message_to_person_node
  - zm.tc.message.send_message_to_channel
  - zm.tc.message.reply_message
  - zm.tc.message.team_chat_msg_mention_me_fetch
  - zm.tc.message.team_chat_msg_sent_list
  - zm.tc.message.team_chat_msg_deep_links_get
  - zm.tc.message.team_chat_session_deep_links_get
---

# Zoom Chat

## Purpose

Covers every Zoom Chat interaction the planner can take. Single-turn, two phases per flow: ANALYSIS (read / resolve only) -> EXECUTION (one write per target; check the response).

- Write: DM (C), channel post (D), reply (E), create channel (F), add users (H), mute/unmute channel notifications (I), archive/unarchive channel (J).
- Read: search (A), channel history (B), my mentions / my sent / replies to my sent messages (G).

Core principle: resolve before act. Always pass system objects from `resolve_entity`; never pass raw name strings into write tools.

Phase discipline: ANALYSIS values must come from prior read tools. ANALYSIS uses no write tools. EXECUTION uses only the listed write tools, with the verify-on-ambiguous reads in Global Write Protocol as the only exception.

Dependent reads are sequential. Do not call a tool whose parameters depend on a `resolve_entity` result in the same action batch as that resolver call. First call `resolve_entity`, wait for its observation, then call the next tool with the observed value. A cached ID, inferred ID, raw channel name, or ID from a previous task is invalid.

Exact channel token rule: when the user provides a channel token starting with `#`, remove only the leading `#` and surrounding punctuation before `resolve_entity`. Preserve the full remaining channel name exactly, including prefixes, timestamps, underscores, hyphens, and numeric suffixes. Never shorten `#TC_CUST_COMPLEX_..._onboarding-wave_07` to `onboarding-wave_07`, never split on `_` or `-`, and never invent a friendlier alias. This rule applies to every channel-scoped flow: B, D, E, F, G, H, I, and J.

## Routing

Evaluate top-to-bottom; first match wins.

| Signal | Flow |
|---|---|
| First-person mentions of the caller, no third-party sender filter: "mentions of me", "where was I mentioned", "@me", channel/window scope allowed | G.1 - My Mentions |
| First-person messages the caller sent + reply status: "did my messages get replies", "whether messages I sent in #x have replies", "any replies to my sent messages" | G.3 - Replies to My Sent Messages |
| First-person messages the caller sent: "what have I sent today", "my sent", channel/window scope allowed | G.2 - My Sent |
| Explicit search/find intent, even when a channel is named: "find/search messages", "message containing TOKEN", "find the message around epoch ms ...", "use the chat search/search_chat path", or requests for exact sender/timestamp/content of a matching message | A - Search Messages |
| A named channel plus a concrete topic/status/risk/owner/deadline/progress/blocker/decision/SLA/legal/finance/sales/support question, including role-style requests like "what did HR/admin/IT/sales say in #channel about TOKEN" | B.2 - Channel-Scoped Topic Lookup |
| Anything else involving message search without a usable channel scope: third-party sender/mention, topical/keyword search, or mixed filters | A - Search Messages |
| Channel name + "recent / latest / catch up" with no person/topic filter | B - Fetch Channel History |
| Person name or email + content to send | C - Send Direct Message |
| "mute/unmute #<channel>" notification preference, with no duration | I - Manage Channel Notifications |
| "archive/unarchive #<channel>" | J - Update Channel Archive Status |
| "reply to" + message ID + reply text | E - Reply to Message |
| Channel name + content to post | D - Send Channel Message |
| "create a channel" + optional people + optional message | F - Create Channel |
| "add <people> to #<channel>" for an existing channel | H - Add Users to Existing Channel |

G fallback rule: if the user names a third-party sender, or applies a filter G.1 / G.2 / G.3 cannot express through `session_id` / time / `limit` / `sort`, use Flow A instead.

Read lock: Flows A, B, and G are read-only. No write tool may be called in a read flow.

Unsupported surface: this skill has no file upload/share, message reminder, scheduled-send, contact invitation / external contact acceptance, or timed mute duration write tool in `required_tools`. If the user asks for one of those operations, say the operation is unsupported by the available Zoom Chat tools and name the missing capability. Do not approximate it by posting a normal channel message, searching for a document link, or claiming that a file/reminder/schedule/timed mute was completed.

Timed mute rule: `team_chat_channel_mute_status_update` supports only immediate `mute` / `unmute`, with no duration or expiration parameter. If the user asks to mute "until tomorrow", "for 1 hour", "during focus time", or any other timed mute, do not call the write tool. Explain that timed mute is unsupported by the available schema and that only indefinite mute/unmute can be performed.

## Flow A: Search Messages

Guardrail: Flow A is for explicit message search, unscoped search, participant-scoped global chat search, and exact-message lookup by token/time. If the user explicitly says to find/search messages, find a message containing a token, use the chat search path, or return exact sender/timestamp/content for a matching message, call `search_chat` first even when a channel is named.

If the request only names a concrete channel and asks about a topic, status, risk, owner, deadline, progress, blocker, decision, SLA, legal item, finance item, sales item, support item, or other role-specific update without explicit search/find wording, route to Flow B.2 instead. Global `search_chat` can return compressed cross-product summaries from other channels or systems; those are not valid evidence for a channel-scoped topic answer.

ANALYSIS:

| Step | Field | Source |
|---|---|---|
| A1 | `query` | User message. If a person is named with no topic, pass the person's name as query. |
| A2 | `participant_names` | User message. |
| A3 | `participant_emails` | `resolve_entity(user, names=A2)` -> `user_email` per row when names are not emails. |
| A4 | `start_time` / `end_time` | User message, format `YYYY-MM-DD HH:MM:SS` when specified. |
| A5 | `channel_name` | Optional, only when the user named a channel and asks for exact sender/timestamp/content or gives an epoch-ms window. |
| A6 | `channel` | `resolve_entity(channel, names=[A5])` only after `search_chat` if exact content needs channel verification. |

EXECUTION:

1. `search_chat(query=..., participants=A3, start_time=..., end_time=..., sort_by_time="desc")`; omit unspecified fields. Use `"asc"` for chronological review.
2. If 0 results: `unified_search(search_by_nl=true, search_query=<original_with_time_phrase>, source=["chat"])`.
3. When the user requests exact sender/timestamp/content, copy exact fields only from tool observations. Never expand a token-only result, rewrite sender names, round timestamps, or invent content from the query.
4. If `search_chat` returns only a compressed excerpt/token or the full message content is not present, and A5 is available, resolve the channel and call `fetch_messages_by_session_and_time(sessions=["<resolved channel_id exactly as returned>"], time=<nearest Flow B bucket>)`; filter the returned channel messages by the exact token/query and timestamp window. Use the Flow B resolved-id-then-bare fallback only if the fetch fails.
5. If exact content still cannot be verified from a tool observation, say that the search found the token but full exact content was not available. Do not label inferred or partial text as "Exact content".

## Flow B: Fetch Channel History

ANALYSIS:

| Step | Field | Source |
|---|---|---|
| B1 | `channel_name` | User message; ask "Which channel?" if missing. |
| B2 | `channel` | `resolve_entity(channel, names=[B1])` -> `{channel_id, channel_name}`. |
| B2-session | `fetch_session_id` | Use `B2.channel_id` exactly as returned by the resolver. Do not strip or append a domain before the first fetch attempt. |
| B3 | `time` bucket | One of `720`, `1440`, `4320`, `10080`, `43200`. Default `720`. |

Bucket mapping: recent/last hour/unspecified -> `720`; today/last 24h -> `1440`; last few days/2-3 days -> `4320`; this week/last week/7 days -> `10080`; this month/30 days -> `43200`.

Never pass arbitrary minute counts. Round up to the nearest bucket and mention the rounding.

EXECUTION: `fetch_messages_by_session_and_time(sessions=["<B2.channel_id exactly as resolved>"], time=B3)`. `sessions` is `list[str]`, not objects. The session value may be a full channel JID or a bare channel id; prefer the resolved value first because it is environment-correct.

If `fetch_messages_by_session_and_time` returns an error string such as "Retrieve message from channel failed" or otherwise does not return messages, retry this read once with the same resolved session id and same bucket. If the resolved id contains `@` and the retry still fails, make one fallback read with the bare id formed by stripping everything from `@` onward. If the original bucket was `720` and all same-bucket attempts fail, make one final channel-scoped attempt with `time=1440` using the same resolved-id-then-bare fallback order. Do not replace failed channel history with unscoped `search_chat` results; unscoped search is not evidence for the named channel. If all channel fetch attempts fail, say that the channel evidence could not be retrieved and stop the read flow.

### B.2 Channel-Scoped Topic Lookup

Use this sub-flow when the user names a channel and asks about a concrete topic, token, customer issue, role update, status, risk, owner, deadline, progress, blocker, decision, SLA, legal item, finance item, sales item, support item, HR/admin/IT update, or cross-role action in that channel.

ANALYSIS is the same as B1/B2/B2-session/B3. For B.2 topic/status lookup, default to `1440` for "today" and `10080` when no time phrase is present; a no-time topic query should cover at least one week to maximize the chance of satisfying the user's information need. Keep Flow B's plain "latest/catch up" default at `720`.

EXECUTION:

1. Resolve the channel first. Do not batch `resolve_entity(channel)` with `search_chat`.
2. Call `fetch_messages_by_session_and_time(sessions=["<B2.channel_id exactly as resolved>"], time=<bucket>)`.
3. Apply the fetch retry rule above if the channel fetch fails.
4. Filter only the returned messages from that channel for the requested topic/token/role words. Answer from those returned messages, preserving exact token(s), sender(s), timestamps, and snippets.
5. Do not cite `search_chat` or `unified_search` results as evidence for B.2. If the requested topic is not present in the channel fetch result, answer that no matching channel message was found in the fetched window and include the window/bucket used.

Answer from the returned messages. Include the count and a sender/time/excerpt list, preserving exact customer identifiers, issue IDs, project tokens, decision markers, links, or status words that appear in the message text. Do not summarize away those identifiers in channel-history/catch-up answers; they are evidence that the correct channel and window were fetched.

For channel history, a grouped summary alone is invalid. Always include a "Raw excerpts" or equivalent list with exact snippets copied from returned messages. If the returned message text contains identifiers such as `ISSUE-...`, `PROJ-...`, `PROJECT-...`, `DECISION-...`, `ATTN-...`, `MENTION-...`, `LINK-...`, `SLA-...`, or their numeric variants like `ISSUE500-...`, preserve the full identifier exactly. Never shorten a full identifier to only its prefix (`DECISION500`, `LINK500`, etc.). At least three full identifiers from returned messages should appear verbatim in a history/catch-up answer when available.

## Flow C: Send Direct Message

Single-recipient DM. Success is `data.output.message_id`.

ANALYSIS:

| Step | Field | Source |
|---|---|---|
| C1 | `recipient_name` | User message. Multiple targets require separate requests. |
| C2 | `user` object | `resolve_entity(user, names=[C1])` -> `{user_id, user_name, user_email}`. Pass all three fields verbatim. |
| C2-self | self DM | For self references, resolve via the caller's User Name from Current Context (see `resolve_entity` override for `names` input rules — display name, not email). Ask if context lacks User Name. |
| C3 | `message_content` | User message. Apply Markdown Formatting. Do not mention the recipient in a DM body. |

External-recipient guard: an email outside the caller's account is still just a normal C2 resolve attempt. Proceed only when `resolve_entity` returns a row with all three required keys (`user_id`, `user_name`, `user_email`). If the external email is not resolved, stop before any write and say the available tools cannot DM that external user because the contact/user cannot be resolved. If the send tool fails with a contact/friend/precondition error, report that the DM was not sent and that establishing the external contact relationship is unsupported by this skill's current tools; do not retry or send a channel message instead.

EXECUTION:

Call `send_message_to_person_node` with `user={user_id, user_name, user_email}` and non-empty `message_content`. Success iff `state == "COMPLETED"` and `data.output.message_id` is present. On failed/invalid response, do not retry.

## Flow D: Send Channel Message

ANALYSIS:

| Step | Field | Source |
|---|---|---|
| D1 | `channel_name` | User message. |
| D2 | `channel` | `resolve_entity(channel, names=[D1])` -> `{channel_id, channel_name}`. |
| D3 | `message_content` | User message. Apply Markdown Formatting. |
| D3-resolve | mention/link IDs | Resolve people, channels, and mention groups only when the body clearly intends to address/notify/link them. |
| D3-deeplink | deep link URLs | Use deep-link tools only on explicit share/link/reference intent. |

Mention intent is by meaning, not by characters. Mention on literal `@name`, vocative addressing, direct asks, urgency, or targeted call-to-action. Skip for descriptive third-person reporting. When in doubt, skip.

Vocative addressing includes a display name at the start of a message followed by a comma and a request, for example "Alice, please review..." or "Example User, pay attention...". For those direct asks, resolve the person and replace the display name in the sent body with the resolved mention tag. Sending only the plain display name is invalid.

EXECUTION:

1. Build the body by substituting resolved references into D3.
2. `send_message_to_channel(to={channelId: <D2.channel_id exactly as resolved>, channelName: <D2.channel_name>}, msg=<body>)`. Use `msg`, not `msgMarkdown`; this matches the execute-node tool schema. Full channel JIDs and bare ids are both accepted by this tool, so do not strip the resolver value.

## Flow E: Reply to Message

ANALYSIS:

| Step | Field | Source |
|---|---|---|
| E1 | `message_id` | User message. |
| E2 | `channel_name` | User message. |
| E3 | `channel` | `resolve_entity(channel, names=[E2])` -> `{channel_id, channel_name}`. |
| E4 | `reply_content` | User message. Apply Markdown Formatting and mention/deep-link resolution as in D. |

EXECUTION: `reply_message(messageId=<E1>, msg=<body>, to=<E3.channel_id exactly as resolved>)`. Full channel JIDs and bare ids are both accepted by this tool, so do not strip the resolver value.

## Flow F: Create Channel

Creates an empty channel seeded with the caller. Members and an initial message are chained only when requested.

ANALYSIS:

| Step | Field | Source |
|---|---|---|
| F1 | `channel_name` | User message. |
| F1-check | name collision check | `resolve_entity(channel, names=[F1])`; if a match returns, stop. |
| F2 | follow-up `member_names` | User message. Optional. Drop "me" and the caller's own name. |
| F2-resolve | member preflight | `resolve_entity(user, names=F2)` when F2 is non-empty. Stop if all fail. |
| F3-self | caller `user` | Resolve the caller via `resolve_entity(user, names=[<User Name from Current Context>])` (see `resolve_entity` override for `names` input rules). Required keys: `user_id`, `user_name`, `user_email`. |
| F3-fallback | caller fallback | If the caller resolve returns `not_found` or lacks `user_id`, stop before create — do NOT fall back to email (email is not a valid `names` input). |
| F4 | `message_content` | Optional. Apply D3-resolve. New channels have no mention groups. |

External-member guard: for "create a channel with external user <email>", treat the email as a member in F2. It must resolve to a complete `{user_id, user_name, user_email}` row before create. Do not fabricate a user object from an email or from a user ID in the prompt. If the external user cannot be resolved, stop before creating the channel unless the user explicitly asked to create it even without that member. This skill has no contact-invitation / external-contact-acceptance tool, so it cannot bootstrap missing external contacts.

EXECUTION:

1. Stop if F1-check matched.
2. Stop if F2 was non-empty and F2-resolved is empty.
3. Call `create_chat_channel_node(channel={channel_name: <F1>, is_public: false}, users=[<F3-self>])` exactly once; never call it with an empty or partial user object. Capture `channel_id` / `channel_name`. If the call fails or no `channel_id` is returned, stop and do not retry.
4. `team_chat_session_deep_links_get(sessions=[{session_id: <channel_id>}])`; skip on failure.
5. If F2-resolved is non-empty, chain Flow H with `channel` from step 3 and `users=F2-resolved`.
6. If F4 exists, call `send_message_to_channel(to={channelId: <channel_id exactly as returned>, channelName: <channel_name>}, msg=<F4>)`.

## Flow G: My Inbox / Personal Feed

Read-only first-person flows with optional channel and time filters.

| Sub | Tool | Default window | Pagination |
|---|---|---|---|
| G.1 My Mentions | `team_chat_msg_mention_me_fetch` | all-time | `limit` |
| G.2 My Sent | `team_chat_msg_sent_list` | last 24h, max 30-day span | `hasMore` + `next_end_timestamp` |
| G.3 Replies to My Sent Messages | Channel-scoped: `fetch_messages_by_session_and_time`; unscoped: `team_chat_msg_sent_list` | channel-scoped default `1440` minutes | channel-scoped none; unscoped uses sent-list pagination |

ANALYSIS:

- Resolve channel scope via `resolve_entity(channel, names=[channel_name])` only when the user names a channel. Omit `session_id` entirely when no channel is named.
- The resolved `channel_id` is authoritative. For tools that require a JID, pass the resolved `channel_id` exactly as returned, including its domain. Never hardcode an environment-specific XMPP domain; development and production may differ. Never replace, append, or normalize a domain unless that exact domain came from the resolver, Current Context, or a prior tool response in the same environment.
- Channel-scoped G calls must pass `session_id=<resolved channel_id>` exactly to the read tool. Do not fetch all sessions and filter afterward; that can miss the target channel under pagination.
- Channel-scoped G.1 starts as a two-step read: action step 1 resolves the channel; action step 2 calls `team_chat_msg_mention_me_fetch` with the observed resolved JID. Never batch the resolver and mention fetch together. Never call mention fetch with a raw channel name or an ID not present in the resolver observation for this request.
- For "in the last 24 hours" / "past 24h", set `start_timestamp = nowMs - 86_400_000` and omit `end_timestamp` only when Current Context explicitly provides a numeric `nowMs` / `epoch ms` value.
- Never invent epoch milliseconds from a calendar date, ISO timestamp, or human-readable "Current time" string. Do not do 13-digit timestamp arithmetic in the reasoning unless the numeric `nowMs` was provided verbatim by Current Context. If no trustworthy numeric `nowMs` is available, omit the timestamp and state that the result was not safely narrowed to 24h.
- Convert time phrases into UTC epoch ms only from an authoritative numeric `nowMs`. Day boundaries are anchored at the user's local midnight.
- If the user supplies an explicit UTC epoch-ms range such as `1778989813813:1778989813815`, `start_timestamp=1778989813813 end_timestamp=1778989813815`, or "between timestamp X and Y", pass those exact integer values to G.1/G.2 tools that accept timestamp fields. Do not reinterpret them as dates, seconds, minutes, or local wall-clock strings.
- For open-ended windows like today, last N hours/days, this week, this month, or since a date, omit `end_timestamp`; the server fills current time.
- For closed past windows such as yesterday or explicit date ranges, pass both `start_timestamp` and `end_timestamp`.
- G.1 `limit` defaults to 20 and must be <= 100. `sort` is `"desc"` or `"asc"`.
- For "last N hours", including "last 2 hours", set `start_timestamp = nowMs - N * 3_600_000` and omit `end_timestamp` when Current Context provides numeric `nowMs`. For "yesterday", pass both local-day bounds: yesterday `00:00:00.000` local as `start_timestamp` and yesterday `23:59:59.999` local as `end_timestamp`.
- For "today", `start_timestamp` must be local `00:00:00.000` for the current date and `end_timestamp` must be omitted. Never round `nowMs` down to the current hour; a "today" start timestamp whose local time is not midnight is invalid.
- For "this week", use the current local calendar week start at `00:00:00.000` and omit `end_timestamp`. For "last 7 days" / "past 7 days", use seven days ago at local `00:00:00.000`; do not collapse these phrases into the same timestamp.
- G.2 channel-scoped "what did I send" / "my sent" is also a two-step channel read. Resolve the channel first. For open-ended recent/current windows (`last 24 hours`, `today`, `this week`, `last N days`, `since ...`), call `fetch_messages_by_session_and_time(sessions=["<resolved channel_id exactly as returned>"], time=<bucket>)`, then filter returned messages where sender is the caller/current user and the content matches any requested topic/token. Use the Flow B resolved-id-then-bare fallback only if the fetch fails. For closed past windows (`yesterday`, `on <past date>`, `between <date1> and <date2>`) or explicit epoch-ms ranges, do **not** use a bucket because buckets cannot express the closed range; instead call `team_chat_msg_sent_list(session_id=<resolved channel_id exactly as returned>, start_timestamp=<closed start>, end_timestamp=<closed end>, need_deep_link=true)` and filter the returned sent rows by the requested topic/token. Do not use `search_chat`, `unified_search`, or `llm_tool` for channel-scoped G.2 when the channel is named.
- G.3 does not call a reply write tool. For a named channel, use `fetch_messages_by_session_and_time` with the resolved channel id exactly as returned and the nearest Flow B bucket. Use the Flow B resolved-id-then-bare fallback only if the fetch fails. This avoids unscoped sent-list pagination and avoids hand-computed epoch mistakes for "last 24 hours".

EXECUTION:

- G.1: `team_chat_msg_mention_me_fetch(session_id=<resolved channel_id exactly as returned>, start_timestamp=..., end_timestamp=..., limit=..., sort=..., need_deep_link=true)`. Do not stop after resolving the channel; the fetch call is required before answering. Answer "yes" only from returned mention rows for that exact `session_id`; do not infer a mention from the user request, from unscoped mention results, or from messages in a different channel.
- G.1 answer source of truth: use the mention tool's raw structured fields, especially `data[].threads[].thread_content`, `thread_timestamp`, `thread_sender_name`, `thread_sender_user_id`, `thread_message_id`, and `metadata.deep_link`. Do not paraphrase from the human-readable observation summary if it omits prefixes or identifiers. For every returned row matching the requested topic/token, include sender, timestamp, and the exact `thread_content` string verbatim.
- G.1 exact-content rule: preserve the complete leading identifier/token exactly as it appears in `thread_content`, including seed-like prefixes such as `MULTI-...`, `MENTION-...`, `DECISION-...`, `PROJECT-...`, `ISSUE-...`, `SENT-...`, or `REPLY-...`. Never shorten `MULTI-SAMPLE-001-SENDER-TAYLOR-MENTION-EXAMPLE @Example User ...` to just `@Example User ...`. Never infer sender from words inside the message body; if the body says "from Sample Sender" but the returned sender field says "Example User", report the returned sender field and preserve the exact body text.
- G.2 channel-scoped open-ended windows: `fetch_messages_by_session_and_time(sessions=["<resolved channel_id exactly as returned>"], time=<bucket>)`, then filter returned messages by current-user sender and requested topic/token. Include exact matching message excerpts and full identifiers in the answer.
- G.2 channel-scoped closed past windows: `team_chat_msg_sent_list(session_id=<resolved channel_id exactly as returned>, start_timestamp=<closed start>, end_timestamp=<closed end>, need_deep_link=true)`, then filter returned messages by requested topic/token. If no sent rows match, answer no/none for that exact closed window and do not cite messages from today or another window.
- For G.2 channel-scoped answers, the final answer must preserve the complete matched message text or at least the complete leading identifier/token exactly as it appears in the fetched message. If the user supplied an identifier such as `MCPREAL-...`, `ISSUE-...`, `PROJECT-...`, `SENT-...`, or `REPLY-...`, do not omit it from the answer even when also providing a human summary.
- G.2 unscoped: `team_chat_msg_sent_list(start_timestamp=..., end_timestamp=..., need_deep_link=true)`.
- G.3 channel-scoped: `fetch_messages_by_session_and_time(sessions=["<resolved channel_id exactly as returned>"], time=1440)` for "last 24 hours"; use the nearest Flow B bucket for other channel-scoped windows. Inspect returned threads where the sender is the caller/current user and `replies_total > 0` or `replies` is non-empty. Report both the count of sent messages inspected and the count with replies. Include reply previews when available. Do not call `team_chat_msg_sent_list` first, and do not call `llm_tool` for this filtering.
- For G.3 yes/no answers, include the exact inspected root-message identifier/token and, for positive cases, the exact reply identifier/token when present. Do not paraphrase away unique identifiers; they are evidence that the correct sent thread was inspected.
- G.3 unscoped: `team_chat_msg_sent_list(start_timestamp=..., end_timestamp=..., need_deep_link=true)`, then filter returned `threads` where `replies_total > 0` or `replies` is non-empty.
- For G.2 / G.3 pagination, if `hasMore == true`, call again with original `start_timestamp` and `end_timestamp = next_end_timestamp`.

Never pass `session_id=""`, `0`, or sentinels for unspecified fields. Never call `llm_tool` in Flow G; reply/mention filtering must be done directly from the returned structured fields. A Flow G answer that uses `llm_tool` is invalid even if the final answer text is correct.

## Flow H: Add Users to Existing Channel

Resolve -> check existing members -> batch-add only new users.

ANALYSIS:

| Step | Field | Source |
|---|---|---|
| H1 | `channel_name` | User message or upstream Flow F. |
| H2 | `member_names` | User message; non-empty. Drop "me" and caller's own name. |
| H3 | `channel` | `resolve_entity(channel, names=[H1])`; reuse Flow F channel when chained. |
| H3-bare | `bare_channel_id` | Strip everything from `@` onward from `H3.channel_id` for `add_people_to_channel_node` only. |
| H3-jid | `channel_jid` | Use `H3.channel_id` as-is if it already contains `@conference`. If only a bare id is available, do not guess a domain; use the bare id only for tools that accept bare ids, or re-resolve/fetch metadata to obtain a JID. |
| H4 | `users` | `resolve_entity(user, names=H2)`; reuse F2-resolved when chained. Drop not-found names and stop if all dropped. |
| H5 | existing members | `team_chat_channel_members_get(channel_id=<H3-jid>, page_size=100)`; the tool does not accept a nested `channel` object. If this read fails, let add be idempotent. |
| H6 | `new_users` | H4 minus H5 by `user_id`. If empty, skip execution and report duplicates. |

External-member guard: adding an external user by email uses the same `resolve_entity(user)` preflight as internal users. Continue only if the resolver returns a full user object. If the resolver cannot find the external email, stop and say the available tools cannot add that external user because they cannot resolve or establish the external contact relationship. If `add_people_to_channel_node` returns failure, an empty add result, or no requested external user in `memberIds`, do one members read-back; if the external user is still absent, report that the add did not complete. Do not claim success from a successful channel create alone.

EXECUTION: `add_people_to_channel_node(channel={channel_id: <H3-bare>, channel_name: <H3.channel_name>}, users=<H6>)`.

## Flow I: Manage Channel Notifications

Mutes or unmutes one or more channel notification settings for the caller. This flow does not post a message into the channel.

ANALYSIS:

| Step | Field | Source |
|---|---|---|
| I1 | `action` | User intent. `mute` for mute/silence notifications; `unmute` for unmute/resume notifications. |
| I2 | `channel_names` | User message. One or more channels, maximum 10. Ask which channel if missing. |
| I3 | `channels` | `resolve_entity(channel, names=I2)` -> `{channel_id, channel_name}` for each channel. |
| I3-bare | `channel_ids` | For each resolved channel, strip everything from `@` onward. The mute tool expects UUID/bare channel IDs, not full JIDs. |
| I4 | `duration` | User message. If any duration or expiration is requested, stop: timed mute is unsupported by the available tool schema. |

EXECUTION:

1. Stop before writing if I4 is present. Say the available mute tool supports only immediate indefinite mute/unmute and has no duration field.
2. Call `team_chat_channel_mute_status_update(channel_ids=[<I3-bare>...], action=<I1>)` exactly once for up to 10 channels.
3. Success iff `status == true`, `errorCode == 0`, and `result.failed_channels` is empty or omitted. If `failed_channels` is non-empty, report partial failure by channel name where possible.

## Flow J: Update Channel Archive Status

Archives or unarchives one or more channels. Requires the caller to have owner/admin/archive permission.

ANALYSIS:

| Step | Field | Source |
|---|---|---|
| J1 | `action` | User intent. `archive` for archive; `unarchive` for unarchive/restore/reopen. |
| J2 | `channel_names` | User message. One or more channels, maximum 10. Ask which channel if missing. |
| J3 | `channels` | `resolve_entity(channel, names=J2)` -> `{channel_id, channel_name}` for each channel. |
| J3-bare | `channel_ids` | For each resolved channel, strip everything from `@` onward. The archive tool expects UUID/bare channel IDs, not full JIDs. |
| J4 | `condition` | User message. If the user says to archive after confirming completion, no blockers, sign-off, closure, or another condition, fetch channel history before writing and evaluate the condition from returned evidence. |

EXECUTION:

For unconditional archive/unarchive requests, call `team_chat_channel_archive_status_update(channel_ids=[<J3-bare>...], action=<J1>)` exactly once for up to 10 channels. Success iff `status == true`, `errorCode == 0`, and `result.failed_channels` is empty or omitted. If `failed_channels` is non-empty, report partial failure by channel name where possible. If the tool returns an access-denied or permission failure, explain that archiving requires owner/admin/channel-admin permission.

For conditional archive requests, first call `fetch_messages_by_session_and_time(sessions=["<J3.channel_id exactly as resolved>"], time=43200)` for each channel, using the Flow B resolved-id-then-bare fallback if the fetch fails. Archive only when the returned evidence clearly satisfies the condition. Stop without writing when messages show active blockers, pending legal/QA/sign-off, progress below 100%, postponed pilots, rejected enablement, unresolved issues, or insufficient evidence. The answer must say whether the archive was performed or skipped and cite the exact evidence token/snippet that drove the decision. Do not archive a channel merely because the user phrased the condition optimistically.

## Global Protocols

### Tool Reference

| Tool | Used by | Input shape |
|---|---|---|
| `resolve_entity(entity_type="channel")` | B, D, E, F, H, I, J | bare names |
| `resolve_entity(entity_type="user")` | A, C, F, H, body user mentions | display names (NOT emails — emails return not_found) |
| `search_chat` | A | query/participants/time |
| `unified_search` | A fallback | NL query with `source=["chat"]` |
| `fetch_messages_by_session_and_time` | A/B/B.2/G.2/G.3/J | `sessions: [resolved_channel_id]`, `time: bucket`; fallback to bare id only after a fetch failure |
| `team_chat_channel_mention_groups_get` | D/E/F | channel_id |
| `team_chat_msg_deep_links_get` | C/D/E | `[{message_id, message_timestamp, session_id}]` |
| `team_chat_session_deep_links_get` | C/D/E/F | `[{session_id}]` |
| `team_chat_msg_mention_me_fetch` | G.1 | see G |
| `team_chat_msg_sent_list` | G.2/G.3 | see G |
| `send_message_to_person_node` | C | `user` object + `message_content` |
| `send_message_to_channel` | D/F | `to={channelId: <resolved_channel_id>, channelName: <name>}` + `msg` <= 500 chars |
| `reply_message` | E | `messageId`, `msg`, `to=<resolved_channel_id>` |
| `create_chat_channel_node` | F | `channel` object + `users` list |
| `add_people_to_channel_node` | H | `channel={channel_id:<bare_channel_id>, channel_name}` + `users` list |
| `team_chat_channel_mute_status_update` | I | `channel_ids=[bare_channel_id...]`, `action="mute"` or `"unmute"` |
| `team_chat_channel_archive_status_update` | J | `channel_ids=[bare_channel_id...]`, `action="archive"` or `"unarchive"` |
| `team_chat_channel_members_get` | H | `channel_id=<channel_jid>`, `page_size<=100` |

Channel ID rule: resolved IDs are immutable and environment-specific. If a resolver returns `abc@conference.<env-domain>`, copy that exact value into tools that need or accept a JID, including `send_message_to_channel.to.channelId`, `reply_message.to`, `team_chat_msg_mention_me_fetch.session_id`, `team_chat_msg_sent_list.session_id`, `team_chat_channel_members_get.channel_id`, and the first attempt for `fetch_messages_by_session_and_time.sessions`. Never hardcode or translate domains between dev (`xmppdev`) and prod (`xmpp`). Strip everything from `@` onward only for the tools that have been live-tested to need bare ids: `add_people_to_channel_node.channel.channel_id`, `team_chat_channel_mute_status_update.channel_ids`, and `team_chat_channel_archive_status_update.channel_ids`. For `fetch_messages_by_session_and_time`, use the resolved id first and fall back to bare only if the fetch fails.

Primary resolve failure stops the flow. Multiple matches: use the first and note the match count.

### Timestamp Handling

Flow B `time` is minutes. Flow G timestamps are UTC epoch milliseconds. Do not mix units.

Read `nowMs` from Current Context when present: take the integer immediately after `epoch ms:` in the `## Current Context` `Current time` line. Do not derive it from the human-readable date string. Manual 13-digit epoch arithmetic can silently produce year-off errors, such as using a 2025 timestamp when the current eval date is 2026; the server may still return data that looks plausible. Day boundaries use the user's local timezone. G.2 `team_chat_msg_sent_list` defaults to `start_timestamp = server nowMs - 24h` and `end_timestamp = server nowMs` when timestamps are omitted, and silently caps spans at 30 days. For G.2 windows longer than 30 days, split into <=30-day calls or report that only the last 30 days are shown.

Silent-failure prevention:

- Do not pass `start > end` or `start == end`.
- `start == end` returns empty results for both G.1 and G.2. Treat equal timestamps as invalid input, not as an exact-point lookup.
- For `team_chat_msg_sent_list`, `start > end` can silently fall back to the last 24 hours instead of returning empty data. Treat this as a dangerous false-positive path: validate timestamp order before the call, especially for `yesterday`, `today`, and explicit epoch-ms ranges.
- Do not pass milliseconds to Flow B `time`.
- Do not pass minutes/seconds to `*_timestamp`.
- Do not use UTC midnight for local date phrases.
- Do not send empty strings for optional fields.
- For open-ended G windows, omit `end_timestamp` because the server fills its own authoritative nowMs, which may be later than client/context nowMs. Do not compute and pass an end timestamp unless the phrase is a closed past window or a pagination call requires `next_end_timestamp`.

Hard-failure prevention:

| Trigger | Tool | Result |
|---|---|---|
| `sort` not exactly `"desc"` or `"asc"` | `team_chat_msg_mention_me_fetch` | hard failure (`result=2`) |
| `limit > 100` or `limit == 0` | `team_chat_msg_mention_me_fetch` | hard failure (`result=2` or `result=1`) |
| `session_id=""` | G.1 / G.2 | hard failure (`session_id is not allowed to be empty`) |
| omitted `sessions` or omitted `time` | `fetch_messages_by_session_and_time` | HTTP 500 / code 5003 |
| `time <= 0` or empty/bogus `sessions` | `fetch_messages_by_session_and_time` | `result=1` or no usable data |

### Markdown Formatting

Default: do not format. Apply only deterministic/high-confidence rules.

Syntax:

| Effect | Syntax |
|---|---|
| Bold | `*text*` |
| Italic | `_text_` |
| Strikethrough | `~text~` |
| Monospace | `` `text` `` |
| Block quote | `> text` |
| Mention all | `<!all>` |
| Color | `<color:#RRGGBB|text>` |
| Datetime | `<date:ms>` / `<time:ms>` / `<datetime:ms>` |

Deterministic outgoing-message formatting:

- Wrap shell commands in monospace wherever they appear, including after verbs like "run", "execute", "use", or "try"; for example send the words `run \`npm test\`` rather than `run npm test`.
- Common command starters include `npm`, `git`, `kubectl`, `docker`, `pip`, `ssh`, `curl`, `make`, `bash`, and `python`.
- Wrap filesystem paths such as `/var/log/app.log`, `./scripts/check.py`, `~/Downloads/report.csv`, and `C:\temp\run.log` in monospace.
- Wrap filenames with technical extensions in monospace: `.py`, `.js`, `.ts`, `.md`, `.yaml`, `.yml`, `.json`, `.sh`, `.conf`, `.log`, `.sql`, `.html`, `.css`, `.ini`, `.toml`, and `.env`.
- Wrap UUIDs or hex hashes of 12 or more characters in monospace.
- Wrap issue/PR/ticket refs in monospace when the marker is explicit, such as `PR #123`, `issue #456`, `bug #789`, `MR #12`, or `PROJECT-123`.
- Wrap standalone HTTP `4xx` and `5xx` status codes in monospace.
- Convert future natural-language times with an explicit hour to `<datetime:ms>` only when the timezone is clear. Skip vague or timezone-ambiguous times.
- Preserve user-supplied `*bold*`, `_italic_`, `~strikethrough~`, and `` `monospace` `` exactly.
- Bold high-confidence status outcomes such as shipped, merged, released, deployed, passed, done, complete, blocked, failed, cancelled, or rejected. Use green/red color only when the success/failure direction is unambiguous.
- Bold high-confidence urgency words such as urgent, P0, P1, critical, outage, or down.
- Use block quote only for explicit attributed quotes such as `said:` or `Quoting:`. Do not block-quote the user's own ordinary message text.
- Wrap pasted multi-line stack traces, JSON, or log excerpts in monospace/code formatting.
- Do not decorate the whole message, apply color outside status outcomes, mention users on hedged language, or apply monospace to ordinary prose.
- If the user asks for "bot message syntax" or similar, these formatting rules must be present in the `msg` / `message_content` passed to the send tool, not only in the final explanation.

JID construction:

| Element | Form | Source |
|---|---|---|
| `user_jid` | `{user_id}@<environment XMPP domain>` | `resolve_entity(user).user_id` plus the XMPP domain from Current Context or a prior tool response in this environment |
| `channel_jid` | use as-is | `resolve_entity(channel).channel_id`; never append or replace the domain |
| `mention_group_id` | use as-is | `team_chat_channel_mention_groups_get` row |

For user mentions, construct `user_jid` only after resolving the user ID and only with the environment-correct XMPP domain. Never hardcode an environment-specific XMPP domain. For channel links, do not construct a JID; copy the resolved channel ID exactly.

Resolved references:

| Effect | Syntax | Required call |
|---|---|---|
| Mention person | `<!{user_jid}|Display Name>` | `resolve_entity(user)` |
| Channel link | `<#{channel_jid}|#name>` | `resolve_entity(channel)` |
| Mention group | `<group:{mention_group_id}|name>` | `team_chat_channel_mention_groups_get` |

Mention by user JID only; never by email. If body-reference resolution fails, render as bold plain text and append a warning in the response. Primary resolve failure still stops the flow.

Deep links are used only on explicit link/share/reference intent. If a requested link cannot be resolved, render the reference as bold plain text and warn. Never invent URLs.

Length: `send_message_to_channel.msg` hard cap is 500 chars. Truncate at sentence boundaries and never cut a markup token.

### Global Write Protocol

- Each write runs at most once per target; never retry writes.
- A write call that returns `FAILED`, `invalid_request`, or a missing required field still counts as the one write for that target. Stop and report; do not try a repaired second write.
- Every write is preceded by its ANALYSIS reads.
- Response success field is authoritative. Only `add_people_to_channel_node` may use one read-back when the success field is missing.
- IDs are internal; do not surface them to the user.

| Write tool | Pre-write reads | Success field |
|---|---|---|
| `send_message_to_person_node` | `resolve_entity(user)` | `data.output.message_id` |
| `send_message_to_channel` | `resolve_entity(channel)` plus body refs | `msgId` |
| `reply_message` | `resolve_entity(channel)`; message ID from prior search/fetch | `msgId` |
| `create_chat_channel_node` | F1-check + F2-resolve + F3-self resolve | `channel_id` |
| `add_people_to_channel_node` | `resolve_entity(channel)` + `resolve_entity(user)` + members read | `result.memberIds` or `result == true` |
| `team_chat_channel_mute_status_update` | `resolve_entity(channel)` | `status == true`, `errorCode == 0`, and no `failed_channels` |
| `team_chat_channel_archive_status_update` | `resolve_entity(channel)` | `status == true`, `errorCode == 0`, and no `failed_channels` |

Missing success field: for add-people only, call members read once to compare actual vs requested. All others: say action may have completed but could not be confirmed; do not retry.

## Output Format

Use values from tool responses, never request payload values. Do not expose internal IDs.

| Outcome | Format |
|---|---|
| Search results | `Found <N> messages` + sender/time/excerpt list |
| Search 0 | `No messages found <with filters>` |
| Channel fetch | `#<channel> - last <bucket>` + count and list |
| Channel fetch 0 | `No messages in #<channel> in the last <bucket>` |
| Flow G | `<sub-flow> - <N> messages` + list with channel deep links when present |
| DM succeeded | `Sent DM to <user_name>` + 80-char preview |
| Channel post/reply succeeded | Success line + channel/recipient + 80-char preview + warnings |
| Channel created | `Channel <name> created.` + deep link if available + chained outcomes |
| Channel exists | `A channel named "<name>" already exists. Pick a different name and I'll create it.` |
| Flow H | `Added <N> user(s) to #<channel>: <names>` plus skipped/not-found lines |
| Flow I | `Muted #<channel>` or `Unmuted #<channel>`; include partial failures if any |
| Flow J | `Archived #<channel>` or `Unarchived #<channel>`; include permission/partial failures if any |
| Resolve failed | `<name> could not be found` |
| Tool error | Plain-language error |

## Examples

### Example 1 - Channel Send With Mention, Channel Link, and Mention Group

Input: `Post to #releases: @alice please review, see #engineering for context, also notify @release-managers group`

ANALYSIS:

- D1: `channel_name = "releases"`.
- D2: `resolve_entity(channel, names=["releases"])` returns `{channel_id: "rel_abc@conference.<env-xmpp-host>", channel_name: "releases"}`.
- D3-resolve:
  - `resolve_entity(user, names=["alice"])` returns `{user_id: "uAliceXyz", user_name: "Alice", user_email: "alice@example.com"}`.
  - Build `user_jid` as `uAliceXyz@<env-xmpp-host>` using the same XMPP host as channel IDs; channel JIDs add only the `conference.` prefix.
  - `resolve_entity(channel, names=["engineering"])` returns `{channel_id: "eng_xyz@conference.<env-xmpp-host>", channel_name: "engineering"}`. Use this channel ID as-is.
  - `team_chat_channel_mention_groups_get(channel_id="rel_abc@conference.<env-xmpp-host>")` returns a row `{mention_group_id: "grp_rm123", name: "release-managers"}`.

EXECUTION:

Body:

```text
<!uAliceXyz@<env-xmpp-host>|Alice> please review, see <#eng_xyz@conference.<env-xmpp-host>|#engineering> for context, also notify <group:grp_rm123|release-managers>
```

Tool call:

```text
send_message_to_channel(
  to={channelId: "rel_abc@conference.<env-xmpp-host>", channelName: "releases"},
  msg=<body>
)
```

Variant - mention group lookup empty: send `release-managers` as bold plain text in the body and warn that the group could not be mentioned.

Variant - plain information, no mention: input `Post to #releases: Alice's PR landed and the rollout is live` is third-person reporting, not a direct ask, so do not resolve or mention Alice.

### Example 2 - Create Channel, Add People, and Send Initial Message

Input: `Create #q2-launch with Alice and Bob and post "kickoff Monday"`

ANALYSIS:

- F1-check: `resolve_entity(channel, names=["q2-launch"])` returns no existing channel.
- F2-resolve: `resolve_entity(user, names=["Alice", "Bob"])` returns full user objects for Alice and Bob.
- F3-self: resolve the caller via `resolve_entity(user, names=[<User Name from Current Context>])` (see `resolve_entity` override for `names` input rules) and keep the full `{user_id, user_name, user_email}` object for `users`.

EXECUTION:

1. `create_chat_channel_node(channel={channel_name: "q2-launch", is_public: false}, users=[<caller_user>])` returns `{channel_id: "new_123@conference.<env-xmpp-host>", channel_name: "q2-launch"}`.
2. Chain Flow H for Alice and Bob. For `add_people_to_channel_node` only, strip the returned channel ID to `new_123` and call `channel={channel_id: "new_123", channel_name: "q2-launch"}`.
3. Send the initial message with the returned channel ID as-is: `send_message_to_channel(to={channelId: "new_123@conference.<env-xmpp-host>", channelName: "q2-launch"}, msg="kickoff Monday")`.

Do not reuse the stripped ID from step 2 for the initial channel post.

### Example 3 - Self Direct Message

Input: `DM me: deployment notes are ready`

ANALYSIS:

- C1 is a self-reference, so take the caller's User Name from Current Context rather than treating `me` as a name (or the email — see `resolve_entity` override for `names` input rules).
- `resolve_entity(user, names=["<User Name>"])` returns `{user_id, user_name, user_email}`.
- C3 body is `deployment notes are ready`; do not mention the recipient in the body.

EXECUTION:

```text
send_message_to_person_node(
  user={user_id: <resolved_user_id>, user_name: <resolved_user_name>, user_email: <resolved_user_email>},
  message_content="deployment notes are ready"
)
```
