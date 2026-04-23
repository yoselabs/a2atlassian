"""Tests for the async Atlassian client wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from requests.exceptions import HTTPError
from requests.models import Response

from a2atlassian.client import AtlassianClient, AtlassianClientBase
from a2atlassian.connections import ConnectionInfo
from a2atlassian.errors import AuthenticationError, RateLimitError, ServerError


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

    @patch("a2atlassian.jira_client._lazy_jira")
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

    @patch("a2atlassian.jira_client._lazy_jira")
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


def _make_http_error(status: int) -> HTTPError:
    resp = Response()
    resp.status_code = status
    return HTTPError(response=resp)


@pytest.fixture
def base_client() -> AtlassianClientBase:
    conn = ConnectionInfo(
        connection="t",
        url="https://t.atlassian.net",
        email="t@t.com",
        token="tok",
        read_only=True,
    )
    return AtlassianClientBase(conn)


class TestBaseRetry:
    async def test_401_raises_authentication_error(self, base_client: AtlassianClientBase) -> None:
        def boom() -> None:
            raise _make_http_error(401)

        with pytest.raises(AuthenticationError):
            await base_client._call(boom)

    async def test_429_retries_then_raises_rate_limit(self, base_client: AtlassianClientBase) -> None:
        calls = 0

        def boom() -> None:
            nonlocal calls
            calls += 1
            raise _make_http_error(429)

        base_client.RETRY_BACKOFF = [0.0, 0.0]
        with pytest.raises(RateLimitError):
            await base_client._call(boom)
        assert calls == base_client.MAX_RETRIES + 1

    async def test_500_retries_then_raises_server_error(self, base_client: AtlassianClientBase) -> None:
        def boom() -> None:
            raise _make_http_error(503)

        base_client.RETRY_BACKOFF = [0.0, 0.0]
        with pytest.raises(ServerError):
            await base_client._call(boom)

    async def test_success_returns_value(self, base_client: AtlassianClientBase) -> None:
        def ok() -> str:
            return "hello"

        result = await base_client._call(ok)
        assert result == "hello"
