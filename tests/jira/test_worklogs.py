"""Tests for Jira worklog operations."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.errors import ErrorEnricher
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.worklogs import add_worklog, get_worklogs, get_worklogs_summary

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mock_client() -> AtlassianClient:
    conn = ConnectionInfo(
        connection="test",
        url="https://test.atlassian.net",
        email="t@t.com",
        token="tok",
        read_only=False,
    )
    client = AtlassianClient(conn)
    client._jira_instance = MagicMock()
    return client


class TestGetWorklogs:
    async def test_returns_worklogs_from_dict(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_get_worklog.return_value = {
            "worklogs": [
                {
                    "id": "100",
                    "author": {"displayName": "Alice"},
                    "timeSpent": "2h",
                    "started": "2026-01-01T09:00:00.000+0000",
                    "comment": "Working on feature",
                },
                {
                    "id": "101",
                    "author": {"displayName": "Bob"},
                    "timeSpent": "1h 30m",
                    "started": "2026-01-02T10:00:00.000+0000",
                    "comment": "",
                },
            ]
        }
        result = await get_worklogs(mock_client, "PROJ-1")
        assert isinstance(result, OperationResult)
        assert result.count == 2
        assert result.data[0]["id"] == "100"
        assert result.data[0]["author"] == "Alice"
        assert result.data[0]["time_spent"] == "2h"
        assert result.data[0]["comment"] == "Working on feature"
        assert result.data[1]["time_spent"] == "1h 30m"

    async def test_returns_worklogs_from_list(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_get_worklog.return_value = [
            {"id": "100", "author": {"displayName": "Alice"}, "timeSpent": "1h"},
        ]
        result = await get_worklogs(mock_client, "PROJ-1")
        assert result.count == 1
        assert result.data[0]["author"] == "Alice"

    async def test_handles_adf_comment(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_get_worklog.return_value = {
            "worklogs": [
                {
                    "id": "100",
                    "author": {"displayName": "Alice"},
                    "timeSpent": "1h",
                    "comment": {
                        "type": "doc",
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": "ADF comment"}]},
                        ],
                    },
                },
            ]
        }
        result = await get_worklogs(mock_client, "PROJ-1")
        assert result.data[0]["comment"] == "ADF comment"

    async def test_empty_worklogs(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_get_worklog.return_value = {"worklogs": []}
        result = await get_worklogs(mock_client, "PROJ-1")
        assert result.count == 0
        assert result.data == []


class TestAddWorklog:
    async def test_adds_worklog_with_response(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_worklog.return_value = {
            "id": "200",
            "author": {"displayName": "Alice"},
            "timeSpent": "2h 30m",
            "started": "2026-01-03T09:00:00.000+0000",
            "comment": "Completed task",
        }
        result = await add_worklog(mock_client, "PROJ-1", "2h 30m", comment="Completed task")
        assert isinstance(result, OperationResult)
        assert result.data["id"] == "200"
        assert result.data["time_spent"] == "2h 30m"
        assert result.data["comment"] == "Completed task"
        mock_client._jira_instance.issue_worklog.assert_called_once_with("PROJ-1", comment="Completed task", timeSpent="2h 30m")

    async def test_adds_worklog_with_none_response(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_worklog.return_value = None
        result = await add_worklog(mock_client, "PROJ-1", "1h")
        assert result.data["issue_key"] == "PROJ-1"
        assert result.data["time_spent"] == "1h"
        assert result.data["status"] == "added"

    async def test_adds_worklog_without_comment(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_worklog.return_value = None
        await add_worklog(mock_client, "PROJ-1", "3h")
        mock_client._jira_instance.issue_worklog.assert_called_once_with("PROJ-1", timeSpent="3h", comment=None)


class TestGetWorklogsSummary:
    @pytest.fixture
    def mock_proxy_client(self) -> AtlassianClient:
        """Client wired so jql returns the proxy-logged ticket and issue_get_worklog returns three worklogs."""
        fixture = json.loads((FIXTURES / "jira_worklogs_proxy.json").read_text())
        conn = ConnectionInfo(
            connection="test",
            url="https://test.atlassian.net",
            email="alice@example.com",
            token="tok",
            worklog_admins=("denis@example.com",),
            timezone="Europe/Istanbul",
        )
        client = AtlassianClient(conn)
        client._jira_instance = MagicMock()
        client._jira_instance.jql.return_value = {
            "issues": [
                {
                    "key": fixture["issue_key"],
                    "fields": {
                        "summary": "Test",
                        "status": {"name": "In Progress"},
                        "assignee": {"displayName": fixture["assignee_display_name"], "emailAddress": fixture["assignee_email"]},
                        "priority": {"name": "Medium"},
                        "issuetype": {"name": "Task"},
                    },
                }
            ],
            "total": 1,
        }
        client._jira_instance.issue_get_worklog.return_value = {"worklogs": fixture["worklogs"]}
        return client

    async def test_self_logged_hours_go_to_assignee(self, mock_proxy_client: AtlassianClient) -> None:
        """Alice logged 4h against PE0-42 (self) on 2026-04-22 -> 4h to Alice, source='self'."""
        result = await get_worklogs_summary(
            mock_proxy_client,
            date_from="2026-04-22",
            detail="by_ticket",
        )
        rows = result.data
        alice_self = [r for r in rows if r["person"] == "Alice" and r["source"] == "self"]
        assert len(alice_self) == 1
        assert alice_self[0]["hours"] == 4.0
        assert alice_self[0]["key"] == "PE0-42"

    async def test_admin_proxy_goes_to_assignee(self, mock_proxy_client: AtlassianClient) -> None:
        """Denis (admin) logged 1h against Alice's ticket -> 1h to Alice, source='proxy:Denis'."""
        result = await get_worklogs_summary(
            mock_proxy_client,
            date_from="2026-04-22",
            detail="by_ticket",
        )
        rows = result.data
        proxy_rows = [r for r in rows if r["person"] == "Alice" and r["source"].startswith("proxy:")]
        assert len(proxy_rows) == 1
        assert proxy_rows[0]["hours"] == 1.0
        assert proxy_rows[0]["source"] == "proxy:Denis"

    async def test_non_admin_other_goes_to_logger(self, mock_proxy_client: AtlassianClient) -> None:
        """Bob (not admin) logged 2h against Alice's ticket -> 2h to Bob, source='non-admin-other'."""
        result = await get_worklogs_summary(
            mock_proxy_client,
            date_from="2026-04-22",
            detail="by_ticket",
        )
        rows = result.data
        bob_rows = [r for r in rows if r["person"] == "Bob"]
        assert len(bob_rows) == 1
        assert bob_rows[0]["hours"] == 2.0
        assert bob_rows[0]["source"] == "non-admin-other"
        assert bob_rows[0]["key"] == "PE0-42"

    async def test_total_detail_aggregates(self, mock_proxy_client: AtlassianClient) -> None:
        result = await get_worklogs_summary(
            mock_proxy_client,
            date_from="2026-04-22",
            detail="total",
        )
        rows = {r["person"]: r["total_hours"] for r in result.data}
        assert rows == {"Alice": 5.0, "Bob": 2.0}

    async def test_by_day_detail(self, mock_proxy_client: AtlassianClient) -> None:
        result = await get_worklogs_summary(
            mock_proxy_client,
            date_from="2026-04-22",
            detail="by_day",
        )
        rows = result.data
        alice = [r for r in rows if r["person"] == "Alice"]
        assert len(alice) == 1
        assert alice[0]["date"] == "2026-04-22"
        assert alice[0]["hours"] == 5.0

    async def test_tz_boundary(self, mock_proxy_client: AtlassianClient) -> None:
        """A worklog at 23:30 UTC on 2026-04-22 is at 02:30 Istanbul on 2026-04-23 -- must land on 04-23."""
        mock_proxy_client._jira_instance.issue_get_worklog.return_value = {
            "worklogs": [
                {
                    "id": "late",
                    "author": {"displayName": "Alice", "emailAddress": "alice@example.com"},
                    "started": "2026-04-22T23:30:00.000+0000",
                    "timeSpentSeconds": 3600,
                }
            ],
        }
        result = await get_worklogs_summary(
            mock_proxy_client,
            date_from="2026-04-23",
            detail="by_day",
        )
        alice = [r for r in result.data if r["person"] == "Alice"]
        assert len(alice) == 1
        assert alice[0]["date"] == "2026-04-23"
        assert alice[0]["hours"] == 1.0


