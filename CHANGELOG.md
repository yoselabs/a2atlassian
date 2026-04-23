# Changelog

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
