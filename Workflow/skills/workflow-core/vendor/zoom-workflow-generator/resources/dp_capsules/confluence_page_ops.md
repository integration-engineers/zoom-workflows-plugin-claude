---
name: confluence_page_ops
description: "Creates, updates, reads, searches, and inspects Confluence pages and wiki content using the remote Confluence connector. Handles page creation in an explicit or authoritatively resolved numeric spaceId, child-page creation when a parent page is resolved, safe version-aware updates to an exactly resolved page, CQL content search, page read-back by ID, page/child-page listing, attachment listing, and Confluence user search for attribution or mention resolution. Resolves user-supplied identifiers when a reliable remote tool can do so, and asks for missing critical information when resolution is absent, ambiguous, or unsupported. Never mention email/messaging unless the user explicitly asks to send, email, share, or notify. Use for Confluence documentation/wiki/page operations that are not Jira tickets, Zoom Canvas Doc, Google Docs, or Confluence administration."
version: "0.4"
tags:
  - confluence
  - wiki
  - documentation
  - pages
  - content
  - search
  - workflow_planner
required_tools:
  - zm.connector_mcp.zm_confluence.confluence_search_user
  - zm.connector_mcp.zm_confluence.confluence_get_attachments
  - zm.connector_mcp.zm_confluence.confluence_get_page_by_id
  - zm.connector_mcp.zm_confluence.confluence_get_pages
  - zm.connector_mcp.zm_confluence.confluence_search_kb_cql
  - zm.connector_mcp.zm_confluence.confluence_get_child_pages
  - zm.connector_mcp.zm_confluence.confluence_create_page
  - zm.connector_mcp.zm_confluence.confluence_update_page
---

# Confluence Page Ops

## Non-Negotiable Remote Tool Contract

- Use only the remote Confluence connector tools in `required_tools`. Never use local shell commands, a browser session, local `acli`, cached local credentials, or user-machine state. This skill is for the remote agent's tool surface.
- A Confluence tool call with `parameters: {}` is invalid unless the exposed remote tool schema explicitly declares no inputs. Before every call, internally construct the exact argument object; if any required argument name or value is missing, ask, block, defer, or continue ANALYSIS with a parameterized read/search tool.
- Write tools may not be called from natural-language context alone. `confluence_create_page` requires at minimum a resolved `spaceId`, `title`, and a storage-format `body` when the tool schema requires body content. Child-page creation additionally requires a resolved `parentId`. `confluence_update_page` requires an exactly resolved numeric page id, the current page read by id, a complete updated `title` and `body`, and `version.number` equal to the current version plus one. Pass that normalized id as an integer to `confluence_get_page_by_id` and as its decimal string to `confluence_update_page`, following each tool's BE schema.
- Read tools also need resolved parameters when target-specific: `confluence_get_page_by_id`, `confluence_get_child_pages`, and `confluence_get_attachments` require a page/parent id. `confluence_search_kb_cql` requires a non-empty bounded CQL query. `confluence_search_user` requires a user-specific query.
- Treat an empty tool observation, missing returned page `id`, or any write-tool error as failure evidence. Do not claim a page was created or updated until the write returns an id and `confluence_get_page_by_id` reads the same id back with the expected content and version.
- If a tool call returns "Tool not found", retry once with the fully qualified name (`zm.connector_mcp.zm_confluence.<tool_name>`). Do not treat name resolution errors as Confluence API failures.

## Create And Update Target Resolution Gate

Mandatory order for page creation:

`RESOLVE SPACE -> RESOLVE OPTIONAL PARENT -> CHECK CREATE-NEW VS EXISTING -> WRITE -> READ BACK`

