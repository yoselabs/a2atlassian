# a2atlassian — Jira cleanup batch (v0.3.0 spec)

**Date:** 2026-04-23
**Source signals:** `2026-04-23-2105-a2atlassian-confluence-gaps.yaml`, `2026-04-23-2120-protea-atlassian-session-scan.yaml`, `2026-04-23-2210-protea-final-pass.yaml`
**Handover brief:** `docs/signals-from-protea-2026-04-23.md`
**Target release:** v0.3.0
**Scope:** Jira-only cleanup and consolidation. Confluence ships as a separate spec (v0.4.0).

---

## Goals

Fix observed production bugs, collapse an oversized tool surface, close the parameter-naming gap that costs one turn per agent session, and establish a decorator-driven pattern for future tool modules.

In one release, Protea's daily-report workflow should stop crossing connectors for Jira reads, stop burning retries on `Connection not found`, and stop blowing the token ceiling on broad JQL.

---

## Precondition — repo consolidation

Two working copies exist. Canonicalize on the standalone before any signal work:

- **Canonical:** `/Users/iorlas/Workspaces/a2atlassian` — HEAD `fb3661c` (v0.2.1, yoselabs rebrand), clean.
- **Stale:** `/Users/iorlas/Workspaces/agentic-eng/a2atlassian` — older HEAD, but holds unique uncommitted work.

**Porting scope (what the first commit contains):**

- Copy `src/a2atlassian/jira_tools/` into the canonical repo. Directory contents verified at time of this spec: `__init__.py`, `boards.py`, `comments.py`, `fields.py`, `issues.py`, `links.py`, `projects.py`, `sprints.py`, `transitions.py`, `users.py`, `watchers.py`, `worklogs.py` (12 files).
- Delete old flat `src/a2atlassian/jira_read_tools.py` and `src/a2atlassian/jira_write_tools.py`.
- Apply the modified `src/a2atlassian/mcp_server.py` and `tests/test_mcp_server.py` that wire the new per-domain registration.

**Audit after porting, before proceeding to design items:** the stale refactor is a mechanical split only. It does **not** already implement any of the section-5 consolidations (`jira_link_to_epic`, watcher merge, project metadata merge, `jira_get_issue_dev_info` deletion, etc.) — confirm this explicitly by running `rg '@server\.tool\(\)' src/a2atlassian/jira_tools/` and checking the tool list matches the pre-consolidation surface (should be 18 read + 16 write = 34 `@server.tool()` calls across the package). If the stale copy turns out to have already landed any of section 5, mark those items as done and skip them.

Delete the agentic-eng working copy after porting so we don't drift again.

---

## Design

### 1. Parameter rename: `project` → `connection`

S1 (plus 2210-A) is a naming bug: the MCP server calls the per-connection identifier `project`, which reads as "Jira project key." Agents pass `PE0` instead of `protea` ~5 times per session before self-correcting.

- Rename across every tool signature, every docstring, the CLI (`--project` → `--connection`), and the MCP server `instructions=` string.
- **No compatibility alias.** Pre-1.0; better to take the breakage now than carry a two-name surface forward.
- Update all tests to use the new name.

### 2. `jira_get_boards` fix

Signal S2: `'Jira' object has no attribute 'boards'` at `src/a2atlassian/jira/boards.py:45`.

