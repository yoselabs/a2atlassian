"""Conftest for fixture-based shape validation tests."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_fixture(name: str):
    """Load a fixture file, stripping _meta header."""
    data = json.loads((FIXTURES / name).read_text())
    if isinstance(data, dict):
        data.pop("_meta", None)
    return data


@pytest.fixture(autouse=True, scope="session")
def _check_fixture_freshness():
    """Warn if fixtures were recorded with a different library version."""
    try:
        from importlib.metadata import version

        meta = json.loads((FIXTURES / "jira_issue.json").read_text()).get("_meta", {})
        recorded = meta.get("library_version", "unknown")
        current = version("atlassian-python-api")
        if current != recorded:
            warnings.warn(
                f"Fixtures recorded with {recorded}, running {current}",
                stacklevel=2,
            )
    except ImportError:
        pass


@pytest.fixture
def real_issue():
    return _load_fixture("jira_issue.json")


@pytest.fixture
def real_search():
    return _load_fixture("jira_search.json")


@pytest.fixture
def real_transitions():
    return _load_fixture("jira_transitions.json")


@pytest.fixture
def real_comments():
    return _load_fixture("jira_comments.json")


@pytest.fixture
def real_boards():
    return _load_fixture("jira_boards.json")


@pytest.fixture
def real_sprints():
    return _load_fixture("jira_sprints.json")


@pytest.fixture
def real_sprint_issues():
    return _load_fixture("jira_sprint_issues.json")


@pytest.fixture
def real_projects():
    return _load_fixture("jira_projects.json")


@pytest.fixture
def real_project_versions():
    return _load_fixture("jira_project_versions.json")


@pytest.fixture
def real_project_components():
    return _load_fixture("jira_project_components.json")


@pytest.fixture
def real_fields():
    return _load_fixture("jira_fields.json")


@pytest.fixture
def real_field_options():
    return _load_fixture("jira_field_options.json")


@pytest.fixture
def real_link_types():
    return _load_fixture("jira_link_types.json")


@pytest.fixture
def real_watchers():
    return _load_fixture("jira_watchers.json")


@pytest.fixture
def real_worklogs():
    return _load_fixture("jira_worklogs.json")


@pytest.fixture
def real_user():
    return _load_fixture("jira_user.json")


@pytest.fixture
def real_create_issue_response():
    return _load_fixture("jira_create_issue_response.json")


@pytest.fixture
def real_issue_full():
    return _load_fixture("jira_issue_full.json")


@pytest.fixture
def real_issue_minimal():
    return _load_fixture("jira_issue_minimal.json")


@pytest.fixture
def real_issue_epic():
    return _load_fixture("jira_issue_epic.json")


@pytest.fixture
def real_issue_subtask():
    return _load_fixture("jira_issue_subtask.json")


@pytest.fixture
def real_issue_done():
    return _load_fixture("jira_issue_done.json")


@pytest.fixture
def real_search_assigned():
    return _load_fixture("jira_search_assigned.json")


@pytest.fixture
def real_search_labels():
    return _load_fixture("jira_search_labels.json")


@pytest.fixture
def real_comments_rich():
    return _load_fixture("jira_comments_rich.json")


@pytest.fixture
def real_worklogs_rich():
    return _load_fixture("jira_worklogs_rich.json")