- `spaceId` is the required create anchor. A space key/name alone is not the numeric `spaceId`, but an exact user-supplied space key is a strong remote identifier. If the create schema requires numeric `spaceId`, resolve an exact key through an authoritative space lookup/listing tool, or through a bounded exact `space.key = "<key>"` page probe followed by `confluence_get_page_by_id` read-back from a returned page in that exact space. If read-back returns one numeric `spaceId`, use it. If the key is fuzzy/name-like, the probe returns no page, the returned container does not exactly match the key, or read-back does not return numeric `spaceId`, ask. Do not infer `spaceId` from broad content search results, examples, recent pages, local state, or remembered spaces.
- If the user asks for a child page, resolve exactly one parent page id first. A parent id supplied by the user is acceptable after `confluence_get_page_by_id` validation. A full exact parent title may be resolved only when the search result is exact and unique. Fuzzy parent references such as "the onboarding page", "latest onboarding notes", "newest release notes", "current plan", or "the docs page" must ask for parent id or exact title even if search returns one plausible result.
- For explicit create-new requests, `confluence_create_page` must be the first write for that target. If duplicate search/listing finds an existing page with the same or near-same title in the target space/parent, ask whether to create a distinct page or reuse the existing one. Do not create a replacement as a hidden update.
- For create-or-update/upsert/save-if-exists requests, resolve the target inside the requested space/parent. Exactly one exact-title match authorizes the update branch; zero exact matches authorize the create branch only when the user explicitly requested create-or-update behavior; multiple matches require clarification.
- For update-existing requests, resolve exactly one page and read it by id immediately before writing. Never create a new page as a substitute for an unresolved update target.
- Updates are full-replacement writes. Preserve the existing title unless the user explicitly requested a rename, and preserve all existing body content except the portions the user explicitly asked to change. Read the current `version.number` and send exactly current plus one. If the current title, body, or version is unavailable, do not update.

## Hard Ask Vetoes

These vetoes run before any write call. A weak or fuzzy search returning one result does not clear these vetoes. The only resolver exception is the exact space-key lookup/probe path defined below, where the returned page/container key matches the supplied key and read-back returns one numeric `spaceId`.

- **Unresolved space key/name:** "in EXAMPLESPACE", "in the wiki space", or any non-numeric space name/key that cannot be resolved by exact-key remote lookup/probe to exactly one numeric `spaceId` -> ask for `spaceId`; no write.
- **Fuzzy parent:** parent references such as "the onboarding page", "latest/newest/current", "the docs page", "the release notes parent", or "under the page about X" -> ask for parent id or exact title; no write.
- **Ambiguous owner/mention:** common human names or roles such as "Alex", "the owner", "the PM", or "the current user" in owner/mention/attribution context -> ask for exact Confluence user identity or permission to write literal plain text; no write while unresolved.
- **Ambiguous update target:** a title-only update with zero, multiple, fuzzy, or cross-space matches -> ask for the page id or an exact title plus space; no write.
- **Unsupported write workaround:** if the user asks for an unsupported move/copy/delete/upload/permission/label action, block even if creating or updating a page would partially satisfy the wording.
- **Unrelated-tool blocker:** do not mention email, messaging, Jira, docs, or other products unless the user explicitly asked for that product/action.

## Critical First-Pass Guards

Run these checks before ANALYSIS. If one matches, do not call any Confluence write tool.

0. **Scope mismatch is a no-tool final answer.** Jira tickets/issues/epics/sprints/projects belong to Jira skills. Zoom Canvas Doc, Google Docs, Sheets, email, and meeting scheduling belong to their own skills. Do not use Confluence pages as a substitute output.
1. **Cross-product write boundary.** This skill may write only Confluence pages via `confluence_create_page` or `confluence_update_page`. It must not call Jira, Zoom Canvas Doc, Google Docs, Google Sheets, mail, or admin tools even if the remote environment exposes them.
2. **Unsupported Confluence writes block.** Page delete, move, copy, label editing, permissions, space creation/deletion, attachment upload/delete, and bulk page-tree rewrites are unsupported by this tool set. Block or defer; do not approximate.
3. **Missing critical create inputs ask.** Page creation needs `spaceId`, `title`, and body content when body is required. Child-page creation needs a parent page id. If a required input is missing and cannot be resolved uniquely through remote reads, ask before writing.
4. **Resolve exactly one existing target.** Reads, updates, and attachment/child listing require a concrete page id, or a search that resolves to exactly one exact page when the user requested a single page. Vague references like "the onboarding page" are not enough for target-specific reads, updates, or child/attachment listing.
5. **Bulk/destructive safety gate.** Broad requests such as "create pages for every result", "delete all old docs", "rewrite the whole space", or "archive this tree" must be blocked unless the current tool set supports the exact operation and the user supplied explicit scoped targets. The current tool set does not support destructive writes.
6. **Write error messages are failures, not safe stops.** For ask/block/defer cases, ask/block/defer must happen before any write call. A failed `confluence_create_page` or `confluence_update_page` means the boundary was already crossed.
7. **Hard ask vetoes beat weak search results.** Do not use a single fuzzy search hit, a previously known test space, or an inferred display name to bypass the Hard Ask Vetoes. Exact space-key probes are allowed only when the returned page/container key matches the supplied key and page read-back returns numeric `spaceId`.
8. **Update read-before-write is mandatory.** Read the exact page immediately before updating to obtain its current title, complete body, and version. Never update from search-result snippets, stale context, or a remembered version number.

