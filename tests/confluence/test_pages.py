"""Tests for Confluence page operations."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from a2atlassian.confluence.pages import get_page, get_page_children
from a2atlassian.confluence_client import ConfluenceClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mock_client() -> ConfluenceClient:
    conn = ConnectionInfo(
        connection="t",
        url="https://t.atlassian.net",
        email="t@t.com",
        token="tok",
        read_only=True,
    )
    client = ConfluenceClient(conn)
    client._confluence_instance = MagicMock()
    return client


class TestGetPage:
    async def test_returns_operation_result(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_id.return_value = json.loads((FIXTURES / "confluence_page.json").read_text())
        result = await get_page(mock_client, "123456789")
        assert isinstance(result, OperationResult)
        assert result.data["id"] == "123456789"
        assert result.data["title"] == "Example page"
        assert result.data["space_key"] == "TEAM"
        assert result.data["version"] == 3
        assert "body" in result.data
        assert result.count == 1
        assert result.truncated is False

    async def test_passes_expand_default(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_id.return_value = {
            "id": "1",
            "title": "",
            "space": {},
            "version": {},
            "body": {"storage": {"value": ""}},
        }
        await get_page(mock_client, "1")
        call = mock_client._confluence_instance.get_page_by_id.call_args
        assert call.kwargs.get("expand") == "body.storage,version,space"


class TestGetPageChildren:
    async def test_returns_list_result(self, mock_client: ConfluenceClient) -> None:
        import json as _json

        mock_client._confluence_instance.get_page_child_by_type.return_value = _json.loads(
            (FIXTURES / "confluence_page_children.json").read_text()
        )["results"]
        result = await get_page_children(mock_client, "100", limit=50, offset=0)
        assert isinstance(result, OperationResult)
        assert result.count == 2
        assert result.data[0]["id"] == "200"
        assert result.data[0]["title"] == "Child A"
        assert result.data[0]["version"] == 1
        assert result.data[0]["url"].endswith("/pages/200")

    async def test_passes_pagination_params(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_child_by_type.return_value = []
        await get_page_children(mock_client, "100", limit=10, offset=20)
        call = mock_client._confluence_instance.get_page_child_by_type.call_args
        assert call.kwargs.get("start") == 20
        assert call.kwargs.get("limit") == 10
        assert call.kwargs.get("type") == "page"
