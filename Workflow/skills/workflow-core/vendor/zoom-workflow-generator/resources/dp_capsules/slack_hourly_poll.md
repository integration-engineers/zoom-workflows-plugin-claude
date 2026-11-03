---
name: slack_hourly_poll
description: "Read-only one-hour polling fallback for new Slack channel messages when there is no supported Slack message trigger. Detect matching messages and expose typed fields for a separately gated delivery; never post, reply, edit, schedule, or delete."
version: "1.0"
tags:
  - slack
  - polling
  - channel history
  - read only
  - workflow_planner
required_tools:
  - zm.connector_mcp.zm_slack.slack_find_user_channels
  - zm.connector_mcp.zm_slack.slack_fetch_conversation_history
---

# Slack Hourly Channel Poll

This step detects new messages in a channel the request names. It never delivers the resulting
digest or performs any Slack write. Run only after a Custom schedule repeating every hour.

1. Derive the half-open window `[run time - 60 minutes, run time)` from the epoch milliseconds
   on the current-time context line. Convert its boundaries to UTC Unix seconds for the Slack
   history tool's `oldest` and `latest` inputs. Do not convert through a local timezone
   abbreviation or use a timestamp mentioned in message text.
2. Resolve the user's named channel with `slack_find_user_channels` in the connected account.
   Accept only one unique exact normalized label. Use its returned provider ID for the history
   read; never substitute a similar channel. If the request names no channel, ask at authoring
   rather than polling every channel.
3. Call only `slack_fetch_conversation_history` for that ID, with bounded page size and the
   window boundaries. Follow a returned cursor until the window is covered or no page remains.
   Require `ok=true` on each page; outer tool success alone is insufficient. Deduplicate by
   message timestamp and keep only provider timestamps inside the half-open hour.
4. Apply only the user's stated keyword, sender, or content criteria. Put grounded message
   timestamp, sender, text excerpt, and channel in `matched_items` only as needed by the
   downstream step. Never invent an unread message or a sender.

Return `matched=true` only when a complete read found at least one qualifying message. A
complete read with none returns `matched=false`, empty `matched_items`, and a concise
response. Any channel ambiguity, authorization failure, pagination gap, tool error, or
unparseable timestamp returns `read_succeeded=false`, `matched=false`, empty
`matched_items`, and a concise reason in `response`. In a multi-source chain, complete
with those typed values so another healthy source can still be delivered and the failure
reported. Never call a Slack send, schedule, reply, edit, react, or delete tool.