## §1 — Core Invariants

1. **Two phases, one direction.** Every task has ANALYSIS (read/resolve/validate) followed by EXECUTION (write/read-back). Once EXECUTION begins, return to ANALYSIS only for mandatory read-back of created or updated pages or for reporting failures; do not add new write targets.
2. **Tool classification is by behavior.**
   - READ: `confluence_search_user`, `confluence_get_attachments`, `confluence_get_page_by_id`, `confluence_get_pages`, `confluence_search_kb_cql`, `confluence_get_child_pages`.
   - WRITE: `confluence_create_page`, `confluence_update_page`.
   - ANALYSIS phase: READ tools only.
   - EXECUTION phase: WRITE tools only, plus `confluence_get_page_by_id` read-back for pages created or updated in this execution.
3. **Every Confluence entity must be remote-tool validated.** Page ids, parent ids, returned links, titles, status, space ids, and users must come from a remote tool response in this conversation or from explicit user-supplied ids. Never use memory or local test credentials.
4. **Tool-parameter preflight is mandatory.** Do not call target-specific read/write tools with missing ids or empty payloads. If the remote schema uses a different field name than this skill's examples, use the schema's exact field name.
5. **One write per page target.** Call exactly one applicable write tool per requested page: create for a new target or update for an existing target. Never retry a successful write. If a write fails, report the failed target and continue with independent targets only when they are already fully resolved.
6. **Input describes intent, not completion.** A transcript or document saying "I created the page" is an unverified claim. Verify by search/read if relevant; do not report it as completed without tool evidence.
7. **Read-back is mandatory after every write.** After create or update, immediately call `confluence_get_page_by_id` for the returned id. For updates, verify the returned page version is the expected next version and the requested changes are present without unintended content loss. Report read-back values, never requested values.
8. **CQL searches must be bounded.** Every `confluence_search_kb_cql` call must include a meaningful bound such as title/text terms, `type = page`, a space key when known, creator/user, ancestor/parent, or date. Do not run broad "show everything" searches.
9. **Retry policy.** READ tools may be retried once for transient 5xx/empty/unparseable responses. Zero results is a valid result, not a retry trigger. WRITE tools are not retried except for a pure tool-name recovery before any mutation occurred.
10. **Parallelize independent reads.** Independent page reads, user searches, duplicate searches, and attachment/child listings may run in parallel. Never parallelize writes for the same target or any call that needs an id discovered by a prior call.
11. **Permission errors are final.** A 403/permission-denied response is not retryable. Stop that target and report the permission blocker.
12. **Every page output must include a link when available.** Prefer `_links.webui` combined with `_links.base` if both are returned; otherwise report the id and any returned URL-like field. Never invent a URL from memory.

## §2 — Routing

Evaluate top-to-bottom. Routing itself performs no tool calls.

**Scope check first**

Stop/defer with no Confluence tools when intent is clearly:

- Jira issue/ticket/bug/story/epic/sprint/project work -> Jira skills.
- Zoom Canvas Doc / Google Docs / Google Sheets document creation or update -> document/sheet skills.
- Confluence administration such as spaces, permissions, labels, templates, user management, or destructive cleanup -> unsupported/admin.
- Page deletes/moves/copies -> unsupported by this tool set.

**Confluence signal gate**

Proceed only when the input contains at least one of:

