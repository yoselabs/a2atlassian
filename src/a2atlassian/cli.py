"""CLI frontend — thin wrapper around a2atlassian core."""

from __future__ import annotations

import asyncio
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import click

from a2atlassian import __version__
from a2atlassian.config import DEFAULT_CONFIG_DIR
from a2atlassian.connections import ConnectionInfo, ConnectionStore
from a2atlassian.jira_client import JiraClient

_TZ_ALIASES: dict[str, str] = {
    "UTC": "UTC",
    "CET": "Europe/Paris",
    "CEST": "Europe/Paris",
    "ET": "America/New_York",
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "PT": "America/Los_Angeles",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
}


def _resolve_timezone(raw: str) -> str:
    """Resolve a user-provided timezone (IANA name or common alias) to an IANA name.

    Raises click.BadParameter on unknown values.
    """
    resolved = _TZ_ALIASES.get(raw.upper(), raw)
    try:
        ZoneInfo(resolved)
    except ZoneInfoNotFoundError as exc:
        msg = f"Unknown timezone: {raw!r}. Expected an IANA name (e.g. Europe/Istanbul) or alias (CET, ET, UTC)."
        raise click.BadParameter(msg) from exc
    return resolved


def _store() -> ConnectionStore:
    return ConnectionStore(DEFAULT_CONFIG_DIR)


@click.group(invoke_without_command=True)
@click.version_option(__version__, package_name="a2atlassian")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """a2atlassian — Agent-to-Atlassian. Work with Jira & Confluence from CLI or MCP."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option("-c", "--connection", required=True, help="Connection name")
@click.option("--url", required=True, help="Atlassian site URL (e.g., https://mysite.atlassian.net)")
@click.option("--email", required=True, help="Account email")
@click.option("--token", required=True, help="API token (or ${ENV_VAR} reference)")
@click.option("--read-only/--no-read-only", default=True, help="Read-only mode (default: true)")
@click.option("--tz", "timezone", default="UTC", help="Timezone (IANA name or alias: CET, ET, UTC; default UTC)")
@click.option("--worklog-admin", "worklog_admins", multiple=True, help="Email(s) allowed to proxy-log worklog hours. Repeat for multiple.")
def login(connection: str, url: str, email: str, token: str, read_only: bool, timezone: str, worklog_admins: tuple[str, ...]) -> None:
    """Save an Atlassian connection. Validates by calling /myself."""
    resolved_tz = _resolve_timezone(timezone)

    info = ConnectionInfo(
        connection=connection,
        url=url,
        email=email,
        token=token,
        read_only=read_only,
        timezone=resolved_tz,
        worklog_admins=tuple(worklog_admins),
    )
    client = JiraClient(info)

    try:
        user = asyncio.run(client.validate())
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Connection failed: {exc}", err=True)
        sys.exit(1)

    store = _store()
    path = store.save(info)
    display_name = user.get("displayName", "unknown")
    click.echo(f"Connection saved: {path} (authenticated as {display_name})")


@cli.command()
@click.option("-c", "--connection", required=True, help="Project name")
def logout(connection: str) -> None:
    """Remove a saved connection."""
    store = _store()
    try:
        store.delete(connection)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    click.echo(f"Connection removed: {connection}")


@cli.command()
@click.option("-c", "--connection", "connection_filter", default=None, required=False, help="Filter by connection name")
def connections(connection_filter: str | None) -> None:
    """List saved connections (no secrets shown)."""
    store = _store()
    results = store.list_connections()
    if connection_filter is not None:
        results = [r for r in results if r.connection == connection_filter]
    if not results:
        click.echo("No connections found.")
        return
    for info in results:
        mode = "read-only" if info.read_only else "read-write"
        click.echo(f"{info.connection} ({info.url}) [{mode}] tz={info.timezone} admins={len(info.worklog_admins)}")
