"""Jira project operations — list projects, versions, components."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from a2atlassian.formatter import OperationResult

if TYPE_CHECKING:
    from a2atlassian.client import AtlassianClient


def _extract_project(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a raw project."""
    lead = raw.get("lead") or {}
    # atlassian-python-api may return lead as a string or dict
    if isinstance(lead, str):
        lead_name = lead
    else:
        lead_name = lead.get("displayName", "")
    return {
        "key": raw.get("key", ""),
        "name": raw.get("name", ""),
        "lead": lead_name,
        "project_type_key": raw.get("projectTypeKey", ""),
    }


def _extract_version(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a raw version."""
    return {
        "id": str(raw.get("id", "")),
        "name": raw.get("name", ""),
        "released": bool(raw.get("released", False)),
        "release_date": raw.get("releaseDate", ""),
    }


def _extract_component(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a raw component."""
    lead = raw.get("lead") or {}
    if isinstance(lead, str):
        lead_name = lead
    else:
        lead_name = lead.get("displayName", "")
    return {
        "id": str(raw.get("id", "")),
        "name": raw.get("name", ""),
        "lead": lead_name,
    }


async def get_projects(client: AtlassianClient) -> OperationResult:
    """List all Jira projects."""
    t0 = time.monotonic()
    data = await client._call(client._jira.projects)
    elapsed = int((time.monotonic() - t0) * 1000)

    projects = data if isinstance(data, list) else []

    return OperationResult(
        name="get_projects",
        data=[_extract_project(p) for p in projects],
        count=len(projects),
        truncated=False,
        time_ms=elapsed,
    )


async def get_project_versions(client: AtlassianClient, project_key: str) -> OperationResult:
    """Get versions for a Jira project."""
    t0 = time.monotonic()
    data = await client._call(client._jira.get_project_versions, project_key)
    elapsed = int((time.monotonic() - t0) * 1000)

    versions = data if isinstance(data, list) else []

    return OperationResult(
        name="get_project_versions",
        data=[_extract_version(v) for v in versions],
        count=len(versions),
        truncated=False,
        time_ms=elapsed,
    )


async def get_project_components(client: AtlassianClient, project_key: str) -> OperationResult:
    """Get components for a Jira project."""
    t0 = time.monotonic()
    data = await client._call(client._jira.get_project_components, project_key)
    elapsed = int((time.monotonic() - t0) * 1000)

    components = data if isinstance(data, list) else []

    return OperationResult(
        name="get_project_components",
        data=[_extract_component(c) for c in components],
        count=len(components),
        truncated=False,
        time_ms=elapsed,
    )


async def get_project_metadata(
    client: AtlassianClient,
    project_key: str,
    include: list[str] | None = None,
) -> OperationResult:
    """Get project metadata. include=['components','versions','all']; default 'all'."""
    include = include or ["all"]
    want_components = "components" in include or "all" in include
    want_versions = "versions" in include or "all" in include

    t0 = time.monotonic()
    data: dict[str, Any] = {}
    if want_components:
        raw = await client._call(client._jira.get_project_components, project_key)
        data["components"] = [{"id": str(c.get("id", "")), "name": c.get("name", "")} for c in raw]
    if want_versions:
        raw = await client._call(client._jira.get_project_versions, project_key)
        data["versions"] = [{"id": str(v.get("id", "")), "name": v.get("name", ""), "released": v.get("released", False)} for v in raw]
    elapsed = int((time.monotonic() - t0) * 1000)

    return OperationResult(
        name="get_project_metadata",
        data=data,
        count=1,
        truncated=False,
        time_ms=elapsed,
    )


async def create_version(
    client: AtlassianClient,
    project_key: str,
    name: str,
    **kwargs: Any,
) -> OperationResult:
    """Create a new version in a Jira project."""
    t0 = time.monotonic()
    data = await client._call(client._jira.create_version, name, project_key, **kwargs)
    elapsed = int((time.monotonic() - t0) * 1000)

    result_data: dict[str, Any]
    if isinstance(data, dict):
        result_data = _extract_version(data)
        result_data["status"] = "created"
    else:
        result_data = {"name": name, "project_key": project_key, "status": "created"}

    return OperationResult(
        name="create_version",
        data=result_data,
        count=1,
        truncated=False,
        time_ms=elapsed,
    )
