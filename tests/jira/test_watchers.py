"""Tests for Jira watcher operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.watchers import add_watcher, get_watchers, remove_watcher


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


class TestGetWatchers:
    async def test_returns_watchers_from_dict(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_get_watchers.return_value = {
            "watchers": [
                {"accountId": "abc123", "displayName": "Alice"},
                {"accountId": "def456", "displayName": "Bob"},
            ]
        }
        result = await get_watchers(mock_client, "PROJ-1")
        assert isinstance(result, OperationResult)
        assert result.count == 2
        assert result.data[0]["account_id"] == "abc123"
        assert result.data[0]["display_name"] == "Alice"
        assert result.data[1]["account_id"] == "def456"

    async def test_returns_watchers_from_list(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_get_watchers.return_value = [
            {"accountId": "abc123", "displayName": "Alice"},
        ]
        result = await get_watchers(mock_client, "PROJ-1")
        assert result.count == 1
        assert result.data[0]["display_name"] == "Alice"

    async def test_handles_int_account_id(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_get_watchers.return_value = {"watchers": [{"accountId": 12345, "displayName": "Alice"}]}
        result = await get_watchers(mock_client, "PROJ-1")
        assert result.data[0]["account_id"] == "12345"

    async def test_empty_watchers(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_get_watchers.return_value = {"watchers": []}
        result = await get_watchers(mock_client, "PROJ-1")
        assert result.count == 0
        assert result.data == []


class TestAddWatcher:
    async def test_adds_watcher(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_add_watcher.return_value = None
        result = await add_watcher(mock_client, "PROJ-1", "abc123")
        assert isinstance(result, OperationResult)
        assert result.data["issue_key"] == "PROJ-1"
        assert result.data["account_id"] == "abc123"
        assert result.data["status"] == "added"
        mock_client._jira_instance.issue_add_watcher.assert_called_once_with("PROJ-1", "abc123")


class TestRemoveWatcher:
    async def test_removes_watcher(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_remove_watcher.return_value = None
        result = await remove_watcher(mock_client, "PROJ-1", "abc123")
        assert isinstance(result, OperationResult)
        assert result.data["issue_key"] == "PROJ-1"
        assert result.data["account_id"] == "abc123"
        assert result.data["status"] == "removed"
        mock_client._jira_instance.issue_remove_watcher.assert_called_once_with("PROJ-1", "abc123")
