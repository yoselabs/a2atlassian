"""CLI frontend — thin wrapper around a2atlassian core."""

from __future__ import annotations

import asyncio
import sys

import click

from a2atlassian import __version__
from a2atlassian.client import AtlassianClient
from a2atlassian.config import DEFAULT_CONFIG_DIR
from a2atlassian.connections import ConnectionInfo, ConnectionStore


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
@click.option("-p", "--project", required=True, help="Project name")
@click.option("--url", required=True, help="Atlassian site URL (e.g., https://mysite.atlassian.net)")
@click.option("--email", required=True, help="Account email")
@click.option("--token", required=True, help="API token (or ${ENV_VAR} reference)")
@click.option("--read-only/--no-read-only", default=True, help="Read-only mode (default: true)")
def login(project: str, url: str, email: str, token: str, read_only: bool) -> None:
    """Save an Atlassian connection. Validates by calling /myself."""
    info = ConnectionInfo(project=project, url=url, email=email, token=token, read_only=read_only)
    client = AtlassianClient(info)

    try:
        user = asyncio.run(client.validate())
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Connection failed: {exc}", err=True)
        sys.exit(1)

    store = _store()
    path = store.save(project, url, email, token, read_only=read_only)
    display_name = user.get("displayName", "unknown")
    click.echo(f"Connection saved: {path} (authenticated as {display_name})")


@cli.command()
@click.option("-p", "--project", required=True, help="Project name")
def logout(project: str) -> None:
    """Remove a saved connection."""
    store = _store()
    try:
        store.delete(project)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    click.echo(f"Connection removed: {project}")


@cli.command()
@click.option("-p", "--project", default=None, help="Filter by project")
def connections(project: str | None) -> None:
    """List saved connections (no secrets shown)."""
    store = _store()
    results = store.list_connections(project=project)
    if not results:
        click.echo("No connections found.")
        return
    for info in results:
        mode = "read-only" if info.read_only else "read-write"
        click.echo(f"{info.project} ({info.url}) [{mode}]")
