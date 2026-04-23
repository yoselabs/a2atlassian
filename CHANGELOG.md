# Changelog

## Unreleased

### Fixed
- **Every MCP tool response crashed client-side** with `pydantic_core.ValidationError: Input should be a valid dictionary or object to extract fields from`. Tool functions declared `-> OperationResult`, but the `@mcp_tool` wrapper actually returns a formatted JSON/TOON string; MCP ≥1.9's output-schema validation then validated the string against the dataclass schema. The decorator now overrides the annotation to `str` on both the wrapper and its `__wrapped__` target so FastMCP builds a matching output schema. Confluence reads were fully blocked by this.
- **`confluence_upsert_pages` silently no-op'd `page_width` / `emoji` on existing pages.** Both knobs went through `Confluence.set_page_property`, which is POST-only and errors (swallowed by the batch handler) when the property already exists. Now resolves through get → `update_page_property` with incremented version, falling back to `set_page_property` on first write.

## v0.5.1 — 2026-04-23

### Docs
- `a2atlassian login --token` and the MCP `login` tool now advertise `op://` 1Password references alongside `${ENV_VAR}`.

## v0.5.0 — 2026-04-23

### Changed (breaking)
- **Connection TOML on-disk key `project` renamed to `connection`.** Existing connection files from v0.2-v0.4 fail to load with a clear error; delete them and re-run `a2atlassian login`. No compat shim.
- `ConnectionInfo` is now a frozen Pydantic v2 `BaseModel` (was a `@dataclass`). External callers that construct it keyword-style are unaffected; `.model_dump()` / `.model_validate()` are available.
- `ConnectionStore.save(info: ConnectionInfo)` — single-argument. The old 7-positional-param signature is gone.
- `ConnectionStore.list_connections()` no longer accepts a filter arg. Use `load()` for single-name lookup, or filter the returned list in the caller.

### Added
- **1Password references** (`op://vault/item/field`) resolve via the `op` CLI alongside `${ENV_VAR}` refs. Falls through unchanged if `op` is not installed or the fetch fails.
- Connection-name validation (`[A-Za-z0-9][A-Za-z0-9._-]*`) applied on both `ConnectionInfo` construction and `ConnectionStore._path` — blocks path traversal.
- Atomic writes: `save()` writes to a tempfile and renames, so a crash mid-write can never leave a corrupt file.

### Changed
- TOML writing moved to `tomli-w` (was hand-rolled string formatting with manual escaping).
- `pydantic>=2,<3` promoted to a direct dependency (previously transitive via `mcp`).

## v0.4.0 — 2026-04-23

### Added
- Confluence domain: `confluence_get_page`, `confluence_get_page_children`, `confluence_search`, `confluence_upsert_pages`.
- Markdown → Confluence storage translator; recursive `<details>` → expand-macro translation.
- Per-page upsert with identity resolution (page_id → parent-scoped title match → space-root title match).
- Batch upsert returns `{succeeded, failed, summary}`; does not raise on partial failure.
- Page-level knobs on upsert: `labels`, `emoji`, `page_width`.
- `--enable confluence` flag; MCP server instructions updated to reflect Confluence scope.

### Changed
- `AtlassianClient` split into `AtlassianClientBase` + `JiraClient` (+ new `ConfluenceClient`). Existing Jira code continues to work; imports change from `a2atlassian.client.AtlassianClient` → `a2atlassian.jira_client.JiraClient`.

## v0.3.1 — 2026-04-23

### Fixed

- **`jira_get_worklogs` summary mode** now paginates through all matching issues instead of silently truncating at 500. Large date ranges correctly include all worklogs.

### New

- **MCP `login` tool** accepts `timezone` and `worklog_admins` parameters, matching the CLI. Agents creating connections via MCP can now set these without a CLI round-trip.

## v0.3.0 — 2026-04-23

### Breaking changes

- **Parameter rename: `project` → `connection`.** Every tool parameter previously called `project` (the saved connection identifier) is now `connection`. CLI: `--project` / `-p` → `--connection` / `-c`. No compatibility alias. The TOML on-disk key stays `project` so existing saved connections load without migration; re-running `a2atlassian login` regenerates the file with the new (fully forward-compatible) shape.
- **`jira_search` now returns a minimal default field set** (`summary`, `status`, `assignee`, `priority`, `issuetype`, `parent`, `updated`) instead of the library's all-fields default. Callers consuming `_jira.jql()` output directly see trimmed payloads; callers using the public `search()` return shape (`_extract_issue_summary`) are unaffected. Pass `fields=["*all"]` to restore full-payload behavior.
- **`jira_get_issue_dev_info` removed** — was a placeholder that returned a static "not supported" string.
- **`jira_link_to_epic` removed** — use `jira_create_issue_link` with `link_type="Epic"`.
- **`jira_add_watcher` + `jira_remove_watcher` replaced by `jira_set_watchers`** (single tool with `add=[]` / `remove=[]` lists).
- **`jira_get_project_components` + `jira_get_project_versions` replaced by `jira_get_project_metadata`** (single tool with `include=["components", "versions", "all"]`).
- **`jira_get_worklogs` now a two-mode tool** — `issue_key` argument triggers raw per-worklog dump (old behavior); `date_from` triggers summary mode with per-person aggregation and worklog-admin attribution.

### Fixed

- **`jira_get_boards`** no longer throws `'Jira' object has no attribute 'boards'`. Uses the correct `atlassian-python-api` method name (`get_all_agile_boards`).
- **`jira_update_sprint`** bonus fix — the underlying `update_sprint` method doesn't exist in `atlassian-python-api` 4.0.7; switched to `update_partially_sprint`.

### New

- **`jira_search_count`** — cheap pre-check tool returning `{jql, total}` without paging through issues.
- **`@mcp_tool` decorator** with `Literal[...]`-based enum validation. Invalid `format`, `detail`, etc. return a structured "Invalid value" error instead of swallowing silently.
- **`ConnectionInfo.timezone`** — IANA zone for day-boundary math in worklog summaries. CLI `--tz` accepts aliases (`CET`, `ET`, `UTC`).
- **`ConnectionInfo.worklog_admins`** — email list. Worklogs authored by an admin on someone else's ticket attribute to the ticket's assignee (covers the proxy-logged-during-daily workflow).
- **"Connection not found" error** now lists available connection names and proposes a close match via `difflib`.

### Documentation

- MCP server `instructions=` string honest about Jira-only scope today.
- Every list-returning tool documents the TOON default.