class TestTwoModeToolLogic:
    """Unit tests for the two-mode jira_get_worklogs MCP tool dispatch logic."""

    @pytest.fixture
    def real_client(self) -> AtlassianClient:
        """A real AtlassianClient with a mocked _jira_instance."""
        conn = ConnectionInfo(
            connection="test",
            url="https://test.atlassian.net",
            email="t@t.com",
            token="tok",
            read_only=False,
            timezone="UTC",
        )
        client = AtlassianClient(conn)
        client._jira_instance = MagicMock()
        return client

    @pytest.fixture
    def tool_fn(self, real_client):
        """Register jira_get_worklogs and return the wrapped coroutine."""
        from mcp.server.fastmcp import FastMCP

        from a2atlassian.jira_tools.worklogs import register_read

        srv = FastMCP("test")
        enricher = ErrorEnricher()
        register_read(srv, lambda _p: real_client, enricher)
        return srv._tool_manager._tools["jira_get_worklogs"].fn

    async def test_error_when_neither_issue_key_nor_date_from(self, tool_fn) -> None:
        """Neither issue_key nor date_from → enriched error string."""
        result = await tool_fn(connection="test")
        assert isinstance(result, str)
        assert "issue_key" in result or "date_from" in result or "raw mode" in result

    async def test_raw_mode_when_only_issue_key(self, tool_fn, real_client) -> None:
        """issue_key set, date_from unset → raw mode: issue_get_worklog called."""
        real_client._jira_instance.issue_get_worklog.return_value = {"worklogs": []}
        result = await tool_fn(connection="test", issue_key="PROJ-1")
        assert isinstance(result, str)
        real_client._jira_instance.issue_get_worklog.assert_called_once_with("PROJ-1")

    async def test_summary_mode_when_only_date_from(self, tool_fn, real_client) -> None:
        """date_from set, issue_key unset → summary mode: jql called."""
        real_client._jira_instance.jql.return_value = {"issues": [], "total": 0}
        result = await tool_fn(connection="test", date_from="2026-04-22")
        assert isinstance(result, str)
        real_client._jira_instance.jql.assert_called_once()

    async def test_raw_filtered_when_issue_key_and_date_from(self, tool_fn, real_client) -> None:
        """issue_key + date_from set → raw mode with date filter applied."""
        import json as _json

        real_client._jira_instance.issue_get_worklog.return_value = {
            "worklogs": [
                {
                    "id": "1",
                    "author": {"displayName": "Alice"},
                    "timeSpent": "2h",
                    "started": "2026-04-22T10:00:00.000+0000",
                    "comment": "",
                },
                {
                    "id": "2",
                    "author": {"displayName": "Bob"},
                    "timeSpent": "1h",
                    "started": "2026-04-23T10:00:00.000+0000",
                    "comment": "",
                },
            ]
        }
        # Request only date 2026-04-22 — only Alice's worklog should survive
        result = await tool_fn(connection="test", issue_key="PROJ-1", date_from="2026-04-22", date_to="2026-04-22", format="json")
        assert isinstance(result, str)
        parsed = _json.loads(result)
        assert parsed["count"] == 1
        assert parsed["data"][0]["author"] == "Alice"

    async def test_detail_raw_in_summary_mode_raises_error(self, tool_fn, real_client) -> None:
        """detail='raw' with date_from (summary mode) → enriched error string."""
        real_client._jira_instance.jql.return_value = {"issues": [], "total": 0}
        result = await tool_fn(connection="test", date_from="2026-04-22", detail="raw")
        assert isinstance(result, str)
        assert "raw" in result
