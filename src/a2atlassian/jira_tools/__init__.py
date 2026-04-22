"""Jira tool modules — one per feature domain.

Each module exposes ``register_read`` and/or ``register_write`` that accept
(server, get_client_or_connection, enricher) and decorate tools onto the server.

FEATURES maps feature name → module so the MCP server can selectively register.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

from a2atlassian.jira_tools import (
    boards,
    comments,
    fields,
    issues,
    links,
    projects,
    sprints,
    transitions,
    users,
    watchers,
    worklogs,
)

FEATURES: dict[str, ModuleType] = {
    "issues": issues,
    "comments": comments,
    "transitions": transitions,
    "projects": projects,
    "fields": fields,
    "users": users,
    "boards": boards,
    "sprints": sprints,
    "links": links,
    "watchers": watchers,
    "worklogs": worklogs,
}