- Explicit Confluence target: "Confluence", wiki, space, page id, parent page, CQL, page attachments, child pages.
- Page create/update intent: "create a Confluence page", "publish this to Confluence", "add a wiki page", "update this page", "append this section", "revise the wiki page".
- Page read/list/search intent: "read page", "find docs", "search Confluence", "list child pages", "get attachments".
- User lookup intent specifically in Confluence context.

If none: stop. Report that no Confluence page action was detected and that no changes were made.

**Flow selection**

| Signal | Flow |
|--------|------|
| Create/publish/new page intent + target space | A (Create Page) |
| Create child page intent + target space + parent signal | B (Create Child Page) |
| Update/append/revise/rename intent + exactly resolvable page | H (Update Page) |
| Page id + read/show/get intent | C (Read Page) |
| Search/find/list docs/content intent | D (Search/List Pages) |
| Parent page id + child listing intent | E (List Child Pages) |
| Page id + attachment listing intent | F (List Attachments) |
| Confluence user/owner/mention lookup intent | G (Search User) |
| Delete/move/admin/bulk destructive intent | Block |
| Missing critical page/space/parent identity | Ask |

**Mention-vs-target rule:** A Confluence page mentioned as background is not automatically the write target. Treat it as a target only when the requested action clearly applies to that page.

## §3 — ANALYSIS

Run silently by default. All required ids and payload fields must be resolved before any write.

### A1 — Extract

Extract only what the user explicitly stated or what the source object unambiguously contains.

| Entity | Rule |
|--------|------|
| `spaceId` | Required for creates. Use if explicitly supplied, if it came from read-back of an explicit user-supplied parent/page id for this same create target, or if remote exact-key resolution/probing returns exactly one numeric `spaceId`. |
| `space_key_or_name` | Candidate for remote exact-key resolution. If it is an exact key and a bounded key probe plus page read-back returns numeric `spaceId`, use that id. If it is name-like/fuzzy or cannot resolve, ask before creating. |
| `title` | Required for creates. Keep concise; do not invent a title unless the source has a clear document title/meeting title. |
| `body_source` | Page content from user text, transcript, summary, or provided source. Preserve facts; do not invent missing decisions/owners/dates. |
| `parentId` | Required only for child-page creation. Accept explicit id; otherwise resolve through remote page search/read. |
| `page_id` | Required for page read, child listing, and attachment listing when no unique search target exists. |
| `current_page` | Required for updates. Read by exact page id immediately before the write; retain its complete title, body representation/value, spaceId, parentId, and `version.number`. |
| `requested_changes` | For updates, only the title/body changes explicitly requested by the user. Treat "append" as preserving the complete existing body and adding content; treat "replace" as replacing only the scope explicitly named by the user. |
| `cql_terms` | Search terms/filters from the request: title, text, space key, type, creator, labels if the tool supports them, date/time hints. |
| `user_query` | Name/email/account text for `confluence_search_user`, only in Confluence user context. |
| `limit` | Use user-specified limit when reasonable. Default to 10 for searches/lists; cap at 25 unless the user explicitly asks for more and pagination is supported. |

### A1.5 — Clarification Gate

Ask only when inference and remote reads cannot safely resolve a critical input.

Ask when:

- Create request lacks an explicit numeric `spaceId`, a `spaceId` read back from an explicit user-supplied parent/page id for this same create target, or exactly one numeric `spaceId` from remote exact-key resolution/probing.
- Create request lacks a title and no clear source title exists.
- Create request lacks body content and the tool schema requires body.
- Child-page request lacks a parent id and search returns zero or multiple plausible parents.
- Child-page request uses a fuzzy/ordinal parent phrase such as "onboarding page", "latest", "newest", "current", or "the docs page"; ask even when search returns one plausible page.
- Create request supplies only a space key/name such as EXAMPLESPACE, but the value is not an exact key or remote exact-key resolution/probing cannot return one numeric `spaceId`; ask even if broad content searches reveal pages in that space.
- An update request does not identify one exact page by id or by a unique exact-title match within a resolved space.
- An update requires changing existing body content but the latest page read does not expose a usable complete body representation/value or numeric `version.number`.
- The page body would assign or mention an unresolved common-name person/role; ask for exact user identity or permission to write literal text.
- Single-page read/list/attachment request names a vague page and search returns zero or multiple plausible pages.
- Duplicate check finds an existing page and the user asked for create-new but did not specify whether duplicates are acceptable.

