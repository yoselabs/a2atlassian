"""Shape validation tests for project extractors against real fixture data."""

from __future__ import annotations

from a2atlassian.jira.projects import (
    _extract_component,
    _extract_project,
    _extract_version,
)


def _assert_flat(result: dict) -> None:
    """Assert no nested dicts or lists leaked through."""
    for key, value in result.items():
        assert not isinstance(value, dict), f"Nested dict at '{key}'"
        assert not isinstance(value, list), f"List at '{key}'"


class TestExtractProject:
    def test_handles_real_shape(self, real_projects):
        projects = real_projects["items"]
        for project in projects:
            result = _extract_project(project)
            _assert_flat(result)

    def test_expected_keys(self, real_projects):
        projects = real_projects["items"]
        result = _extract_project(projects[0])
        assert set(result.keys()) == {
            "key",
            "name",
            "lead",
            "project_type_key",
        }


class TestExtractVersion:
    def test_handles_real_shape(self, real_project_versions):
        versions = real_project_versions["items"]
        for version in versions:
            result = _extract_version(version)
            _assert_flat(result)

    def test_expected_keys(self, real_project_versions):
        versions = real_project_versions["items"]
        result = _extract_version(versions[0])
        assert set(result.keys()) == {
            "id",
            "name",
            "released",
            "release_date",
        }


class TestExtractComponent:
    def test_handles_real_shape(self, real_project_components):
        components = real_project_components["items"]
        for component in components:
            result = _extract_component(component)
            _assert_flat(result)

    def test_expected_keys(self, real_project_components):
        components = real_project_components["items"]
        result = _extract_component(components[0])
        assert set(result.keys()) == {
            "id",
            "name",
            "lead",
        }
