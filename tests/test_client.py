"""Tests for the async Atlassian client wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.errors import AuthenticationError, RateLimitError


@pytest.fixture
def connection() -> ConnectionInfo:
    return ConnectionInfo(
        connection="test",
        url="https://test.atlassian.net",
        email="test@example.com",
        token="test-token",
        read_only=True,
    )


@pytest.fixture
def client(connection: ConnectionInfo) -> AtlassianClient:
    c = AtlassianClient(connection)
    c.RETRY_BACKOFF = [0, 0]
    return c


class TestAtlassianClient:
    def test_init(self, client: AtlassianClient) -> None:
        assert client.connection.connection == "test"

    @patch("a2atlassian.client._lazy_jira")
    async def test_jira_property_creates_instance(self, mock_lazy: MagicMock, connection: ConnectionInfo) -> None:
        mock_jira_cls = MagicMock()
        mock_lazy.return_value = mock_jira_cls
        client = AtlassianClient(connection)
        _ = client._jira
        mock_jira_cls.assert_called_once_with(
            url="https://test.atlassian.net",
            username="test@example.com",
            password="test-token",
            cloud=True,
        )

    @patch("a2atlassian.client._lazy_jira")
    async def test_jira_cached(self, mock_lazy: MagicMock, connection: ConnectionInfo) -> None:
        mock_jira_cls = MagicMock()
        mock_lazy.return_value = mock_jira_cls
        client = AtlassianClient(connection)
        _ = client._jira
        _ = client._jira
        mock_jira_cls.assert_called_once()

    async def test_call_async_wraps_sync(self, client: AtlassianClient) -> None:
        mock_fn = MagicMock(return_value={"key": "TEST-1"})
        result = await client._call(mock_fn, "arg1", kwarg1="val1")
        mock_fn.assert_called_once_with("arg1", kwarg1="val1")
        assert result == {"key": "TEST-1"}

    async def test_retry_on_rate_limit(self, client: AtlassianClient) -> None:
        from requests.exceptions import HTTPError

        response = MagicMock()
        type(response).status_code = PropertyMock(return_value=429)
        error = HTTPError(response=response)

        mock_fn = MagicMock(side_effect=[error, error, {"ok": True}])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client._call(mock_fn)
        assert result == {"ok": True}
        assert mock_fn.call_count == 3

    async def test_retry_on_server_error(self, client: AtlassianClient) -> None:
        from requests.exceptions import HTTPError

        response = MagicMock()
        type(response).status_code = PropertyMock(return_value=500)
        error = HTTPError(response=response)

        mock_fn = MagicMock(side_effect=[error, {"ok": True}])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client._call(mock_fn)
        assert result == {"ok": True}

    async def test_auth_error_no_retry(self, client: AtlassianClient) -> None:
        from requests.exceptions import HTTPError

        response = MagicMock()
        type(response).status_code = PropertyMock(return_value=401)
        error = HTTPError(response=response)

        mock_fn = MagicMock(side_effect=error)
        with pytest.raises(AuthenticationError):
            await client._call(mock_fn)
        assert mock_fn.call_count == 1

    async def test_max_retries_exceeded(self, client: AtlassianClient) -> None:
        from requests.exceptions import HTTPError

        response = MagicMock()
        type(response).status_code = PropertyMock(return_value=429)
        error = HTTPError(response=response)

        mock_fn = MagicMock(side_effect=error)
        with patch("asyncio.sleep", new_callable=AsyncMock), pytest.raises(RateLimitError):
            await client._call(mock_fn)
        assert mock_fn.call_count == 3