Do not ask when:

- The user supplied an explicit `spaceId`, `page_id`, or `parentId`.
- Remote exact-key resolution/probing returned exactly one numeric `spaceId` for the user-supplied space key.
- A remote read/search returns exactly one non-fuzzy, exact-title matching page for the requested read target.
- A create-or-update request resolves to exactly one exact-title page (update it) or zero exact-title pages (create it).
- The request is unsupported by the tool set; block directly instead of asking about impossible operations.

Batch all currently known questions into one clarification. After the user answers, validate answers through remote reads where possible before writing.

### A2 — Resolve Space And Parent

**Space resolution for create flows A/B**

1. If `spaceId` is explicit, carry it forward.
2. If the user supplied an explicit parent/page id for this same create target and read-back returns a `spaceId`, that returned `spaceId` may be used for that target only.
3. If only an exact space key is explicit and the create schema does not accept keys directly, resolve it to numeric `spaceId` with one of these read-only paths:
   - Authoritative space lookup/listing by key/name when the exposed schema supports it. One exact key match with one numeric `spaceId` -> use it.
   - Otherwise, run a bounded exact-key page probe such as `type = page AND space.key = "<key>"` with the smallest practical limit, then call `confluence_get_page_by_id` on a returned page whose container/path confirms the exact key. If read-back returns one numeric `spaceId`, use it.
4. If the supplied space value is fuzzy/name-like, there are zero pages to probe, multiple conflicting containers, no numeric `spaceId`, a key/container mismatch, or only broad page/content search evidence, ask for `spaceId`.
5. Never use a hardcoded default, recently used space, local CLI space, or example id.

**Parent resolution for child create flow B**

1. If `parentId` is explicit, validate with `confluence_get_page_by_id(parentId)` before write.
2. If parent is named by full exact title, use bounded `confluence_search_kb_cql` or `confluence_get_pages` in the resolved space. Match exact title only.
3. One exact-title match -> use returned page id as `parentId`.
4. Any fuzzy, role-like, ordinal, or partial parent phrase -> ask for parent id or exact title. Do not search-and-pick.
5. Zero/multiple matches -> ask; do not create a top-level page as a substitute.

### A3 — Duplicate And Target Resolution

**Create duplicate check**

- Create-or-update/upsert/save-if-exists requires an exact-title search in the resolved scope. One exact match selects update, zero exact matches select create, and multiple exact matches require clarification.
- Search/list within the resolved `spaceId` and optional `parentId` for same or near-same title.
- If one current page matches and the user asked strictly to create a new page, ask whether to create a distinct page, stop/reuse the existing page, or update it. Do not silently change create intent into update intent.
- If multiple pages match, ask or stop; do not choose the first page.
- If no page matches, proceed to create.

**Read/search target resolution**

- Page id read: call `confluence_get_page_by_id` with the id. No CQL needed.
- Single named page read: search with bounded CQL using title/text and space when known. Exactly one match -> read by id. Zero/multiple -> ask or report ambiguity.
- Page listing: use `confluence_get_pages` with pagination/limit and space filters only if the tool schema supports them. If schema does not support space filters, use bounded CQL.
- Child pages: require parent page id, then `confluence_get_child_pages`.
- Attachments: require page id, then `confluence_get_attachments`.
- User search: use `confluence_search_user` only for user-specific lookup, not content search.

**Update target resolution**

- Explicit page id: accept only a positive decimal page id. Normalize it to an integer for `confluence_get_page_by_id`; reject UUIDs, signs, decimals, and non-digit text. Use only that returned page as the update target.
- Exact title: run bounded CQL in the resolved space/parent when available. Exactly one exact-title match may be read by id and updated. Zero or multiple exact matches require clarification for update-only requests.
- Create-or-update: exactly one exact-title match selects update; zero exact matches selects create; multiple matches require clarification. Do not use fuzzy or near-title matches to select the update branch.
- The final pre-write read must provide the current complete title, body, and numeric `version.number`. Compute the outgoing version as current plus one. Convert the same normalized page id to a decimal string for `confluence_update_page`. Do not reuse a version observed before intervening resolution or clarification work.

