#!/usr/bin/env python3
"""Record real Jira API responses as fixture files.

Usage:
    A2ATLASSIAN_TEST_URL=https://test.atlassian.net \
    A2ATLASSIAN_TEST_EMAIL=user@example.com \
    A2ATLASSIAN_TEST_TOKEN=... \
    A2ATLASSIAN_TEST_PROJECT=TEST \
    A2ATLASSIAN_TEST_ISSUE=TEST-1 \
    A2ATLASSIAN_TEST_BOARD_ID=1 \
    A2ATLASSIAN_TEST_SPRINT_ID=1 \
    A2ATLASSIAN_TEST_FIELD_ID=customfield_10000 \
    A2ATLASSIAN_TEST_ACCOUNT_ID=712020:... \
    python scripts/record_fixtures.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        print(f"WARNING: {name} not set, skipping related fixtures")
    return value


# --- Anonymization ---


class _AnonState:
    """Mutable counter state for anonymization mappings."""

    def __init__(self) -> None:
        self.counter = 0
        self.account_ids: dict[str, str] = {}
        self.names: dict[str, str] = {}

    def anon_account_id(self, raw: str) -> str:
        if raw not in self.account_ids:
            self.counter += 1
            self.account_ids[raw] = f"user-{self.counter:03d}"
        return self.account_ids[raw]

    def anon_name(self, raw: str) -> str:
        if raw not in self.names:
            self.counter += 1
            self.names[raw] = f"Test User {self.counter}"
        return self.names[raw]


_state = _AnonState()

_ANON_URL = "https://test.atlassian.net"


def _anonymize_str(data: str, base_url: str) -> str:
    if base_url and base_url in data:
        data = data.replace(base_url, _ANON_URL)
    data = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "user@example.com", data)
    return re.sub(r"712020:[a-f0-9-]+", lambda m: _state.anon_account_id(m.group()), data)


def _anonymize_url_field(v: Any, base_url: str) -> Any:
    if isinstance(v, str) and base_url:
        return v.replace(base_url, _ANON_URL)
    if isinstance(v, dict):
        return {kk: vv.replace(base_url, _ANON_URL) if isinstance(vv, str) else vv for kk, vv in v.items()}
    return v


def anonymize(data: Any, base_url: str) -> Any:
    """Recursively anonymize PII in API response data."""
    if isinstance(data, str):
        return _anonymize_str(data, base_url)
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k == "accountId" and isinstance(v, str) and ("712020:" in v or len(v) > 20):
                result[k] = _state.anon_account_id(v)
            elif k == "displayName" and isinstance(v, str):
                result[k] = _state.anon_name(v)
            elif k == "emailAddress" and isinstance(v, str):
                result[k] = "user@example.com"
            elif k in ("avatarUrls", "self") and isinstance(v, (str, dict)):
                result[k] = _anonymize_url_field(v, base_url)
            else:
                result[k] = anonymize(v, base_url)
        return result
    if isinstance(data, list):
        return [anonymize(item, base_url) for item in data]
    return data


def _build_meta(api_method: str, args: list[str]) -> dict[str, Any]:
    from importlib.metadata import version  # noqa: PLC0415

    return {
        "recorded_at": datetime.now(UTC).isoformat(),
        "library_version": version("atlassian-python-api"),
        "api_method": api_method,
        "args": args,
        "cloud": True,
    }


def _wrap_with_meta(data: Any, api_method: str, args: list[str]) -> Any:
    meta = _build_meta(api_method, args)
    if isinstance(data, dict):
        return {"_meta": meta, **data}
    if isinstance(data, list):
        return {"_meta": meta, "items": data}
    return {"_meta": meta, "value": data}


async def _record(
    output_dir: Path,
    url: str,
    filename: str,
    method_name: str,
    args_desc: list[str],
    coro: Any,
) -> None:
    try:
        data = await coro
        data = anonymize(data, url)
        data = _wrap_with_meta(data, method_name, args_desc)
        (output_dir / filename).write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False))
        print(f"  OK  {filename}")
    except Exception as exc:
        print(f"  FAIL {filename}: {exc}")


async def _record_issue_fixtures(client: AtlassianClient, output_dir: Path, url: str, issue_key: str) -> None:
    r = lambda f, m, a, c: _record(output_dir, url, f, m, a, c)  # noqa: E731
    await r("jira_issue.json", "client._jira.issue", [issue_key], client._call(client._jira.issue, issue_key))
    await r(
        "jira_transitions.json",
        "client._jira.get_issue_transitions",
        [issue_key],
        client._call(client._jira.get_issue_transitions, issue_key),
    )
    await r(
        "jira_comments.json",
        "client._jira.issue_get_comments",
        [issue_key],
        client._call(client._jira.issue_get_comments, issue_key),
    )
    await r(
        "jira_watchers.json",
        "client._jira.issue_get_watchers",
        [issue_key],
        client._call(client._jira.issue_get_watchers, issue_key),
    )
    await r(
        "jira_worklogs.json",
        "client._jira.issue_get_worklog",
        [issue_key],
        client._call(client._jira.issue_get_worklog, issue_key),
    )


async def _record_project_fixtures(client: AtlassianClient, output_dir: Path, url: str, project: str) -> None:
    r = lambda f, m, a, c: _record(output_dir, url, f, m, a, c)  # noqa: E731
    await r(
        "jira_search.json",
        "client._jira.jql",
        [f"project = {project}"],
        client._call(client._jira.jql, f"project = {project}", limit=5),
    )
    await r("jira_projects.json", "client._jira.projects", [], client._call(client._jira.projects))
    await r(
        "jira_project_versions.json",
        "client._jira.get_project_versions",
        [project],
        client._call(client._jira.get_project_versions, project),
    )
    await r(
        "jira_project_components.json",
        "client._jira.get_project_components",
        [project],
        client._call(client._jira.get_project_components, project),
    )


async def _record_create_issue(client: AtlassianClient, output_dir: Path, url: str, project: str) -> None:
    """Create a temporary issue, record the response, then delete it."""
    try:
        data = await client._call(
            client._jira.create_issue,
            fields={
                "project": {"key": project},
                "summary": "A2AT-fixture-recording-temp",
                "issuetype": {"name": "Task"},
            },
        )
        data = anonymize(data, url)
        data = _wrap_with_meta(data, "client._jira.create_issue", ["fields={...}"])
        (output_dir / "jira_create_issue_response.json").write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False))
        print("  OK  jira_create_issue_response.json")
        key = data.get("key", "")
        if key:
            await client._call(client._jira.delete_issue, key)
            print(f"  (cleaned up {key})")
    except Exception as exc:
        print(f"  FAIL jira_create_issue_response.json: {exc}")


async def record_all() -> None:
    """Record all fixture files from a live Jira instance."""
    url = _env("A2ATLASSIAN_TEST_URL")
    email = _env("A2ATLASSIAN_TEST_EMAIL")
    token = _env("A2ATLASSIAN_TEST_TOKEN")
    project = _env("A2ATLASSIAN_TEST_PROJECT")
    issue_key = _env("A2ATLASSIAN_TEST_ISSUE")
    board_id = _env("A2ATLASSIAN_TEST_BOARD_ID")
    sprint_id = _env("A2ATLASSIAN_TEST_SPRINT_ID")
    field_id = _env("A2ATLASSIAN_TEST_FIELD_ID")
    account_id = _env("A2ATLASSIAN_TEST_ACCOUNT_ID")

    if not all([url, email, token]):
        print("ERROR: A2ATLASSIAN_TEST_URL, _EMAIL, _TOKEN are required")
        sys.exit(1)

    conn = ConnectionInfo(connection="recorder", url=url, email=email, token=token, read_only=True)
    client = AtlassianClient(conn)

    output_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    output_dir.mkdir(parents=True, exist_ok=True)

    r = lambda f, m, a, c: _record(output_dir, url, f, m, a, c)  # noqa: E731

    print("Recording fixtures...")

    if issue_key:
        await _record_issue_fixtures(client, output_dir, url, issue_key)

    if project:
        await _record_project_fixtures(client, output_dir, url, project)

    await r("jira_fields.json", "client._jira.get_all_fields", [], client._call(client._jira.get_all_fields))
    await r("jira_link_types.json", "client._jira.get_issue_link_types", [], client._call(client._jira.get_issue_link_types))
    await r("jira_boards.json", "client._jira.get_all_agile_boards", [], client._call(client._jira.get_all_agile_boards))

    if board_id:
        bid = int(board_id)
        await r(
            "jira_sprints.json",
            "client._jira.get_all_sprints_from_board",
            [board_id],
            client._call(client._jira.get_all_sprints_from_board, bid),
        )

    if sprint_id:
        sid = int(sprint_id)
        await r(
            "jira_sprint_issues.json",
            "client._jira.get_sprint_issues",
            [sprint_id],
            client._call(client._jira.get_sprint_issues, sid, 0, 5),
        )

    if field_id:
        await r(
            "jira_field_options.json",
            "client._jira.get_custom_field_option",
            [field_id],
            client._call(client._jira.get_custom_field_option, field_id),
        )

    if account_id:
        await r(
            "jira_user.json",
            "client._jira.user",
            [account_id],
            client._call(client._jira.user, account_id=account_id),
        )

    if project:
        await _record_create_issue(client, output_dir, url, project)

    print("Done.")


if __name__ == "__main__":
    asyncio.run(record_all())
