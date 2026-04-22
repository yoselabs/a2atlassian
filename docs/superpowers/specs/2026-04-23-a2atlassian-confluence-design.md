# a2atlassian — Confluence support (v0.4.0 spec)

**Date:** 2026-04-23
**Source signals:** `2026-04-23-2105-a2atlassian-confluence-gaps.yaml`, `2026-04-23-2120-protea-atlassian-session-scan.yaml`, `2026-04-23-2210-protea-final-pass.yaml`
**Handover brief:** `docs/signals-from-protea-2026-04-23.md` (signals S3, S4, S5; related S11)
**Target release:** v0.4.0
**Precondition:** v0.3.0 (cleanup batch) ships first. This spec assumes the `@mcp_tool` decorator, renamed `connection` parameter, and consolidated tool surface from v0.3.0 are in place.

**Client-layer refactor is owned by this spec, not v0.3.0.** v0.3.0 leaves `src/a2atlassian/client.py` / `AtlassianClient` unchanged. The split into `AtlassianClientBase` + `JiraClient` + `ConfluenceClient` (see Architecture section below) is the first implementation step of v0.4.0, before any Confluence tool work begins.

---

## Goals

Close the largest structural gap in a2atlassian: ship Confluence parity so the per-project connector actually covers the whole Atlassian product. Encode Protea's workaround catalogue (`<details>` → expand macro, storage-format hygiene, `page_width` control, batch upsert with per-page status) into the tool layer so every consumer gets the right behavior by default.

Success criteria: Protea's daily-report workflow should write all of its six pages through a2atlassian in a single batch call, with partial-failure visibility, without re-deriving any markdown-to-storage workaround.

---

## Scope (v1)

**Read:**

- `confluence_get_page(connection, page_id, expand=None)` — fetch one page. `expand` defaults to `"body.storage,version,space"`.
- `confluence_get_page_children(connection, page_id, limit=50, offset=0)` — list children.
- `confluence_search(connection, cql, limit=25, offset=0)` — CQL search with minimal default fields.

**Write:**

- `confluence_upsert_pages(connection, pages=[...])` — batch create-or-update with per-page status.

**Deferred to v2:** `confluence_delete_page`, comments, attachments, labels-as-separate-tool, restrictions.

Four tools total. One batch write; the rest are reads.

---

## Design

### Tool 1 — `confluence_get_page`