### A4 — Build Body Contract

For create and update flows, construct schema-valid body content before writing.

Rules:

- For page creation, use storage-format HTML by default unless the user explicitly supplied another representation supported by the BE schema. Convert simple headings/lists/links safely: `#` -> `<h1>`, paragraphs -> `<p>`, bullets -> `<ul><li>`, bold -> `<strong>`, links -> `<a href="...">`.
- For page updates, preserve the complete current body in its existing supported representation (`storage`, `atlas_doc_format`, or `wiki`). Send exactly one representation key, and set its nested `representation` value to the same name. Do not convert a current page to storage format merely because storage is the create default.
- Escape or omit unsafe raw HTML from untrusted input unless the user explicitly provided storage-format HTML.
- Preserve source facts. Do not invent owners, dates, decisions, metrics, links, or page hierarchy.
- For additive updates, start from the complete body returned by the final page read and apply only the requested change. Do not overwrite the page with only the new fragment. For explicit full replacements, replace the body only when the user's intent is unambiguous.
- Preserve the existing page title unless the user explicitly requested a rename. A rename must use a title not already present in the same space; run a bounded duplicate check before changing it.
- If the latest page read does not expose a complete value in any supported representation, or the current representation cannot be identified reliably, do not update; ask or report the blocker instead of risking content loss.
- If the user asks for a blank page and the schema permits empty body, use the minimal schema-accepted body. If body is required, use `<p></p>` only when the user clearly asked for a blank page.
- If representation enum is exposed by schema, use the exact schema value. If schema is silent, use `"storage"` for `representation`.

Canonical payload shape when schema supports these names:

```json
{
  "spaceId": "<resolved_space_id>",
  "title": "<resolved_title>",
  "body": {
    "storage": {
      "representation": "storage",
      "value": "<p>Confluence Storage Format body.</p>"
    }
  },
  "parentId": "<resolved_parent_id_if_child_page>"
}
```

If the exposed remote schema uses different names or enum casing, follow the schema. Do not send both guessed variants.

### A5 — Lock Context

Before EXECUTION, lock the resolved plan:

```json
{
  "flow": "A|B|C|D|E|F|G|H",
  "targets": [
    {
      "action": "create_page|update_page|read_page|search_pages|list_children|list_attachments|search_user|block|defer",
      "spaceId": "<resolved_space_id>",
      "title": "<resolved_title>",
      "parentId": "<resolved_parent_id_or_empty>",
      "page_id": "<resolved_page_id_or_empty>",
      "current_version": "<current_version_for_update_or_empty>",
      "next_version": "<current_plus_one_for_update_or_empty>",
      "planned_diffs": ["create page with title/body/parent OR update exact page with requested changes"]
    }
  ],
  "org_ctx": {
    "resolved_pages": [],
    "resolved_users": [],
    "duplicate_candidates": [],
    "content_representation": "<resolved_representation>"
  }
}
```

Self-check before write:

- Can every write parameter be traced to explicit user input, remote tool output, or deterministic content conversion?
- Is this definitely a supported create or update, not a delete/move/admin request?
- For update: was exactly one page read immediately before execution, is its complete body available, and is `next_version = current_version + 1`?
- Is this free of every Hard Ask Veto?
- For create: is `spaceId` present?
- Is the complete outgoing `title` present?
- Is the complete outgoing body present when required?
- If child page: is `parentId` validated?

If any answer is no, do not write.

## §4 — EXECUTION

### E0 — Entry Gate

Before calling a write tool, verify all conditions:

1. Lock Context is complete.
2. The operation is exactly one supported create or update.
3. Create: `spaceId` and `title` are non-empty. Update: exact page `id`, current title/body, and current numeric version are present.
4. Body payload matches the remote schema and contains the complete intended post-write body, not only an additive fragment.
5. Parent id is present and validated for child-page creation.
6. Duplicate handling is resolved.
7. No Hard Ask Veto remains in the write target.
8. No read-only, unsupported, or cross-product intent remains in the write target.
9. Update: outgoing `version.number` is exactly the latest read version plus one; the existing title is retained unless rename was explicit.

