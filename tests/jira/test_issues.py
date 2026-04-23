"""Tests for Jira issue operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.issues import create_issue, delete_issue, get_issue, search, update_issue


@pytest.fixture
def mock_client() -> AtlassianClient:
    conn = ConnectionInfo(
        connection="test",
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
                "status": {"name": "In Progress", "statusCategory": {"name": "In Progress"}},
                "assignee": {"displayName": "Alice"},
                "reporter": {"displayName": "Bob"},
                "priority": {"name": "High"},
                "issuetype": {"name": "Story"},
            },
        }
        result = await get_issue(mock_client, "PROJ-1")
        assert isinstance(result, OperationResult)
        assert result.data["key"] == "PROJ-1"
        assert result.data["summary"] == "Test issue"
        assert result.data["status"] == "In Progress"
        assert result.data["assignee"] == "Alice"
        assert result.data["reporter"] == "Bob"
        assert result.data["priority"] == "High"
        assert result.data["type"] == "Story"
        assert result.count == 1
        assert result.truncated is False
        assert result.time_ms >= 0

    async def test_passes_issue_key(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue.return_value = {"key": "PROJ-1", "fields": {}}
        await get_issue(mock_client, "PROJ-1")
        mock_client._jira_instance.issue.assert_called_once_with("PROJ-1")

    async def test_handles_null_fields(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue.return_value = {
            "key": "PROJ-1",
            "fields": {
                "summary": "Test",
                "status": None,
                "assignee": None,
                "priority": None,
                "issuetype": None,
            },
        }
        result = await get_issue(mock_client, "PROJ-1")
        assert result.data["status"] == ""
        assert result.data["assignee"] == ""


class TestSearch:
    async def test_returns_list_result(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.jql.return_value = {
            "issues": [
                {"key": "PROJ-1", "fields": {"summary": "First", "status": {"name": "Open"}}},
                {"key": "PROJ-2", "fields": {"summary": "Second", "status": {"name": "Done"}}},
            ],
            "total": 2,
        }
        result = await search(mock_client, "project = PROJ", limit=50)
        assert isinstance(result, OperationResult)
        assert len(result.data) == 2
        assert result.count == 2
        assert result.data[0]["key"] == "PROJ-1"
        assert result.data[0]["summary"] == "First"
        assert result.data[0]["status"] == "Open"

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


class TestCreateIssue:
    async def test_creates_issue(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.create_issue.return_value = {
            "id": "10001",
            "key": "PROJ-42",
            "self": "https://test.atlassian.net/rest/api/2/issue/10001",
        }
        result = await create_issue(mock_client, "PROJ", "New task", "Story")
        assert isinstance(result, OperationResult)
        assert result.data["key"] == "PROJ-42"
        assert result.data["id"] == "10001"
        assert result.data["status"] == "created"
        assert result.count == 1
        mock_client._jira_instance.create_issue.assert_called_once_with(
            fields={
                "project": {"key": "PROJ"},
                "summary": "New task",
                "issuetype": {"name": "Story"},
            }
        )

    async def test_creates_issue_with_description(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.create_issue.return_value = {
            "id": "10002",
            "key": "PROJ-43",
        }
        result = await create_issue(mock_client, "PROJ", "With desc", "Bug", description="Details here")
        assert result.data["key"] == "PROJ-43"
        call_fields = mock_client._jira_instance.create_issue.call_args[1]["fields"]
        assert call_fields["description"] == "Details here"

    async def test_creates_issue_with_extra_fields(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.create_issue.return_value = {
            "id": "10003",
            "key": "PROJ-44",
        }
        extra = {"priority": {"name": "High"}, "labels": ["urgent"]}
        result = await create_issue(mock_client, "PROJ", "Extra", "Task", extra_fields=extra)
        assert result.data["key"] == "PROJ-44"
        call_fields = mock_client._jira_instance.create_issue.call_args[1]["fields"]
        assert call_fields["priority"] == {"name": "High"}
        assert call_fields["labels"] == ["urgent"]

    async def test_handles_int_id(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.create_issue.return_value = {
            "id": 10004,
            "key": "PROJ-45",
        }
        result = await create_issue(mock_client, "PROJ", "Int ID", "Task")
        assert result.data["id"] == "10004"


class TestUpdateIssue:
    async def test_updates_issue(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.update_issue_field.return_value = None
        result = await update_issue(mock_client, "PROJ-1", {"summary": "Updated"})
        assert isinstance(result, OperationResult)
        assert result.data["issue_key"] == "PROJ-1"
        assert result.data["status"] == "updated"
        mock_client._jira_instance.update_issue_field.assert_called_once_with("PROJ-1", {"summary": "Updated"})


class TestDeleteIssue:
    async def test_deletes_issue(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.delete_issue.return_value = None
        result = await delete_issue(mock_client, "PROJ-1")
        assert isinstance(result, OperationResult)
        assert result.data["issue_key"] == "PROJ-1"
        assert result.data["status"] == "deleted"
        mock_client._jira_instance.delete_issue.assert_called_once_with("PROJ-1")
