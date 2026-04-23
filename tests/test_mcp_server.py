"""Tests for the MCP server tool registrations and argument parsing."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest

from a2atlassian.connections import ConnectionInfo
from a2atlassian.jira_tools import FEATURES as JIRA_FEATURES
from a2atlassian.mcp_server import (
    _parse_enable_args,
    _parse_register_args,
    _parse_scope_args,
    _register_jira_tools,
)


class TestParseRegisterArgs:
    def test_single_register(self) -> None:
        args = ["--register", "myproject", "https://p.atlassian.net", "e@m.com", "tok123"]
        result = _parse_register_args(args)
        assert len(result) == 1
        assert result[0].connection == "myproject"
        assert result[0].url == "https://p.atlassian.net"
        assert result[0].email == "e@m.com"
        assert result[0].token == "tok123"
        assert result[0].read_only is True

    def test_multiple_register(self) -> None:
        args = [
            "--register",
            "a",
            "https://a.atlassian.net",
            "a@m.com",
            "tok_a",
            "--register",
            "b",
            "https://b.atlassian.net",
            "b@m.com",
            "tok_b",
        ]
        result = _parse_register_args(args)
        assert len(result) == 2
        assert result[0].connection == "a"
        assert result[1].connection == "b"

    def test_register_with_rw(self) -> None:
        args = ["--register", "myproject", "https://p.atlassian.net", "e@m.com", "tok123", "--rw"]
        result = _parse_register_args(args)
        assert result[0].read_only is False

    def test_empty_args(self) -> None:
        assert _parse_register_args([]) == []

    def test_insufficient_args_after_register(self) -> None:
        args = ["--register", "myproject", "https://p.atlassian.net"]
        with pytest.raises(ValueError, match="4 arguments"):
            _parse_register_args(args)


class TestParseScopeArgs:
    def test_single_scope(self) -> None:
        args = ["--scope", "myproject"]
        result = _parse_scope_args(args)
        assert result == ["myproject"]

    def test_multiple_scopes(self) -> None:
        args = ["--scope", "myproject", "--scope", "secondary"]
        result = _parse_scope_args(args)
        assert result == ["myproject", "secondary"]

    def test_no_scope(self) -> None:
        assert _parse_scope_args([]) == []

    def test_mixed_args(self) -> None:
        args = ["--scope", "myproject", "--register", "b", "u", "e", "t"]
        result = _parse_scope_args(args)
        assert result == ["myproject"]


class TestParseEnableArgs:
    def test_no_enable(self) -> None:
        assert _parse_enable_args([]) == {}

    def test_domain_only(self) -> None:
        result = _parse_enable_args(["--enable", "jira"])
        assert result == {"jira": None}

    def test_domain_with_features(self) -> None:
        result = _parse_enable_args(["--enable", "jira:issues,sprints"])
        assert result == {"jira": {"issues", "sprints"}}

    def test_multiple_domains(self) -> None:
        result = _parse_enable_args(["--enable", "jira", "--enable", "confluence"])
        assert result == {"jira": None, "confluence": None}

    def test_domain_all_overrides_features(self) -> None:
        """--enable jira should override --enable jira:issues."""
        result = _parse_enable_args(["--enable", "jira:issues", "--enable", "jira"])
        assert result == {"jira": None}

    def test_features_merge(self) -> None:
        """Multiple --enable jira:X should merge feature sets."""
        result = _parse_enable_args(["--enable", "jira:issues", "--enable", "jira:sprints,boards"])
        assert result == {"jira": {"issues", "sprints", "boards"}}

    def test_mixed_with_other_args(self) -> None:
        args = ["--scope", "myproject", "--enable", "jira:issues", "--register", "b", "u", "e", "t"]
        result = _parse_enable_args(args)
        assert result == {"jira": {"issues"}}

    def test_whitespace_in_features(self) -> None:
        result = _parse_enable_args(["--enable", "jira: issues , sprints "])
        assert result == {"jira": {"issues", "sprints"}}

    def test_empty_features_ignored(self) -> None:
        result = _parse_enable_args(["--enable", "jira:issues,,sprints"])
        assert result == {"jira": {"issues", "sprints"}}


class TestToolRegistrationFiltering:
    """Test that --enable filtering actually controls which tools get registered."""

    def _make_server(self):
        from mcp.server.fastmcp import FastMCP

        return FastMCP("test")

    def _tool_names(self, srv) -> set[str]:
        return set(srv._tool_manager._tools.keys())

    def test_all_jira_tools_registered_by_default(self, monkeypatch) -> None:
        """features=None registers all Jira tools."""
        srv = self._make_server()
        monkeypatch.setattr("a2atlassian.mcp_server.server", srv)
        _register_jira_tools(features=None)
        names = self._tool_names(srv)
        # Sanity check: at least one tool per feature registered
        assert len(names) >= len(JIRA_FEATURES)
        assert "jira_get_issue" in names
        assert "jira_create_issue" in names
        assert "jira_get_sprints" in names

    def test_only_issues_feature(self, monkeypatch) -> None:
        srv = self._make_server()
        monkeypatch.setattr("a2atlassian.mcp_server.server", srv)
        _register_jira_tools(features={"issues"})
        names = self._tool_names(srv)
        assert names == {
            "jira_get_issue",
            "jira_search",
            "jira_search_count",
            "jira_create_issue",
            "jira_update_issue",
            "jira_delete_issue",
        }

    def test_unknown_feature_exits(self, monkeypatch) -> None:
        srv = self._make_server()
        monkeypatch.setattr("a2atlassian.mcp_server.server", srv)
        with pytest.raises(SystemExit) as exc_info:
            _register_jira_tools(features={"isues"})  # typo
        assert "isues" in str(exc_info.value)
        assert "Available:" in str(exc_info.value)

    def test_empty_features_registers_nothing(self, monkeypatch) -> None:
        srv = self._make_server()
        monkeypatch.setattr("a2atlassian.mcp_server.server", srv)
        _register_jira_tools(features=set())
        assert self._tool_names(srv) == set()

    def test_multiple_features(self, monkeypatch) -> None:
        srv = self._make_server()
        monkeypatch.setattr("a2atlassian.mcp_server.server", srv)
        _register_jira_tools(features={"issues", "comments"})
        names = self._tool_names(srv)
        assert "jira_get_issue" in names
        assert "jira_get_comments" in names
        assert "jira_add_comment" in names
        assert "jira_get_sprints" not in names
        assert "jira_create_sprint" not in names


def _dummy_value(param: inspect.Parameter) -> object:
    """Generate a plausible dummy value based on type annotation."""
    ann = param.annotation
    if ann is inspect.Parameter.empty:
        return "test"
    ann_str = str(ann) if not isinstance(ann, str) else ann
    if "list" in ann_str:
        return ["TEST-1"]
    if ann_str == "dict" or "dict" in ann_str:
        return {}
    if ann_str == "int":
        return 1
    if ann_str == "bool":
        return True
    return "test"


class TestToolWrapperExecution:
    """Call every registered tool wrapper to cover the try/except/format bodies."""

    @staticmethod
    def _build_kwargs(fn) -> dict:
        sig = inspect.signature(fn)
        kwargs = {}
        for name, param in sig.parameters.items():
            if param.default is not inspect.Parameter.empty:
                continue  # skip optional params — defaults are fine
            kwargs[name] = _dummy_value(param)
        return kwargs

    @staticmethod
    def _register_and_split(*, read_only=False):
        """Register all tools, return (server, read_tool_names, write_tool_names)."""
        from mcp.server.fastmcp import FastMCP

        from a2atlassian.errors import ErrorEnricher
        from a2atlassian.jira_tools import FEATURES as JIRA_FEATURES

        srv = FastMCP("test")
        mock_client = MagicMock()
        conn = ConnectionInfo(
            connection="test",
            url="https://test.atlassian.net",
            email="t@t.com",
            token="tok",
            read_only=read_only,
        )
        enricher = ErrorEnricher()
        read_names: set[str] = set()
        write_names: set[str] = set()

        for mod in JIRA_FEATURES.values():
            before = set(srv._tool_manager._tools.keys())
            if hasattr(mod, "register_read"):
                mod.register_read(srv, lambda _p: mock_client, enricher)
            after_read = set(srv._tool_manager._tools.keys())
            read_names |= after_read - before
            if hasattr(mod, "register_write"):
                mod.register_write(srv, lambda _p: conn, enricher)
            write_names |= set(srv._tool_manager._tools.keys()) - after_read

        return srv, read_names, write_names

    async def test_all_read_tools_execute(self) -> None:
        """Every read tool wrapper body executes without crashing."""
        srv, read_names, _ = self._register_and_split()
        assert len(read_names) == 18
        for name in read_names:
            tool = srv._tool_manager._tools[name]
            kwargs = self._build_kwargs(tool.fn)
            result = await tool.fn(**kwargs)
            assert isinstance(result, str), f"{name} did not return str"

    async def test_all_write_tools_execute(self) -> None:
        """Every write tool wrapper body executes (writable connection)."""
        srv, _, write_names = self._register_and_split(read_only=False)
        assert len(write_names) == 16
        for name in write_names:
            tool = srv._tool_manager._tools[name]
            kwargs = self._build_kwargs(tool.fn)
            result = await tool.fn(**kwargs)
            assert isinstance(result, str), f"{name} did not return str"

    async def test_write_tools_read_only_guard(self) -> None:
        """Write tools return error when connection is read-only."""
        srv, _, write_names = self._register_and_split(read_only=True)
        for name in write_names:
            tool = srv._tool_manager._tools[name]
            kwargs = self._build_kwargs(tool.fn)
            result = await tool.fn(**kwargs)
            assert "read-only" in result, f"{name} did not enforce read-only"


class TestConnectionNotFoundEnrichment:
    def test_message_includes_available_names(self, tmp_path, monkeypatch) -> None:
        from a2atlassian import mcp_server
        from a2atlassian.connections import ConnectionStore

        store = ConnectionStore(tmp_path)
        store.save("protea", "https://p.atlassian.net", "x@y.com", "t")
        monkeypatch.setattr(mcp_server, "_store", lambda: store)

        with pytest.raises(FileNotFoundError, match="protae") as exc_info:
            mcp_server._get_connection("protae")

        msg = str(exc_info.value)
        assert "protea" in msg
        assert "Did you mean" in msg


class TestToolDeletions:
    def test_jira_get_issue_dev_info_is_absent(self) -> None:
        """Ensure the deleted placeholder tool is gone from source."""
        import inspect

        from a2atlassian.jira_tools import issues as issues_mod

        source = inspect.getsource(issues_mod)
        assert "jira_get_issue_dev_info" not in source
