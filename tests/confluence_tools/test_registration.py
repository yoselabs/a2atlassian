"""Assert the Confluence code path does not transitively import Jira modules."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from a2atlassian.confluence_client import ConfluenceClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.errors import ErrorEnricher


def test_confluence_client_does_not_import_jira() -> None:
    code = (
        "import sys\n"
        "from a2atlassian.confluence_client import ConfluenceClient\n"
        "from a2atlassian.connections import ConnectionInfo\n"
        "c = ConfluenceClient(ConnectionInfo(connection='x', url='https://x', email='a@b', token='t', read_only=True))\n"
        "assert c is not None\n"
        "loaded_jira = [m for m in sys.modules if m.startswith('a2atlassian.jira') or m.startswith('a2atlassian.jira_client')]\n"
        "assert loaded_jira == [], f'unexpected jira imports: {loaded_jira}'\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)  # noqa: S603
    if result.returncode != 0:
        pytest.fail(f"stdout={result.stdout!r} stderr={result.stderr!r}")


def test_all_four_confluence_tools_registered() -> None:
    import contextlib

    import a2atlassian.mcp_server as ms

    # Register — idempotency varies; suppress if already registered in a previous test module.
    with contextlib.suppress(Exception):
        ms._register_confluence_tools(None)

    tool_names = {t.name for t in ms.server._tool_manager.list_tools()}
    assert "confluence_get_page" in tool_names
    assert "confluence_get_page_children" in tool_names
    assert "confluence_search" in tool_names
    assert "confluence_upsert_pages" in tool_names


def _make_mock_client() -> ConfluenceClient:
    conn = ConnectionInfo(connection="t", url="https://t.atlassian.net", email="t@t.com", token="tok", read_only=True)
    client = ConfluenceClient(conn)
    client._confluence_instance = MagicMock()
    return client


class TestConfluenceToolWrappers:
    """Execute each tool wrapper body to cover the inner function lines."""

    async def test_get_page_tool_executes(self) -> None:
        from mcp.server.fastmcp import FastMCP

        from a2atlassian.confluence_tools.pages import register_read

        mock_client = _make_mock_client()
        mock_client._confluence_instance.get_page_by_id.return_value = {
            "id": "1",
            "title": "T",
            "space": {"key": "SP", "name": "Space"},
            "version": {"number": 1, "when": ""},
            "body": {"storage": {"value": "<p>hi</p>"}},
            "_links": {"webui": "/p/1"},
        }
        srv = FastMCP("test")
        enricher = ErrorEnricher()
        register_read(srv, lambda _c: mock_client, enricher)
        tool = srv._tool_manager._tools["confluence_get_page"]
        result = await tool.fn(connection="t", page_id="1")
        assert isinstance(result, str)

    async def test_get_page_children_tool_executes(self) -> None:
        from mcp.server.fastmcp import FastMCP

        from a2atlassian.confluence_tools.pages import register_read

        mock_client = _make_mock_client()
        mock_client._confluence_instance.get_page_child_by_type.return_value = []
        srv = FastMCP("test")
        enricher = ErrorEnricher()
        register_read(srv, lambda _c: mock_client, enricher)
        tool = srv._tool_manager._tools["confluence_get_page_children"]
        result = await tool.fn(connection="t", page_id="1")
        assert isinstance(result, str)

    async def test_upsert_pages_tool_read_only_guard(self) -> None:
        # Lines 84-87: upsert body — read-only guard fires first
        from mcp.server.fastmcp import FastMCP

        from a2atlassian.confluence_tools.pages import register_write

        conn = ConnectionInfo(connection="t", url="https://t.atlassian.net", email="t@t.com", token="tok", read_only=True)
        srv = FastMCP("test")
        enricher = ErrorEnricher()
        register_write(srv, lambda _c: conn, enricher)
        tool = srv._tool_manager._tools["confluence_upsert_pages"]
        result = await tool.fn(connection="t", pages=[])
        assert "read-only" in result

    async def test_search_tool_executes(self) -> None:
        # Line 39 in search.py: the _search call
        from mcp.server.fastmcp import FastMCP

        from a2atlassian.confluence_tools.search import register_read

        mock_client = _make_mock_client()
        mock_client._confluence_instance.cql.return_value = {"results": [], "totalSize": 0}
        srv = FastMCP("test")
        enricher = ErrorEnricher()
        register_read(srv, lambda _c: mock_client, enricher)
        tool = srv._tool_manager._tools["confluence_search"]
        result = await tool.fn(connection="t", cql="type = page")
        assert isinstance(result, str)
