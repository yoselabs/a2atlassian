"""Tests for Jira board operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.boards import get_board_issues, get_boards


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


class TestGetBoards:
    async def test_returns_boards_from_values(self, mock_client: AtlassianClient) -> None:
        """boards() returns {"values": [...]} dict."""
        mock_client._jira_instance.boards.return_value = {
            "values": [
                {"id": 1, "name": "My Board", "type": "scrum", "location": {"projectKey": "PROJ"}},
                {"id": 2, "name": "Kanban", "type": "kanban", "location": {"projectKey": "KAN"}},
            ],
        }
        result = await get_boards(mock_client)
        assert isinstance(result, OperationResult)
        assert result.count == 2
        assert result.data[0]["id"] == "1"
        assert result.data[0]["name"] == "My Board"
        assert result.data[0]["type"] == "scrum"
        assert result.data[0]["project_key"] == "PROJ"
        assert result.data[1]["id"] == "2"
        assert result.data[1]["type"] == "kanban"

    async def test_returns_boards_from_list(self, mock_client: AtlassianClient) -> None:
        """boards() may return a plain list."""
        mock_client._jira_instance.boards.return_value = [
            {"id": 10, "name": "Board X", "type": "scrum", "location": {"projectKey": "X"}},
        ]
        result = await get_boards(mock_client)
        assert result.count == 1
        assert result.data[0]["id"] == "10"
        assert result.data[0]["name"] == "Board X"

    async def test_handles_dict_type(self, mock_client: AtlassianClient) -> None:
        """type can be a dict with a name key."""
        mock_client._jira_instance.boards.return_value = {
            "values": [
                {"id": 3, "name": "B", "type": {"name": "kanban"}, "location": {"projectKey": "K"}},
            ],
        }
        result = await get_boards(mock_client)
        assert result.data[0]["type"] == "kanban"

    async def test_handles_missing_location(self, mock_client: AtlassianClient) -> None:
        """location may be absent."""
        mock_client._jira_instance.boards.return_value = {
            "values": [
                {"id": 4, "name": "No Loc", "type": "scrum"},
            ],
        }
        result = await get_boards(mock_client)
        assert result.data[0]["project_key"] == ""

    async def test_handles_string_location(self, mock_client: AtlassianClient) -> None:
        """atlassian-python-api may transform location to a string."""
        mock_client._jira_instance.boards.return_value = {
            "values": [
                {"id": 5, "name": "Str Loc", "type": "scrum", "location": "PROJ"},
            ],
        }
        result = await get_boards(mock_client)
        assert result.data[0]["project_key"] == "PROJ"

    async def test_empty_boards(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.boards.return_value = {"values": []}
        result = await get_boards(mock_client)
        assert result.count == 0
        assert result.data == []


class TestGetBoardIssues:
    async def test_returns_issues(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_issues_for_board.return_value = {
            "issues": [
                {"key": "PROJ-1", "fields": {"summary": "First", "status": {"name": "Open"}}},
                {"key": "PROJ-2", "fields": {"summary": "Second", "status": {"name": "Done"}}},
            ],
            "total": 2,
        }
        result = await get_board_issues(mock_client, board_id=1)
        assert isinstance(result, OperationResult)
        assert result.count == 2
        assert result.data[0]["key"] == "PROJ-1"
        assert result.data[1]["key"] == "PROJ-2"

    async def test_pagination_params(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_issues_for_board.return_value = {"issues": [], "total": 0}
        await get_board_issues(mock_client, board_id=1, limit=25, offset=10)
        mock_client._jira_instance.get_issues_for_board.assert_called_once_with(1, startAt=10, maxResults=25)

    async def test_truncation_flag(self, mock_client: AtlassianClient) -> None:
        issues = [{"key": f"PROJ-{i}", "fields": {"summary": f"Issue {i}"}} for i in range(50)]
        mock_client._jira_instance.get_issues_for_board.return_value = {
            "issues": issues,
            "total": 100,
        }
        result = await get_board_issues(mock_client, board_id=1, limit=50)
        assert result.truncated is True