- Spike: check `atlassian-python-api`'s pinned version (`uv.lock`). Expected: the Agile method is named `get_all_agile_boards` (or similar), not `boards`. Same check for `get_issues_for_board` (line 78).
- Apply the correct method name.
- Audit `sprints.py` and any other Agile-endpoint callers for the same rot; fix together.
- Fallback (only if the library's method names are unstable across versions): call raw REST via `client._jira.get("rest/agile/1.0/board", ...)`.

### 3. `jira_search` field defaults + `jira_search_count`

S7: broad JQL returns full fields-per-ticket and blows the token ceiling.

- `search()` in `src/a2atlassian/jira/issues.py` grows a `fields: list[str] | None = None` parameter.
  - `None` → pass minimal defaults to `_jira.jql()`: `["summary", "status", "assignee", "priority", "issuetype", "parent", "updated"]`.
  - `["*all"]` → omit `fields=` (full payload escape hatch).
  - Explicit list → pass through.
- The `jira_search` MCP tool mirrors the parameter, with a docstring note about `fields=["*all"]` being large.
- New tool `jira_search_count(connection, jql)` — thin wrapper calling `_jira.jql(jql, limit=0)`, returns `{jql, total}` as JSON (single-entity response per the codebase-wide format rule).

Breaking change: anyone bypassing `_extract_issue_summary` and consuming `_jira.jql()` raw payload sees a trimmed shape. Documented in changelog; no major bump (pre-1.0).

### 4. Unified `jira_get_worklogs` (raw + summary modes)

Merges the existing per-issue `jira_get_worklogs` and the new S8 daily-summary tool into one:

```python
jira_get_worklogs(
    connection: str,
    issue_key: str | None = None,      # raw mode: per-worklog dump for this ticket
    date_from: str | None = None,      # summary mode: ISO date, start of range
    date_to: str | None = None,        # summary mode: ISO date, end (defaults to date_from)
    people: list[str] | None = None,
    jql_scope: str | None = None,
    detail: Literal["auto", "raw", "total", "by_day", "by_ticket"] = "auto",
    format: Literal["toon", "json"] = "toon",
) -> str
```

**Mode selection** — fully enumerated:

| `issue_key` | `date_from` | Mode | Behavior |
|---|---|---|---|
| set | unset | raw | per-worklog dump for the ticket, unfiltered |
| set | set | raw | per-worklog dump for the ticket, filtered to `[date_from, date_to]` in the connection's TZ |
| unset | set | summary | aggregated per attribution rules across scope |
| unset | unset | error | enricher returns: "Provide either issue_key (raw mode) or date_from (summary mode)." |

`detail="auto"` resolves to `raw` when `issue_key` is set, `by_day` otherwise. Explicit `detail` values override.

**Attribution rules (summary mode)** — addresses S8's worklog-author misattribution. Rules evaluated in order; first match wins:

| Order | Case | Attributed to | `source` string |
|---|---|---|---|
| 1 | `logger == assignee` | assignee | `"self"` |
| 2 | `logger ∈ worklog_admins` | assignee | `"proxy:<logger_name>"` |
| 3 | `logger ∉ admins, logger != assignee` | logger | `"non-admin-other"` |

The order matters: if the assignee is themselves in `worklog_admins` and logs their own time, rule 1 fires (`"self"`), not rule 2.

**New connection fields** (optional, in the TOML):

```toml
timezone = "Europe/Istanbul"          # IANA name; default "UTC"
worklog_admins = ["denis@..."]        # default []
```

Day boundaries computed in the connection's timezone. Per-call `tz` override available but rarely needed. CLI accepts common aliases (`--tz CET`, `--tz ET`) and resolves to IANA via `zoneinfo`.

**Return shape (summary mode, JSON).** Three `detail` levels:

- `total` — `{person, total_hours}` rows.
- `by_day` — `{person, date, hours}` rows. **Default.**
- `by_ticket` — `{person, date, key, hours, source}` rows with `source` as a flat string (`"self"` / `"proxy:Denis"` / `"non-admin-other"`).

Every level flat-table in TOON; `by_ticket` keeps attribution readable via the stringified source. Response echoes `tz` for audit.

**JQL shape for finding in-scope tickets:**

```
{jql_scope or f"project = {project_key}"} AND worklogDate >= "{date_from}" AND worklogDate <= "{date_to}"
```

Critical: query by `worklogDate`, not `worklogAuthor` — that's the fix for the proxy-logging blind spot.

### 5. Tool-surface consolidation

**Delete:**

- `jira_get_issue_dev_info` — placeholder that returns a static "not supported" string.
- `jira_link_to_epic` — folded into `jira_create_issue_link` by passing `link_type="Epic"`.
- `jira_add_watcher` + `jira_remove_watcher` — replaced by `jira_set_watchers(issue_key, add=[], remove=[])`.
- `jira_get_project_components` + `jira_get_project_versions` — folded into `jira_get_project_metadata(project_key, include=["components", "versions"])` with an `"all"` sentinel.

**Keep:** `jira_get_board_issues` and `jira_get_sprint_issues`. Kanban boards are filter-backed; JQL can't cleanly replicate a board's filter without fetching it first. Worth the two dedicated tools.

**Net:** 37 → 34 tools (18 read + 16 write + 3 connection management today; -6 deletions + 3 additions). Smaller absolute change than the boilerplate reduction, but removes a class of redundant tools from agent discovery.

### 6. `@mcp_tool` decorator + enum validation

Every current tool repeats the same shape:

```python
client = get_client(connection)
try:
    result = await <op>(client, ...)
except Exception as exc:
    return enricher.enrich(str(exc), {"connection": connection})
return format_result(result, fmt=format)
```

Extract to `@mcp_tool` in `src/a2atlassian/decorators.py`:

- Wraps the try/except → `enricher.enrich` → `format_result` pipeline.
- Inspects function type hints. Any parameter typed `Literal["a", "b", ...]` (e.g. `format`, `detail`, `content_format`, `page_width`) is validated at call time.
- Invalid values return: `"Invalid value for 'format': 'tooon'. Expected one of: toon, json."`
- New enricher method `enum_mismatch(param, value, choices)` for phrasing consistency.

Removes ~5 lines × ~34 tools = ~170 lines of boilerplate. Catches a whole class of agent typos silently.

### 7. MCP server instructions + docstring updates

S12, S9 — documentation hygiene:

- `mcp_server.py` `instructions=` string currently claims "work with Jira and Confluence" — but only Jira ships today. **Replace** the opening phrase so the scope is honest: drop the Confluence mention and add `"Scope today: Jira only. For Confluence, use mcp__atlassian (sooperset)."` Shortens ToolSearch discovery loops observed in session traces. Also update the parameter-name sentence to reflect the rename from section 1 (`"Connections are identified by a connection name"` rather than `"by project name"`).
- Same note at the top of README.md.
- Every list-returning tool docstring: append `"Returns TOON by default (compact); pass format='json' for standard JSON shape."`

Restore the Confluence mention and remove the "Jira only" caveat as part of the v0.4.0 Confluence release.

### 8. Error enrichment (residual from S1)

Even after the rename in section 1, an invalid connection name should surface helpful context:

```
Connection not found: protae

Available connections: protea, foo
Did you mean: protea?
Run `a2atlassian list` to see saved connections, or `a2atlassian login` to add one.
```

Route both the store-level `FileNotFoundError` and the scope-filter error in `mcp_server._get_connection` through the enricher. New enricher method `connection_not_found(name, available)`.

---

## Testing

- **S2 fix:** extend `tests/jira/test_boards.py` to mock the new accessor. Re-record `tests/fixtures/jira_boards.json` from real Jira Cloud via the existing fixture script. Sprint/worklog modules — add fixture-driven regression tests if Agile-endpoint rot touches them.
- **Search defaults:** extend `tests/jira/test_issues.py::TestSearch`; assert default and override behavior on `fields=`. New `TestSearchCount`.
- **Worklogs (two-mode):** new `tests/jira/test_worklogs.py::TestDailyHours` covers each attribution rule × each `detail` level. New fixture `jira_worklogs_proxy.json` with one ticket + three worklogs (self / admin-proxy / non-admin-other). Timezone boundary case: worklog at 23:59 UTC landing on different local day.
- **Decorator:** new `tests/test_decorators.py::TestMcpTool` covers the happy path, exception enrichment, and enum validation errors.
- **Tool-surface deletions:** update `tests/test_mcp_server.py` to confirm the deleted tool names no longer register.
- **Connection rename:** update every test calling a tool with `project=...` to `connection=...`. No alias path to test.
- **Connection fields:** extend `tests/test_connections.py` for `timezone` and `worklog_admins` round-trip. Assert CLI alias resolution (`--tz CET` → `Europe/Paris`).

---

## Release shape

- Single release, **v0.3.0**. Loud changelog on the rename and the S7 field-default change — both are the kind of breaking change that silently confuses a consumer if they miss the note.
- Ships before v0.4.0 (Confluence).
- Target completion: 2–3 focused days.

---

## Out of scope

- All Confluence work (S3, S4, S5, S11). Separate spec.
- S6 — sooperset content-contamination. Upstream filing only, no code here.
- S10 — claude-code file-state friction. Not our codebase.
- Prompt/workflow-side Protea fixes (S2210 D–I). Not our codebase.

---

## Open contingencies

1. The S2 fix approach depends on the atlassian-python-api version's actual surface. If the library exposes Agile endpoints through a distinct client class rather than just different method names, switch to approach 2 from the brainstorm (lazy `_agile` on `AtlassianClient`). Decide after the spike, not before.
2. If the `@mcp_tool` decorator's type-hint introspection runs into FastMCP's own schema introspection at registration time, fall back to explicit `enum=[...]` kwargs on the decorator. Known-good path; slightly less ergonomic.
