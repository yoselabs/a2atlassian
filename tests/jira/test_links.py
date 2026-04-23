"""Tests for Jira issue link operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.links import (
    create_issue_link,
    get_link_types,
    link_to_epic,
    remove_issue_link,
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


class TestGetLinkTypes:
    async def test_returns_link_types_from_dict(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_issue_link_types.return_value = {
            "issueLinkTypes": [
                {"id": "1", "name": "Blocks", "inward": "is blocked by", "outward": "blocks"},
                {"id": "2", "name": "Duplicate", "inward": "is duplicated by", "outward": "duplicates"},
            ]
        }
        result = await get_link_types(mock_client)
        assert isinstance(result, OperationResult)
        assert result.count == 2
        assert result.data[0]["id"] == "1"
        assert result.data[0]["name"] == "Blocks"
        assert result.data[0]["inward"] == "is blocked by"
        assert result.data[0]["outward"] == "blocks"

    async def test_returns_link_types_from_list(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_issue_link_types.return_value = [
            {"id": 10, "name": "Relates", "inward": "relates to", "outward": "relates to"},
        ]
        result = await get_link_types(mock_client)
        assert result.count == 1
        assert result.data[0]["id"] == "10"
        assert result.data[0]["name"] == "Relates"

    async def test_empty_link_types(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_issue_link_types.return_value = {"issueLinkTypes": []}
        result = await get_link_types(mock_client)
        assert result.count == 0
        assert result.data == []


class TestCreateIssueLink:
    async def test_creates_link(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.create_issue_link.return_value = None
        result = await create_issue_link(mock_client, "Blocks", "PROJ-1", "PROJ-2")
        assert isinstance(result, OperationResult)
        assert result.data["link_type"] == "Blocks"
        assert result.data["inward_key"] == "PROJ-1"
        assert result.data["outward_key"] == "PROJ-2"
        assert result.data["status"] == "created"
        mock_client._jira_instance.create_issue_link.assert_called_once_with(
            {
                "type": {"name": "Blocks"},
                "inwardIssue": {"key": "PROJ-1"},
                "outwardIssue": {"key": "PROJ-2"},
            }
        )


class TestRemoveIssueLink:
    async def test_removes_link(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.remove_issue_link.return_value = None
        result = await remove_issue_link(mock_client, "12345")
        assert isinstance(result, OperationResult)
        assert result.data["link_id"] == "12345"
        assert result.data["status"] == "removed"
        mock_client._jira_instance.remove_issue_link.assert_called_once_with("12345")


class TestLinkToEpic:
    async def test_links_to_epic(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.update_issue_field.return_value = None
        result = await link_to_epic(mock_client, "PROJ-5", "PROJ-1")
        assert isinstance(result, OperationResult)
        assert result.data["issue_key"] == "PROJ-5"
        assert result.data["epic_key"] == "PROJ-1"
        assert result.data["status"] == "linked"
        mock_client._jira_instance.update_issue_field.assert_called_once_with("PROJ-5", {"parent": {"key": "PROJ-1"}})