Straightforward read-by-id. Single-entity response, `format="json"` default (matches the cleanup spec's rule).

### Tool 2 — `confluence_get_page_children`

List children under a page id. Paginated. Minimal default fields (title, id, version, url). Same "defaults slim, escape hatch for full" pattern as `jira_search` from v0.3.0.

### Tool 3 — `confluence_search`

CQL passthrough with a minimal default expand set. Document the gotcha about `text ~ "..."` being broad and expensive in CQL; mirror `jira_search`'s `limit` / `offset` shape.

### Tool 4 — `confluence_upsert_pages` (the interesting one)

```python
confluence_upsert_pages(
    connection: str,
    pages: list[PageUpsertSpec],
) -> str  # json
```

Where each `PageUpsertSpec` is:

```python
{
    "space": str,
    "title": str,
    "content": str,
    "parent_id": str | None = None,
    "page_id": str | None = None,
    "content_format": Literal["markdown", "storage"] = "markdown",
    "page_width": Literal["full-width", "fixed-width"] | None = None,
    "emoji": str | None = None,
    "labels": list[str] | None = None,
}
```

**Identity resolution** — per page in the batch, in order:

1. If `page_id` given → update that page. Error if not found.
2. Else if `parent_id` given → search for a title match **under that parent only**. Update if found, create if not.
3. Else → search in space root (top-level pages only) for matching title. Update-or-create.

**Title-match scope is strictly per-parent, never per-space.** A page with the same title under a different parent does not count as a match. The trade-off: re-running with a different `parent_id` will create a new page rather than re-use the existing one elsewhere in the space. This is deliberate — per-space title uniqueness would re-introduce the ambiguity that makes sooperset's current behavior fragile (two managers can legitimately have a "2026-04-23 report" under different sprint parents). Callers that need cross-space deduplication should cache `page_id` from a prior run.

Eliminates the duplicate-title failure on re-run (13+ occurrences in a single Protea session) within the expected scope (same parent, same title). Caller can cache the returned `page_id` to fast-path subsequent upserts regardless of parent.

**Return shape** (JSON):

```json
{
  "succeeded": [
    {"title": "...", "page_id": "...", "status": "created"|"updated", "url": "...", "version": 3}
  ],
  "failed": [
    {"title": "...", "error": "...", "error_category": "permission"|"format"|"conflict"|"other"}
  ],
  "summary": {"total": 6, "created": 2, "updated": 3, "failed": 1}
}
```

**Does not throw on partial failure.** Returns all outcomes. This is the structural fix for the silent half-published state observed repeatedly in Protea sessions.

**Page-level knobs:**

- `page_width` — fixes S5. `None` on update preserves whatever the page had before (important — avoids regressing pages the caller doesn't explicitly want to change). Default on create: `"fixed-width"`.
- `emoji` — the API supports it; sooperset doesn't expose it.
- `labels` — optional; applied after page body is saved.

### Content format — markdown as the primary path

Implements D2 from the brainstorm. `content_format="markdown"` (default) runs the input through an internal `markdown_to_storage()` translator. `content_format="storage"` is an escape hatch that bypasses translation.

**Translator rules:**

| Markdown construct | Confluence storage output |
|---|---|
| `# / ## / ###` headings | `<h1>` / `<h2>` / `<h3>` |
| pipe-syntax tables | native `<table><tbody><tr><th>...` |
| `<details><summary>X</summary>...</details>` | `<ac:structured-macro ac:name="expand"><ac:parameter ac:name="title">X</ac:parameter><ac:rich-text-body>...</ac:rich-text-body></ac:structured-macro>` (encodes S11 permanently). Translator is **recursive** — markdown inside the `<details>` body is re-parsed through the full rule set, including nested tables, code fences, and nested details. |
| `@user:<accountId>` | `<ac:link><ri:user ri:account-id="..."/></ac:link>` |
| code fences with language | `<ac:structured-macro ac:name="code">` with `ac:parameter ac:name="language"` |
| HTML passthrough | unchanged (Confluence storage is HTML-shaped) |

Critically, the translator re-parses markdown *inside* HTML `<details>` bodies — the specific gap that made the current sooperset path useless for collapsible tables. Every translation rule is a pure function with a round-trip unit test.

**Raw storage path** (`content_format="storage"`) passes input through unchanged. Caller owns Fabric-editor compatibility when they use this.

**Future content formats:** `adf` (Atlassian Document Format, JSON-based) — deferred. Not needed for v1.

### Client + module architecture — D5

**Refactor step (must happen before any Confluence tool is written).** Today's `src/a2atlassian/client.py` contains a single `AtlassianClient` that wraps `atlassian.Jira`. Split into:

- `AtlassianClientBase` in `client.py` — owns `__init__(ConnectionInfo)`, the `_call(fn, *args, **kwargs)` retry helper, the class-level `MAX_RETRIES` / `RETRY_BACKOFF` / `REQUEST_TIMEOUT` constants, and `validate()` (which calls `/myself` — works for both services but currently uses Jira's client — move to base by calling whichever service's `/myself` is configured, or keep Jira-only and add a Confluence-side `validate()` in the subclass).
- `JiraClient(AtlassianClientBase)` in `jira_client.py` — owns the lazy `_jira` property (moves from current `AtlassianClient`).
- `ConfluenceClient(AtlassianClientBase)` in `confluence_client.py` — owns the lazy `_confluence` property.

Every existing caller of `AtlassianClient` in `jira/` and `jira_tools/` changes to `JiraClient`. This is a mechanical rename + an import change; no logic moves.

Resulting directory layout:

```
src/a2atlassian/
  client.py               # AtlassianClientBase — shared retry/auth
  jira_client.py          # JiraClient — lazy _jira
  confluence_client.py    # ConfluenceClient — lazy _confluence
  jira/                   # existing operation modules
  jira_tools/             # existing MCP tool modules
  confluence/             # new: pages.py, search.py, content_format.py
  confluence_tools/       # new: pages.py, search.py
```

Reasoning:

- The two underlying libraries (`atlassian.Jira`, `atlassian.Confluence`) diverge on response shape, pagination, and error codes. Keeping them separate keeps the boundary crisp.
- `ConnectionInfo` remains one object (same credentials). Each client is constructed from the same connection.
- Testing stays clean: Jira tests never touch Confluence mocks and vice versa.

**MCP contract impact (`mcp_server.py`):**

- New `_get_jira_client(connection)` and `_get_confluence_client(connection)` accessors. Tool modules receive the accessor they need via registration.
- `--enable confluence` flag becomes real (the `known_domains = {"jira"}` stub in the current code extends to `{"jira", "confluence"}`).
- Server `instructions=` gets a Confluence line; the "Jira only today" caveat added in v0.3.0 comes out.
- Connection TOML gains no new required fields for Confluence (auth is the same). Optional `timezone` / `worklog_admins` from v0.3.0 stay untouched.

---

## Testing

- **Recorded fixtures** for every Confluence endpoint: page GET, children, CQL search, create, update. Extend the existing `scripts/record-fixtures.sh` pattern to Confluence.
- **Pure-function translator tests** in `tests/confluence/test_content_format.py`. Every rule above gets a round-trip test. Particular attention to: tables-inside-details (the S11 regression case), mentions, code fences with language attributes, nested lists.
- **Upsert identity matrix** — 6 tests for the 3 resolution paths × create/update.
- **Batch partial-failure** — mocked responses where some pages return 403, some 400, some 200; assert the tool returns structured outcomes instead of throwing.
- **Raw escape hatch** — `content_format="storage"` bypasses translation (test with a storage-format snippet that contains `<ac:structured-macro>` and confirm it passes through unchanged).
- **Client separation** — a fixture that boots a `ConfluenceClient` without importing any Jira modules (asserts the module boundary holds).

---

## Open questions

1. **CQL default-fields shape.** JQL's minimal default fits a ticket shape naturally (key, summary, status, assignee). CQL results are heterogeneous (pages, blogposts, comments, attachments). Needs a decision during implementation: one minimal set per content-type, or a single "headline + id + url + lastModified" set that works for all. Probably the latter; confirm during spike.
2. **Markdown translator coverage boundary.** Protea's real content will inevitably include constructs we didn't anticipate. Decision for v1: ship with the rule table as-is and **defer** the `translation_warnings` field to v2 — passing through unknown constructs as HTML is already a reasonable fallback, and agents can diff the round-trip if they care. If this turns out to hurt in practice, add the field in a point release; the upsert response shape would gain an optional top-level `translation_warnings: list[str]` array without breaking existing consumers.
3. **Rate limiting.** Confluence's rate limits differ from Jira's; the shared retry helper in `AtlassianClientBase` may need per-service backoff config. Confirm during spike; not a blocker.

---

## Out of scope

- S6 — sooperset content-contamination. Upstream filing only.
- Attachments, comments, restrictions — v2.
- ADF (Atlassian Document Format) as a content-format option — v2.
- Confluence → Jira linking tools (smart links, mentions of tickets in pages). Exists natively via the API; not worth a dedicated tool for v1.
- Space administration tools. Out of scope indefinitely.

---

## Release shape

- **v0.4.0** after v0.3.0 lands.
- Larger PR than the cleanup batch. Recommended: split the implementation into a reviewable sequence of commits (client separation → read tools → translator → upsert → batch semantics → docs).
- Target completion: multi-week, one focused pitch.
