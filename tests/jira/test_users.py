"""Tests for Jira user operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.users import get_user_profile


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


class TestGetUserProfile:
    async def test_returns_user_profile(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.user.return_value = {
            "accountId": "5b10a2844c20165700ede21g",
            "displayName": "Alice Smith",
            "emailAddress": "alice@example.com",
            "active": True,
        }
        result = await get_user_profile(mock_client, "5b10a2844c20165700ede21g")
        assert isinstance(result, OperationResult)
        assert result.data["account_id"] == "5b10a2844c20165700ede21g"
        assert result.data["display_name"] == "Alice Smith"
        assert result.data["email"] == "alice@example.com"
        assert result.data["active"] is True
        assert result.count == 1
        mock_client._jira_instance.user.assert_called_once_with("5b10a2844c20165700ede21g")

    async def test_handles_missing_email(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.user.return_value = {
            "accountId": "5b10a2844c20165700ede21g",
            "displayName": "Bot User",
            "active": True,
        }
        result = await get_user_profile(mock_client, "5b10a2844c20165700ede21g")
        assert result.data["email"] == ""

    async def test_handles_inactive_user(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.user.return_value = {
            "accountId": "5b10a2844c20165700ede21g",
            "displayName": "Former User",
            "emailAddress": "former@example.com",
            "active": False,
        }
        result = await get_user_profile(mock_client, "5b10a2844c20165700ede21g")
        assert result.data["active"] is False

    async def test_handles_missing_fields(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.user.return_value = {}
        result = await get_user_profile(mock_client, "unknown")
        assert result.data["account_id"] == ""
        assert result.data["display_name"] == ""
        assert result.data["email"] == ""
        assert result.data["active"] is False
