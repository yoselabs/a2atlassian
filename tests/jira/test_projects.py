"""Tests for Jira project operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2atlassian.client import AtlassianClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult
from a2atlassian.jira.projects import (
    create_version,
    get_project_components,
    get_project_metadata,
    get_project_versions,
    get_projects,
)


@pytest.fixture
def mock_client() -> AtlassianClient:
    conn = ConnectionInfo(
        connection="test",
        url="https://test.atlassian.net",
        email="t@t.com",
        token="tok",
        read_only=False,
    )
    client = AtlassianClient(conn)
    client._jira_instance = MagicMock()
    return client


class TestGetProjects:
    async def test_returns_projects(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.projects.return_value = [
            {
                "key": "PROJ",
                "name": "My Project",
                "lead": {"displayName": "Alice"},
                "projectTypeKey": "software",
            },
            {
                "key": "OPS",
                "name": "Operations",
                "lead": {"displayName": "Bob"},
                "projectTypeKey": "business",
            },
        ]
        result = await get_projects(mock_client)
        assert isinstance(result, OperationResult)
        assert len(result.data) == 2
        assert result.count == 2
        assert result.data[0]["key"] == "PROJ"
        assert result.data[0]["name"] == "My Project"
        assert result.data[0]["lead"] == "Alice"
        assert result.data[0]["project_type_key"] == "software"

    async def test_empty_projects(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.projects.return_value = []
        result = await get_projects(mock_client)
        assert result.count == 0
        assert result.data == []

    async def test_lead_as_string(self, mock_client: AtlassianClient) -> None:
        """atlassian-python-api may return lead as a string."""
        mock_client._jira_instance.projects.return_value = [
            {
                "key": "PROJ",
                "name": "My Project",
                "lead": "Alice",
                "projectTypeKey": "software",
            },
        ]
        result = await get_projects(mock_client)
        assert result.data[0]["lead"] == "Alice"

    async def test_null_lead(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.projects.return_value = [
            {
                "key": "PROJ",
                "name": "My Project",
                "lead": None,
                "projectTypeKey": "software",
            },
        ]
        result = await get_projects(mock_client)
        assert result.data[0]["lead"] == ""


class TestGetProjectVersions:
    async def test_returns_versions(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_project_versions.return_value = [
            {
                "id": "10001",
                "name": "v1.0",
                "released": True,
                "releaseDate": "2026-01-15",
            },
            {
                "id": "10002",
                "name": "v2.0",
                "released": False,
                "releaseDate": "",
            },
        ]
        result = await get_project_versions(mock_client, "PROJ")
        assert isinstance(result, OperationResult)
        assert len(result.data) == 2
        assert result.data[0]["id"] == "10001"
        assert result.data[0]["name"] == "v1.0"
        assert result.data[0]["released"] is True
        assert result.data[0]["release_date"] == "2026-01-15"
        mock_client._jira_instance.get_project_versions.assert_called_once_with("PROJ")

    async def test_handles_int_id(self, mock_client: AtlassianClient) -> None:
        """id may come as int from atlassian-python-api."""
        mock_client._jira_instance.get_project_versions.return_value = [
            {"id": 10001, "name": "v1.0", "released": False},
        ]
        result = await get_project_versions(mock_client, "PROJ")
        assert result.data[0]["id"] == "10001"

    async def test_empty_versions(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_project_versions.return_value = []
        result = await get_project_versions(mock_client, "PROJ")
        assert result.count == 0


class TestGetProjectComponents:
    async def test_returns_components(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_project_components.return_value = [
            {
                "id": "20001",
                "name": "Backend",
                "lead": {"displayName": "Alice"},
            },
            {
                "id": "20002",
                "name": "Frontend",
                "lead": {"displayName": "Bob"},
            },
        ]
        result = await get_project_components(mock_client, "PROJ")
        assert isinstance(result, OperationResult)
        assert len(result.data) == 2
        assert result.data[0]["id"] == "20001"
        assert result.data[0]["name"] == "Backend"
        assert result.data[0]["lead"] == "Alice"
        mock_client._jira_instance.get_project_components.assert_called_once_with("PROJ")

    async def test_component_lead_as_string(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_project_components.return_value = [
            {"id": "20001", "name": "Backend", "lead": "Alice"},
        ]
        result = await get_project_components(mock_client, "PROJ")
        assert result.data[0]["lead"] == "Alice"

    async def test_component_null_lead(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_project_components.return_value = [
            {"id": "20001", "name": "Backend", "lead": None},
        ]
        result = await get_project_components(mock_client, "PROJ")
        assert result.data[0]["lead"] == ""


class TestCreateVersion:
    async def test_creates_version(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.create_version.return_value = {
            "id": "10003",
            "name": "v3.0",
            "self": "https://test.atlassian.net/rest/api/2/version/10003",
        }
        result = await create_version(mock_client, "PROJ", "v3.0")
        assert isinstance(result, OperationResult)
        assert result.data["id"] == "10003"
        assert result.data["name"] == "v3.0"
        assert result.data["status"] == "created"
        mock_client._jira_instance.create_version.assert_called_once_with("v3.0", "PROJ")

    async def test_handles_int_id(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.create_version.return_value = {
            "id": 10004,
            "name": "v4.0",
        }
        result = await create_version(mock_client, "PROJ", "v4.0")
        assert result.data["id"] == "10004"


class TestGetProjectMetadata:
    async def test_components_only(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_project_components.return_value = [{"id": "1", "name": "Backend"}]
        result = await get_project_metadata(mock_client, "PROJ", include=["components"])
        assert "components" in result.data
        assert "versions" not in result.data
        assert result.data["components"] == [{"id": "1", "name": "Backend"}]

    async def test_versions_only(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_project_versions.return_value = [{"id": "1", "name": "v1", "released": False}]
        result = await get_project_metadata(mock_client, "PROJ", include=["versions"])
        assert "versions" in result.data
        assert "components" not in result.data

    async def test_all_sentinel(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_project_components.return_value = []
        mock_client._jira_instance.get_project_versions.return_value = []
        result = await get_project_metadata(mock_client, "PROJ", include=["all"])
        assert "components" in result.data
        assert "versions" in result.data

    async def test_default_all(self, mock_client: AtlassianClient) -> None:
        mock_client._jira_instance.get_project_components.return_value = []
        mock_client._jira_instance.get_project_versions.return_value = []
        result = await get_project_metadata(mock_client, "PROJ")
        assert "components" in result.data
        assert "versions" in result.data