Gate failure -> ask/block/defer and report that no Confluence write was made.

### E1 — Write

Call `confluence_create_page` exactly once per resolved page target.

Hard payload gate:

- Required: `spaceId`, `title`.
- Required when body is needed: `body.storage.representation`, `body.storage.value`.
- Optional: `parentId` only when resolved and schema supports it.
- Forbidden: delete/move/admin fields, local URLs, local file paths, or values copied from examples.

For multiple independent page creates, create one page at a time unless the remote environment explicitly supports safe parallel writes. Stop writing additional pages if a shared missing permission or invalid space error appears.

### E2 — Update

Call `confluence_update_page` exactly once for the resolved existing page.

Required payload contract:

```json
{
  "id": "<normalized_decimal_page_id>",
  "title": "<existing_title_or_explicit_new_title>",
  "body": {
    "<representation_key>": {
      "representation": "<same_representation_key>",
      "value": "<complete_post_update_body>"
    }
  },
  "version": {
    "number": 2,
    "message": "<optional_concise_change_summary>"
  }
}
```

- Replace the example version `2` with the integer obtained by adding one to the latest read version.
- Replace both representation placeholders with exactly one of `storage`, `atlas_doc_format`, or `wiki`, preserving the supported representation returned by the latest page read.
- Pass the normalized page id as a decimal string here. For the subsequent `confluence_get_page_by_id` read-back, convert the returned decimal id to an integer and reject a non-numeric id.
- Include `spaceId` only when the live schema requires it or the user explicitly requested a supported space change; do not infer a move.
- If the update returns a version conflict, do not retry with a guessed increment. Read the latest page again, report the conflict, and ask before reapplying when the intervening edit could affect the requested change.

### E3 — Read-Back

After each successful create or update response:

1. Extract page id from the write result.
2. Validate the returned id as a positive decimal value, convert it to an integer, and call `confluence_get_page_by_id` with that integer id.
3. Compare read-back title, body changes, status, spaceId, parentId, version, and link fields against Lock Context.
4. Report read-back values. If read-back fails or differs, report the mismatch and do not claim full success.

For read-only flows C/D/E/F/G, the read/search/list response itself is the output. No additional read-back is needed unless a search result must be expanded by page id.

## §5 — Output Format

Every created, updated, or read page output should include:

- Title
- Page id
- Status when returned
- Space id when returned
- Parent id when relevant and returned
- Link when returned

Outcome formats:

| Outcome | Format |
|---------|--------|
| Created | `Created Confluence page: {title} (id: {id}) - {link}` |
| Updated | `Updated Confluence page: {title} (id: {id}, version: {version}) - {link}` |
| Read | `{title} (id: {id}, status: {status}) - {link}` |
| Listed | `{N} Confluence pages found for {query/scope}` plus concise rows |
| Attachments | `{N} attachments found for page {id}` plus names/ids when returned |
| User search | `{N} Confluence users matched {query}` plus display/email/account fields when returned |
| Ask | `I need {missing_field} before creating the Confluence page. No Confluence changes were made.` |
| Block | `Cannot perform this Confluence operation with the available tools: {reason}. No Confluence changes were made.` |
| Defer | `This request belongs to {skill/product}. No Confluence changes were made.` |
| Failed | `Confluence operation failed at {step}: {error}.` |

Ask/block/defer answers must name the specific gate that fired. Do not answer with an unrelated product/tool blocker. For a create request with an unresolved or unprobeable space key/name, the final answer must ask for the numeric Confluence `spaceId` and must include `No Confluence changes were made.` Do not mention email, messaging, sharing, or notification tools unless the user asked to send/share/notify something.

Use "Done" only when all requested targets succeeded and read-back verified every create or update.

## §6 — Technical Notes

