"""Tests for Jira worklog operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.worklogs import add_worklog, get_worklogs


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
