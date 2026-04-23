"""Tests for Jira field operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.fields import get_field_options, search_fields


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


class TestSearchFields:
    async def test_returns_fields(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_all_fields.return_value = [
            {
                "id": "summary",
                "name": "Summary",
                "custom": False,
                "schema": {"type": "string"},
            },
            {
                "id": "customfield_10001",
                "name": "Story Points",
                "custom": True,
                "schema": {"type": "number"},
            },
        ]
        result = await search_fields(mock_client)
        assert isinstance(result, OperationResult)
        assert len(result.data) == 2
        assert result.count == 2
        assert result.data[0]["id"] == "summary"
        assert result.data[0]["name"] == "Summary"
        assert result.data[0]["custom"] is False
        assert result.data[0]["schema_type"] == "string"
        assert result.data[1]["custom"] is True
        assert result.data[1]["schema_type"] == "number"

    async def test_empty_fields(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_all_fields.return_value = []
        result = await search_fields(mock_client)
        assert result.count == 0
        assert result.data == []

    async def test_missing_schema(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_all_fields.return_value = [
            {"id": "summary", "name": "Summary", "custom": False},
        ]
        result = await search_fields(mock_client)
        assert result.data[0]["schema_type"] == ""

    async def test_null_schema(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_all_fields.return_value = [
            {"id": "summary", "name": "Summary", "custom": False, "schema": None},
        ]
        result = await search_fields(mock_client)
        assert result.data[0]["schema_type"] == ""

    async def test_schema_as_string(self, mock_client: AtlassianClient) -> None:
        """atlassian-python-api may transform schema to a string."""
        mock_client._jira_instance.get_all_fields.return_value = [
            {"id": "summary", "name": "Summary", "custom": False, "schema": "string"},
        ]
        result = await search_fields(mock_client)
        assert result.data[0]["schema_type"] == "string"


class TestGetFieldOptions:
    async def test_returns_options_list(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_custom_field_option.return_value = [
            {"id": "1", "value": "Low"},
            {"id": "2", "value": "Medium"},
            {"id": "3", "value": "High"},
        ]
        result = await get_field_options(mock_client, "customfield_10001")
        assert isinstance(result, OperationResult)
        assert len(result.data) == 3
        assert result.data[0]["id"] == "1"
        assert result.data[0]["value"] == "Low"
        mock_client._jira_instance.get_custom_field_option.assert_called_once_with("customfield_10001")

    async def test_returns_options_dict_with_values(self, mock_client: AtlassianClient) -> None:
        """Response may be a dict with a 'values' key."""
        mock_client._jira_instance.get_custom_field_option.return_value = {
            "values": [
                {"id": "1", "value": "Option A"},
                {"id": "2", "value": "Option B"},
            ]
        }
        result = await get_field_options(mock_client, "customfield_10001")
        assert len(result.data) == 2
        assert result.data[0]["value"] == "Option A"

    async def test_returns_single_option_dict(self, mock_client: AtlassianClient) -> None:
        """Response may be a single option dict."""
        mock_client._jira_instance.get_custom_field_option.return_value = {
            "id": "1",
            "value": "Only Option",
        }
        result = await get_field_options(mock_client, "customfield_10001")
        assert len(result.data) == 1
        assert result.data[0]["value"] == "Only Option"

    async def test_handles_int_id(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_custom_field_option.return_value = [
            {"id": 1, "value": "Low"},
        ]
        result = await get_field_options(mock_client, "customfield_10001")
        assert result.data[0]["id"] == "1"

    async def test_empty_response(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_custom_field_option.return_value = []
        result = await get_field_options(mock_client, "customfield_10001")
        assert result.count == 0
        assert result.data == []