| Topic | Rule |
|-------|------|
| `spaceId` vs space key | `confluence_create_page` requires numeric `spaceId` unless the live schema explicitly accepts keys. An exact space key may be resolved by authoritative lookup or exact-key page probe plus page read-back. A fuzzy name is not enough. |
| Page id types | Accept only a positive decimal page id. Pass it as an integer to `confluence_get_page_by_id` and as a decimal string to `confluence_update_page`. |
| CQL | Use bounded CQL. Prefer `type = page` plus title/text/space/date/user constraints. Do not run broad unbounded content searches. |
| Pagination | Honor `limit`/`start`/`next` fields only when exposed by schema. Default `limit` to 10; cap at 25 unless explicitly requested. |
| Links | Use returned link fields. If `_links.base` and `_links.webui` are both present, combine them. Otherwise report the returned URL/id without inventing a domain. |
| Attachments | This skill lists attachments only. Upload/delete/update attachment operations are unsupported. |
| Users | `confluence_search_user` is only for Confluence user lookup in a Confluence task. It is not a general people search and not a Jira assignee resolver. |
| Storage body | Keep body valid and minimal. Avoid Markdown in `body.storage.value`; convert to storage-safe HTML first. |
| Update version | Read the latest numeric `version.number` immediately before writing and send exactly that value plus one. Never guess or reuse a stale version. |
| Additive update | Preserve the complete existing body and apply only the requested addition/change; the update API replaces page content rather than patching a fragment. |
| No local state | Do not mention or rely on local `acli`, browser login, filesystem files, or test account details in remote execution. |

## §7 — Examples

### Example 1: Create Page In Explicit Space

Input: `Create a Confluence page in spaceId 12345 titled "Launch Checklist" with these bullets: owner Alice; freeze Friday.`

Plan:

- Route Flow A.
- `spaceId` explicit: `12345`.
- title explicit: `Launch Checklist`.
- body converted to storage HTML.
- duplicate search bounded to title/space.
- create once.
- read back by returned id.

Write payload:

```json
{
  "spaceId": "12345",
  "title": "Launch Checklist",
  "body": {
    "storage": {
      "representation": "storage",
      "value": "<ul><li>Owner: Alice</li><li>Freeze: Friday</li></ul>"
    }
  }
}
```

### Example 2: Space Key Resolution

Input: `Create a Confluence page titled "Support Handoff" in the EXAMPLESPACE space.`

If exact-key lookup/probing cannot resolve EXAMPLESPACE to exactly one numeric `spaceId`, ask: `I need the numeric Confluence spaceId for EXAMPLESPACE before creating the page. No Confluence changes were made.`

Do not use a remembered or local test `spaceId`.

### Example 3: Update Request

Input: `Update Confluence page id 12345 and append a Risks section containing "Rollback plan pending".`

Plan:

- Validate `12345` as a positive decimal page id and read it as integer `12345` immediately before the write.
- Preserve the returned title, complete existing body, and its supported representation.
- Append the requested Risks section to the complete body.
- Set `version.number` to the returned current version plus one.
- Call `confluence_update_page` once with id string `"12345"`, then read page integer `12345` back and verify the new section, representation, and version.

Do not send only the new Risks fragment as the body, convert the body representation unnecessarily, or guess the version number.

### Example 4: Child Page With Ambiguous Parent

Input: `Create a child page under the onboarding page.`

Search for candidate onboarding pages only if enough scope is known. If multiple candidates appear, ask for the parent page id. Do not choose the first result and do not create a top-level page.

### Example 5: Jira Request

Input: `Create a Jira task to review the Confluence docs.`

Defer to `jira_issue_ops`. Do not create a Confluence page as a proxy task tracker.

### Example 6: Space Key Is Not Space Id

Input: `Create a Confluence page in the EXAMPLESPACE space titled "Support Handoff".`

Resolve EXAMPLESPACE with an authoritative space resolver when available; otherwise use a bounded exact `space.key = "EXAMPLESPACE"` page probe and page read-back to obtain numeric `spaceId`. If the probe cannot prove the exact key and return numeric `spaceId`, ask. Do not use broad searches, infer a numeric id, or create from a remembered space key mapping.

### Example 7: Create Or Update

Input: `Create or update the Confluence page "Weekly Notes" with today's notes.`

Resolve the target space, then run an exact-title search for `Weekly Notes` in that scope:

- Exactly one exact match: read it by id, preserve its complete body unless replacement was explicit, apply today's notes, use current version plus one, update once, and read back.
- Zero exact matches: create the page only because the user explicitly requested create-or-update behavior, then read back.
- Multiple exact matches or unresolved scope: ask for the page id or exact space; make no write.
