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
    def _register_and_split(*, read_only=False, include_confluence=False):
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

        feature_maps = [JIRA_FEATURES]
        if include_confluence:
            from a2atlassian.confluence_tools import FEATURES as CONFLUENCE_FEATURES

            feature_maps.append(CONFLUENCE_FEATURES)

        for feature_map in feature_maps:
            for mod in feature_map.values():
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
        assert len(read_names) == 17
        for name in read_names:
            tool = srv._tool_manager._tools[name]
            kwargs = self._build_kwargs(tool.fn)
            result = await tool.fn(**kwargs)
            assert isinstance(result, str), f"{name} did not return str"

    async def test_all_write_tools_execute(self) -> None:
        """Every write tool wrapper body executes (writable connection)."""
        srv, _, write_names = self._register_and_split(read_only=False)
        assert len(write_names) == 14
        for name in write_names:
            tool = srv._tool_manager._tools[name]
            kwargs = self._build_kwargs(tool.fn)
            result = await tool.fn(**kwargs)
            assert isinstance(result, str), f"{name} did not return str"

    async def test_all_tools_declare_str_return_type(self) -> None:
        """Regression: every registered tool must declare -> str so FastMCP's output_schema
        matches the formatted string the @mcp_tool wrapper returns. Declaring -> OperationResult
        (the internal dataclass) makes FastMCP validate the JSON string against a dict schema
        and raises 'Input should be a valid dictionary or object to extract fields from'."""
        srv, read_names, write_names = self._register_and_split(read_only=False, include_confluence=True)
        for name in read_names | write_names:
            tool = srv._tool_manager._tools[name]
            hints = inspect.get_annotations(tool.fn, eval_str=True)
            assert hints.get("return") is str, f"{name} declares return {hints.get('return')!r}; must be str"
            # With -> str, FastMCP generates a wrap_output schema that accepts the
            # formatted string. Verify validation round-trips so we catch any future
            # regression where someone reintroduces a dataclass return type.
            validated = tool.fn_metadata.convert_result("ok")
            assert validated is not None

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
        from a2atlassian.connections import ConnectionInfo, ConnectionStore

        store = ConnectionStore(tmp_path)
        store.save(ConnectionInfo(connection="protea", url="https://p.atlassian.net", email="x@y.com", token="t"))
        monkeypatch.setattr(mcp_server, "_store", lambda: store)

        with pytest.raises(FileNotFoundError, match="protae") as exc_info:
            mcp_server._get_connection("protae")

        msg = str(exc_info.value)
        assert "protea" in msg
        assert "Did you mean" in msg


class TestLoginToolSignature:
    """Verify the MCP login tool exposes timezone and worklog_admins parameters."""

    def test_login_has_timezone_param(self) -> None:
        import inspect

        from a2atlassian.mcp_server import login

        sig = inspect.signature(login)
        assert "timezone" in sig.parameters
        assert sig.parameters["timezone"].default == "UTC"

    def test_login_has_worklog_admins_param(self) -> None:
        import inspect

        from a2atlassian.mcp_server import login

        sig = inspect.signature(login)
        assert "worklog_admins" in sig.parameters
        assert sig.parameters["worklog_admins"].default is None

    async def test_login_persists_timezone_and_admins(self, tmp_path, monkeypatch) -> None:
        """login() passes timezone + worklog_admins through to ConnectionStore.save()."""
        from unittest.mock import AsyncMock, patch

        from a2atlassian import mcp_server
        from a2atlassian.connections import ConnectionStore

        store = ConnectionStore(tmp_path)
        monkeypatch.setattr(mcp_server, "_store", lambda: store)

        with patch("a2atlassian.mcp_server.JiraClient") as mock_client_cls:
            instance = mock_client_cls.return_value
            instance.validate = AsyncMock(return_value={"displayName": "Alice"})

            result = await mcp_server.login(
                connection="myproj",
                url="https://myproj.atlassian.net",
                email="alice@example.com",
                token="tok",
                timezone="Europe/Istanbul",
                worklog_admins=["admin@example.com"],
            )

        assert "Alice" in result
        loaded = store.load("myproj")
        assert loaded.timezone == "Europe/Istanbul"
        assert "admin@example.com" in loaded.worklog_admins


class TestConfluenceWiring:
    def test_known_domains_includes_confluence(self) -> None:
        from a2atlassian.mcp_server import _parse_enable_args

        parsed = _parse_enable_args(["--enable", "confluence"])
        assert "confluence" in parsed

    def test_instructions_mentions_confluence(self) -> None:
        from a2atlassian.mcp_server import server

        text = getattr(server, "instructions", "") or ""
        assert "Confluence" in text
        assert "Jira only today" not in text

    def test_get_confluence_client_returns_confluence_client(self) -> None:
        from a2atlassian.confluence_client import ConfluenceClient
        from a2atlassian.connections import ConnectionInfo
        from a2atlassian.mcp_server import _ephemeral_connections, _get_confluence_client

        _ephemeral_connections["mp"] = ConnectionInfo(
            connection="mp", url="https://x.atlassian.net", email="a@b", token="t", read_only=True
        )
        try:
            client = _get_confluence_client("mp")
            assert isinstance(client, ConfluenceClient)
        finally:
            _ephemeral_connections.pop("mp", None)


class TestToolDeletions:
    def test_jira_get_issue_dev_info_is_absent(self) -> None:
        """Ensure the deleted placeholder tool is gone from source."""
        import inspect

        from a2atlassian.jira_tools import issues as issues_mod

        source = inspect.getsource(issues_mod)
        assert "jira_get_issue_dev_info" not in source

    def test_jira_link_to_epic_is_absent(self) -> None:
        import inspect

        from a2atlassian.jira_tools import links as links_mod

        source = inspect.getsource(links_mod)
        assert "jira_link_to_epic" not in source
