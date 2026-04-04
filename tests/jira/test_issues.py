"""Tests for Jira issue operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.issues import get_issue, search


@pytest.fixture
def mock_client() -> AtlassianClient:
    conn = ConnectionInfo(
        project="test",
        url="https://test.atlassian.net",
        email="t@t.com",
        token="tok",
        read_only=True,
    )
    client = AtlassianClient(conn)
    client._jira_instance = MagicMock()
    return client


class TestGetIssue:
    async def test_returns_operation_result(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue.return_value = {
            "key": "PROJ-1",
            "fields": {
                "summary": "Test issue",
                "status": {"name": "In Progress"},
                "assignee": {"displayName": "Alice"},
            },
        }
        result = await get_issue(mock_client, "PROJ-1")
        assert isinstance(result, OperationResult)
        assert result.data["key"] == "PROJ-1"
        assert result.count == 1
        assert result.truncated is False
        assert result.time_ms >= 0

    async def test_passes_issue_key(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue.return_value = {"key": "PROJ-1", "fields": {}}
        await get_issue(mock_client, "PROJ-1")
        mock_client._jira_instance.issue.assert_called_once_with("PROJ-1")


class TestSearch:
    async def test_returns_list_result(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.jql.return_value = {
            "issues": [
                {"key": "PROJ-1", "fields": {"summary": "First"}},
                {"key": "PROJ-2", "fields": {"summary": "Second"}},
            ],
            "total": 2,
        }
        result = await search(mock_client, "project = PROJ", limit=50)
        assert isinstance(result, OperationResult)
        assert len(result.data) == 2
        assert result.count == 2

    async def test_truncation_flag(self, mock_client: AtlassianClient) -> None:
        issues = [{"key": f"PROJ-{i}", "fields": {"summary": f"Issue {i}"}} for i in range(50)]
        mock_client._jira_instance.jql.return_value = {
            "issues": issues,
            "total": 100,
        }
        result = await search(mock_client, "project = PROJ", limit=50)
        assert result.truncated is True

    async def test_pagination_params(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.jql.return_value = {"issues": [], "total": 0}
        await search(mock_client, "project = PROJ", limit=25, offset=10)
        mock_client._jira_instance.jql.assert_called_once_with("project = PROJ", limit=25, start=10)
