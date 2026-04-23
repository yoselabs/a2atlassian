"""MCP server frontend — server setup, connection management, and tool registration."""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from a2atlassian.client import AtlassianClient
from a2atlassian.config import DEFAULT_CONFIG_DIR
from a2atlassian.connections import ConnectionInfo, ConnectionStore
from a2atlassian.errors import ErrorEnricher
from a2atlassian.jira_tools import FEATURES as JIRA_FEATURES

server = FastMCP(
    "a2atlassian",
    instructions=(
        "Agent-to-Atlassian — work with Jira and Confluence. "
        "Connections are identified by project name. "
        "Use 'login' to save a connection, then call tools with the project name. "
        "Connections are read-only by default; re-login with --read-only false to enable writes. "
        "For security, pass tokens as ${ENV_VAR} references, not literal values. "
        "Default output is TOON for lists (token-efficient), JSON for single entities."
    ),
)

_ephemeral_connections: dict[str, ConnectionInfo] = {}
_scope_filter: list[str] = []
_enricher = ErrorEnricher()


def _store() -> ConnectionStore:
    return ConnectionStore(DEFAULT_CONFIG_DIR)


def _get_connection(project: str) -> ConnectionInfo:
    """Resolve a connection by project name."""
    if project in _ephemeral_connections:
        return _ephemeral_connections[project]
    store = _store()
    conn = store.load(project)
    if _scope_filter and project not in _scope_filter:
        msg = f"Connection '{project}' exists but is not in scope. Available: {', '.join(_scope_filter)}"
        raise FileNotFoundError(msg)
    return conn


def _get_client(project: str) -> AtlassianClient:
    """Resolve a connection and return a client."""
    return AtlassianClient(_get_connection(project))


# --- Connection management tools ---


@server.tool()
async def login(project: str, url: str, email: str, token: str, read_only: bool = True) -> str:
    """Save an Atlassian connection. Validates by calling /myself.

    For security, prefer passing token as ${ENV_VAR} reference (e.g., "${ATLASSIAN_TOKEN}")
    rather than a literal value. The variable is expanded at runtime, never stored resolved.
    """
    info = ConnectionInfo(connection=project, url=url, email=email, token=token, read_only=read_only)
    client = AtlassianClient(info)
    user = await client.validate()
    store = _store()
    path = store.save(connection=project, url=url, email=email, token=token, read_only=read_only)
    display_name = user.get("displayName", "unknown")
    return f"Connection saved: {path} (authenticated as {display_name})"


@server.tool()
def logout(project: str) -> str:
    """Remove a saved connection."""
    store = _store()
    store.delete(project)
    return f"Connection removed: {project}"


@server.tool()
def list_connections(project: str | None = None) -> str:
    """List saved connections (no secrets shown)."""
    store = _store()
    saved = store.list_connections(connection=project)
    all_conns = list(saved)
    for p, info in _ephemeral_connections.items():
        if project is None or p == project:
            all_conns.append(info)
    if not all_conns:
        return "No connections found."
    lines = []
    for info in all_conns:
        mode = "read-only" if info.read_only else "read-write"
        ephemeral = " [ephemeral]" if info.connection in _ephemeral_connections else ""
        lines.append(f"{info.connection} ({info.url}) [{mode}]{ephemeral}")
    return "\n".join(lines)


# --- Tool registration ---


def _register_jira_tools(features: set[str] | None) -> None:
    """Register Jira tools filtered by feature set. None means all features.

    Note: must be called from main(), not at import time, so --enable can filter.
    """
    if features is not None:
        unknown = features - set(JIRA_FEATURES.keys())
        if unknown:
            sys.exit(f"Error: unknown Jira feature(s): {', '.join(sorted(unknown))}. Available: {', '.join(sorted(JIRA_FEATURES.keys()))}")
    for name, mod in JIRA_FEATURES.items():
        if features is not None and name not in features:
            continue
        if hasattr(mod, "register_read"):
            mod.register_read(server, _get_client, _enricher)
        if hasattr(mod, "register_write"):
            mod.register_write(server, _get_connection, _enricher)


# --- CLI argument parsing ---


def _parse_register_args(args: list[str]) -> list[ConnectionInfo]:
    """Parse --register args: --register project url email token [--rw]"""
    connections = []
    i = 0
    while i < len(args):
        if args[i] == "--register":
            if i + 4 >= len(args):
                msg = f"--register requires 4 arguments (project url email token), got {len(args) - i - 1}"
                raise ValueError(msg)
            project = args[i + 1]
            url = args[i + 2]
            email = args[i + 3]
            token = args[i + 4]
            i += 5
            read_only = True
            if i < len(args) and args[i] == "--rw":
                read_only = False
                i += 1
            connections.append(
                ConnectionInfo(
                    connection=project,
                    url=url,
                    email=email,
                    token=token,
                    read_only=read_only,
                )
            )
        else:
            i += 1
    return connections


def _parse_scope_args(args: list[str]) -> list[str]:
    """Parse --scope args: --scope project [--scope project2]"""
    scopes = []
    i = 0
    while i < len(args):
        if args[i] == "--scope" and i + 1 < len(args):
            scopes.append(args[i + 1])
            i += 2
        else:
            i += 1
    return scopes


def _parse_enable_args(args: list[str]) -> dict[str, set[str] | None]:
    """Parse --enable args into a domain->features mapping.

    Examples:
        --enable jira              -> {"jira": None}        (all features)
        --enable jira:issues,sprints -> {"jira": {"issues", "sprints"}}
        --enable jira --enable confluence -> {"jira": None, "confluence": None}

    Returns empty dict when no --enable flags are given (means enable everything).
    """
    result: dict[str, set[str] | None] = {}
    i = 0
    while i < len(args):
        if args[i] == "--enable" and i + 1 < len(args):
            spec = args[i + 1]
            if ":" in spec:
                domain, features_str = spec.split(":", 1)
                features = {f.strip() for f in features_str.split(",") if f.strip()}
                existing = result.get(domain)
                if existing is None and domain in result:
                    pass  # already enabling all — keep it
                elif existing is not None:
                    result[domain] = existing | features
                else:
                    result[domain] = features
            else:
                result[spec] = None  # None = all features
            i += 2
        else:
            i += 1
    return result


def _domain_enabled(domain: str, enable: dict[str, set[str] | None]) -> bool:
    """Check if a domain is enabled. Empty enable dict means everything is enabled."""
    return not enable or domain in enable


def _domain_features(domain: str, enable: dict[str, set[str] | None]) -> set[str] | None:
    """Get enabled features for a domain. Returns None if all features are enabled."""
    if not enable or domain not in enable:
        return None
    return enable[domain]


def main() -> None:
    """Run the MCP server (stdio transport)."""
    global _scope_filter  # noqa: PLW0603

    args = sys.argv[1:]

    for conn in _parse_register_args(args):
        _ephemeral_connections[conn.connection] = conn

    _scope_filter = _parse_scope_args(args)
    enable = _parse_enable_args(args)

    # Validate domain names
    if enable:
        known_domains = {"jira"}  # add "confluence" when it ships
        unknown_domains = set(enable.keys()) - known_domains
        if unknown_domains:
            sys.exit(f"Error: unknown domain(s): {', '.join(sorted(unknown_domains))}. Available: {', '.join(sorted(known_domains))}")

    # Register domain tools based on --enable flags
    if _domain_enabled("jira", enable):
        _register_jira_tools(_domain_features("jira", enable))

    server.run()


if __name__ == "__main__":
    main()
