"""Tests for the @write_operation decorator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from a2atlassian.connections import ConnectionStore
from a2atlassian.decorators import write_operation
from a2atlassian.errors import WriteAccessDeniedError

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def store_with_readonly(tmp_config_dir: Path) -> ConnectionStore:
    store = ConnectionStore(tmp_config_dir)
    store.save("readonly_proj", "https://x.atlassian.net", "a@b.com", "tok", read_only=True)
    return store


@pytest.fixture
def store_with_readwrite(tmp_config_dir: Path) -> ConnectionStore:
    store = ConnectionStore(tmp_config_dir)
    store.save("rw_proj", "https://x.atlassian.net", "a@b.com", "tok", read_only=False)
    return store


class TestWriteOperation:
    async def test_blocks_readonly_connection(self, store_with_readonly: ConnectionStore) -> None:
        @write_operation
        async def my_write_tool(project: str, data: str) -> str:
            return f"wrote {data}"

        with pytest.raises(WriteAccessDeniedError, match="read-only"):
            await my_write_tool(project="readonly_proj", data="test", _store=store_with_readonly)

    async def test_allows_readwrite_connection(self, store_with_readwrite: ConnectionStore) -> None:
        @write_operation
        async def my_write_tool(project: str, data: str) -> str:
            return f"wrote {data}"

        result = await my_write_tool(project="rw_proj", data="test", _store=store_with_readwrite)
        assert result == "wrote test"

    async def test_passes_through_kwargs(self, store_with_readwrite: ConnectionStore) -> None:
        inner = AsyncMock(return_value="ok")

        @write_operation
        async def my_tool(project: str, key: str, body: str) -> str:
            return await inner(project=project, key=key, body=body)

        await my_tool(project="rw_proj", key="PROJ-1", body="hello", _store=store_with_readwrite)
        inner.assert_called_once_with(project="rw_proj", key="PROJ-1", body="hello")

    async def test_error_message_includes_project(self, store_with_readonly: ConnectionStore) -> None:
        @write_operation
        async def my_tool(project: str) -> str:
            return "ok"

        with pytest.raises(WriteAccessDeniedError, match="readonly_proj"):
            await my_tool(project="readonly_proj", _store=store_with_readonly)
