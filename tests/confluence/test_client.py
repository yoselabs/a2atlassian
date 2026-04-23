"""Tests for ConfluenceClient lazy construction."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from a2atlassian.confluence_client import ConfluenceClient
from a2atlassian.connections import ConnectionInfo


@pytest.fixture
def conn() -> ConnectionInfo:
    return ConnectionInfo(
        connection="t",
        url="https://t.atlassian.net",
        email="t@t.com",
        token="tok",
        read_only=True,
    )


class TestConfluenceClient:
    def test_does_not_import_atlassian_at_construction(self, conn: ConnectionInfo) -> None:
        # Constructing the client must not access the _confluence property.
        client = ConfluenceClient(conn)
        assert client._confluence_instance is None

    def test_lazy_confluence_instantiation(self, conn: ConnectionInfo) -> None:
        with patch("a2atlassian.confluence_client._lazy_confluence") as loader:
            loader.return_value = MagicMock(return_value="CONFLUENCE_OBJ")
            client = ConfluenceClient(conn)
            first = client._confluence
            second = client._confluence
        assert first == "CONFLUENCE_OBJ"
        assert first is second  # cached after first access
        loader.assert_called_once()

    async def test_validate_calls_current_user_endpoint(self, conn: ConnectionInfo) -> None:
        client = ConfluenceClient(conn)
        client._confluence_instance = MagicMock()
        client._confluence_instance.get.return_value = {"accountId": "abc", "displayName": "X"}
        result = await client.validate()
        client._confluence_instance.get.assert_called_once_with("rest/api/user/current")
        assert result["displayName"] == "X"
