"""Tests for Jira comment operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.comments import add_comment, edit_comment, get_comments


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


class TestGetComments:
    async def test_returns_comments(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_get_comments.return_value = {
            "comments": [
                {"id": "1", "body": "First comment", "author": {"displayName": "Alice"}, "created": "2026-01-01"},
                {"id": "2", "body": "Second comment", "author": {"displayName": "Bob"}, "created": "2026-01-02"},
            ],
            "total": 2,
        }
        result = await get_comments(mock_client, "PROJ-1")
        assert isinstance(result, OperationResult)
        assert len(result.data) == 2
        assert result.count == 2
        assert result.data[0]["author"] == "Alice"
        assert result.data[0]["body"] == "First comment"

    async def test_empty_comments(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_get_comments.return_value = {
            "comments": [],
            "total": 0,
        }
        result = await get_comments(mock_client, "PROJ-1")
        assert result.count == 0

    async def test_adf_body_extraction(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_get_comments.return_value = {
            "comments": [
                {
                    "id": "1",
                    "body": {
                        "type": "doc",
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": "Hello ADF"}]},
                        ],
                    },
                    "author": {"displayName": "Alice"},
                },
            ],
            "total": 1,
        }
        result = await get_comments(mock_client, "PROJ-1")
        assert result.data[0]["body"] == "Hello ADF"


class TestAddComment:
    async def test_add_comment(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_add_comment.return_value = {
            "id": "123",
            "body": "New comment",
            "author": {"displayName": "Alice"},
        }
        result = await add_comment(mock_client, "PROJ-1", "New comment")
        assert isinstance(result, OperationResult)
        assert result.data["id"] == "123"
        assert result.data["body"] == "New comment"
        mock_client._jira_instance.issue_add_comment.assert_called_once_with("PROJ-1", "New comment")


class TestEditComment:
    async def test_edit_comment(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.issue_edit_comment.return_value = {
            "id": "123",
            "body": "Updated comment",
            "author": {"displayName": "Alice"},
        }
        result = await edit_comment(mock_client, "PROJ-1", "123", "Updated comment")
        assert isinstance(result, OperationResult)
        assert result.data["body"] == "Updated comment"
        mock_client._jira_instance.issue_edit_comment.assert_called_once_with("PROJ-1", "123", "Updated comment")
