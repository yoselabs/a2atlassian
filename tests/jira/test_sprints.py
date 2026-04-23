"""Tests for Jira sprint operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.sprints import (
    add_issues_to_sprint,
    create_sprint,
    get_sprint_issues,
    get_sprints,
    update_sprint,
)


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


class TestGetSprints:
    async def test_returns_sprints_from_values(self, mock_client: AtlassianClient) -> None:
        """get_all_sprints_from_board returns {"values": [...]}."""
        mock_client._jira_instance.get_all_sprints_from_board.return_value = {
            "values": [
                {"id": 1, "name": "Sprint 1", "state": "active", "startDate": "2026-04-01", "endDate": "2026-04-14"},
                {"id": 2, "name": "Sprint 2", "state": "future", "startDate": "", "endDate": ""},
            ],
        }
        result = await get_sprints(mock_client, board_id=10)
        assert isinstance(result, OperationResult)
        assert result.count == 2
        assert result.data[0]["id"] == "1"
        assert result.data[0]["name"] == "Sprint 1"
        assert result.data[0]["state"] == "active"
        assert result.data[0]["start_date"] == "2026-04-01"
        assert result.data[0]["end_date"] == "2026-04-14"
        assert result.data[1]["state"] == "future"

    async def test_returns_sprints_from_list(self, mock_client: AtlassianClient) -> None:
        """Response may be a plain list."""
        mock_client._jira_instance.get_all_sprints_from_board.return_value = [
            {"id": 3, "name": "Sprint 3", "state": "closed", "startDate": "2026-03-01", "endDate": "2026-03-14"},
        ]
        result = await get_sprints(mock_client, board_id=10)
        assert result.count == 1
        assert result.data[0]["state"] == "closed"

    async def test_handles_missing_state(self, mock_client: AtlassianClient) -> None:
        """state may be missing entirely."""
        mock_client._jira_instance.get_all_sprints_from_board.return_value = {
            "values": [
                {"id": 4, "name": "Sprint 4", "startDate": "", "endDate": ""},
            ],
        }
        result = await get_sprints(mock_client, board_id=10)
        assert result.data[0]["state"] == ""

    async def test_handles_int_id(self, mock_client: AtlassianClient) -> None:
        """id is cast to string."""
        mock_client._jira_instance.get_all_sprints_from_board.return_value = {
            "values": [
                {"id": 99, "name": "S", "state": "future"},
            ],
        }
        result = await get_sprints(mock_client, board_id=10)
        assert result.data[0]["id"] == "99"

    async def test_empty_sprints(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_all_sprints_from_board.return_value = {"values": []}
        result = await get_sprints(mock_client, board_id=10)
        assert result.count == 0
        assert result.data == []


class TestGetSprintIssues:
    async def test_returns_issues(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_sprint_issues.return_value = {
            "issues": [
                {"key": "PROJ-1", "fields": {"summary": "First", "status": {"name": "Open"}}},
                {"key": "PROJ-2", "fields": {"summary": "Second", "status": {"name": "Done"}}},
            ],
            "total": 2,
        }
        result = await get_sprint_issues(mock_client, sprint_id=1)
        assert isinstance(result, OperationResult)
        assert result.count == 2
        assert result.data[0]["key"] == "PROJ-1"

    async def test_pagination_params(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_sprint_issues.return_value = {"issues": [], "total": 0}
        await get_sprint_issues(mock_client, sprint_id=1, limit=25, offset=10)
        mock_client._jira_instance.get_sprint_issues.assert_called_once_with(1, startAt=10, maxResults=25)

    async def test_truncation_flag(self, mock_client: AtlassianClient) -> None:
        issues = [{"key": f"PROJ-{i}", "fields": {"summary": f"Issue {i}"}} for i in range(50)]
        mock_client._jira_instance.get_sprint_issues.return_value = {
            "issues": issues,
            "total": 100,
        }
        result = await get_sprint_issues(mock_client, sprint_id=1, limit=50)
        assert result.truncated is True


class TestCreateSprint:
    async def test_creates_sprint(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.create_sprint.return_value = {
            "id": 42,
            "name": "New Sprint",
            "state": "future",
            "startDate": "2026-04-15",
            "endDate": "2026-04-28",
        }
        result = await create_sprint(
            mock_client,
            name="New Sprint",
            board_id=10,
            start_date="2026-04-15",
            end_date="2026-04-28",
        )
        assert isinstance(result, OperationResult)
        assert result.data["id"] == "42"
        assert result.data["name"] == "New Sprint"
        assert result.data["state"] == "future"
        assert result.count == 1
        mock_client._jira_instance.create_sprint.assert_called_once_with(
            name="New Sprint", originBoardId=10, startDate="2026-04-15", endDate="2026-04-28"
        )

    async def test_creates_sprint_without_dates(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.create_sprint.return_value = {
            "id": 43,
            "name": "Dateless Sprint",
            "state": "future",
        }
        result = await create_sprint(mock_client, name="Dateless Sprint", board_id=10)
        assert result.data["name"] == "Dateless Sprint"
        assert result.data["start_date"] == ""
        assert result.data["end_date"] == ""


class TestUpdateSprint:
    async def test_updates_sprint(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.update_partially_sprint.return_value = {
            "id": 42,
            "name": "Renamed Sprint",
            "state": "active",
            "startDate": "2026-04-15",
            "endDate": "2026-04-28",
        }
        result = await update_sprint(
            mock_client,
            sprint_id=42,
            name="Renamed Sprint",
            state="active",
        )
        assert isinstance(result, OperationResult)
        assert result.data["name"] == "Renamed Sprint"
        assert result.data["state"] == "active"
        mock_client._jira_instance.update_partially_sprint.assert_called_once_with(42, name="Renamed Sprint", state="active")

    async def test_updates_sprint_non_dict_response(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.update_partially_sprint.return_value = None
        result = await update_sprint(mock_client, sprint_id=42, name="X")
        assert result.data["sprint_id"] == 42
        assert result.data["status"] == "updated"


class TestAddIssuesToSprint:
    async def test_adds_issues(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.add_issues_to_sprint.return_value = None
        result = await add_issues_to_sprint(mock_client, sprint_id=42, issue_keys=["PROJ-1", "PROJ-2"])
        assert isinstance(result, OperationResult)
        assert result.data["sprint_id"] == 42
        assert result.data["issue_keys"] == "PROJ-1, PROJ-2"
        assert result.data["status"] == "added"
        assert result.count == 2
        mock_client._jira_instance.add_issues_to_sprint.assert_called_once_with(42, ["PROJ-1", "PROJ-2"])
