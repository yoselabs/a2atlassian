"""Tests for Confluence page operations."""

from __future__ import annotations

import json
import json as _json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from a2atlassian.confluence.pages import get_page, get_page_children, resolve_page_identity, upsert_page, upsert_pages
from a2atlassian.confluence_client import ConfluenceClient
from a2atlassian.connections import ConnectionInfo
from a2atlassian.formatter import OperationResult

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mock_client() -> ConfluenceClient:
    conn = ConnectionInfo(
        connection="t",
        url="https://t.atlassian.net",
        email="t@t.com",
        token="tok",
        read_only=True,
    )
    client = ConfluenceClient(conn)
    client._confluence_instance = MagicMock()
    return client


class TestGetPage:
    async def test_returns_operation_result(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_id.return_value = json.loads((FIXTURES / "confluence_page.json").read_text())
        result = await get_page(mock_client, "123456789")
        assert isinstance(result, OperationResult)
        assert result.data["id"] == "123456789"
        assert result.data["title"] == "Example page"
        assert result.data["space_key"] == "TEAM"
        assert result.data["version"] == 3
        assert "body" in result.data
        assert result.count == 1
        assert result.truncated is False

    async def test_passes_expand_default(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_id.return_value = {
            "id": "1",
            "title": "",
            "space": {},
            "version": {},
            "body": {"storage": {"value": ""}},
        }
        await get_page(mock_client, "1")
        call = mock_client._confluence_instance.get_page_by_id.call_args
        assert call.kwargs.get("expand") == "body.storage,version,space"


class TestGetPageChildren:
    async def test_returns_list_result(self, mock_client: ConfluenceClient) -> None:
        import json as _json

        mock_client._confluence_instance.get_page_child_by_type.return_value = _json.loads(
            (FIXTURES / "confluence_page_children.json").read_text()
        )["results"]
        result = await get_page_children(mock_client, "100", limit=50, offset=0)
        assert isinstance(result, OperationResult)
        assert result.count == 2
        assert result.data[0]["id"] == "200"
        assert result.data[0]["title"] == "Child A"
        assert result.data[0]["version"] == 1
        assert result.data[0]["url"].endswith("/pages/200")

    async def test_passes_pagination_params(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_child_by_type.return_value = []
        await get_page_children(mock_client, "100", limit=10, offset=20)
        call = mock_client._confluence_instance.get_page_child_by_type.call_args
        assert call.kwargs.get("start") == 20
        assert call.kwargs.get("limit") == 10
        assert call.kwargs.get("type") == "page"


class TestResolveIdentity:
    async def test_page_id_wins(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_id.return_value = {"id": "42", "title": "X"}
        resolved = await resolve_page_identity(mock_client, space="SP", title="ignored", page_id="42", parent_id=None)
        assert resolved == "42"

    async def test_page_id_missing_raises(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_id.return_value = None
        with pytest.raises(ValueError, match="page_id"):
            await resolve_page_identity(mock_client, space="SP", title="ignored", page_id="999", parent_id=None)

    async def test_parent_scoped_match(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_child_by_type.return_value = [
            {"id": "100", "title": "Report"},
            {"id": "101", "title": "Other"},
        ]
        resolved = await resolve_page_identity(mock_client, space="SP", title="Report", page_id=None, parent_id="50")
        assert resolved == "100"
        call = mock_client._confluence_instance.get_page_child_by_type.call_args
        assert call.args[0] == "50"

    async def test_parent_scoped_no_match_returns_none(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_child_by_type.return_value = [{"id": "100", "title": "X"}]
        resolved = await resolve_page_identity(mock_client, space="SP", title="Missing", page_id=None, parent_id="50")
        assert resolved is None

    async def test_space_root_match(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_title.return_value = {"id": "200", "title": "Top"}
        resolved = await resolve_page_identity(mock_client, space="SP", title="Top", page_id=None, parent_id=None)
        assert resolved == "200"

    async def test_space_root_no_match_returns_none(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_title.return_value = None
        resolved = await resolve_page_identity(mock_client, space="SP", title="Nope", page_id=None, parent_id=None)
        assert resolved is None


class TestUpsertSingle:
    async def test_create_when_no_existing(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_title.return_value = None
        mock_client._confluence_instance.create_page.return_value = _json.loads(
            (FIXTURES / "confluence_create_page_response.json").read_text()
        )
        result = await upsert_page(
            mock_client,
            space="SP",
            title="New",
            content="# hi",
            parent_id=None,
            page_id=None,
            content_format="markdown",
            page_width=None,
            emoji=None,
            labels=None,
        )
        assert result["status"] == "created"
        assert result["page_id"] == "900"
        assert result["version"] == 1
        call = mock_client._confluence_instance.create_page.call_args
        assert call.kwargs.get("representation") == "storage"
        assert "<h1>hi</h1>" in call.kwargs.get("body", "")

    async def test_update_when_match(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_title.return_value = {"id": "900", "title": "New"}
        mock_client._confluence_instance.update_page.return_value = _json.loads(
            (FIXTURES / "confluence_update_page_response.json").read_text()
        )
        result = await upsert_page(
            mock_client,
            space="SP",
            title="New",
            content="body",
            parent_id=None,
            page_id=None,
            content_format="markdown",
            page_width=None,
            emoji=None,
            labels=None,
        )
        assert result["status"] == "updated"
        assert result["page_id"] == "900"
        assert result["version"] == 4

    async def test_storage_bypasses_translator(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_title.return_value = None
        mock_client._confluence_instance.create_page.return_value = {"id": "1", "version": {"number": 1}, "_links": {"webui": "/p/1"}}
        raw = '<ac:structured-macro ac:name="info"><ac:rich-text-body><p>x</p></ac:rich-text-body></ac:structured-macro>'
        await upsert_page(
            mock_client,
            space="SP",
            title="T",
            content=raw,
            parent_id=None,
            page_id=None,
            content_format="storage",
            page_width=None,
            emoji=None,
            labels=None,
        )
        call = mock_client._confluence_instance.create_page.call_args
        assert call.kwargs.get("body") == raw  # passed through unchanged


class TestUpsertBatch:
    async def test_all_success(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_title.return_value = None
        mock_client._confluence_instance.create_page.side_effect = [
            {"id": "1", "version": {"number": 1}, "_links": {"webui": "/p/1"}},
            {"id": "2", "version": {"number": 1}, "_links": {"webui": "/p/2"}},
        ]
        result = await upsert_pages(
            mock_client,
            pages=[
                {"space": "SP", "title": "A", "content": "hi"},
                {"space": "SP", "title": "B", "content": "hello"},
            ],
        )
        assert isinstance(result, OperationResult)
        assert result.data["summary"] == {"total": 2, "created": 2, "updated": 0, "failed": 0}
        assert len(result.data["succeeded"]) == 2
        assert result.data["failed"] == []

    async def test_partial_failure_does_not_raise(self, mock_client: ConfluenceClient) -> None:
        from requests.exceptions import HTTPError
        from requests.models import Response

        def _err(status: int) -> HTTPError:
            r = Response()
            r.status_code = status
            return HTTPError(response=r)

        mock_client._confluence_instance.get_page_by_title.return_value = None
        mock_client._confluence_instance.create_page.side_effect = [
            {"id": "1", "version": {"number": 1}, "_links": {"webui": "/p/1"}},
            _err(403),
            _err(400),
        ]
        result = await upsert_pages(
            mock_client,
            pages=[
                {"space": "SP", "title": "A", "content": "hi"},
                {"space": "SP", "title": "B", "content": "hi"},
                {"space": "SP", "title": "C", "content": "hi"},
            ],
        )
        assert result.data["summary"] == {"total": 3, "created": 1, "updated": 0, "failed": 2}
        assert len(result.data["succeeded"]) == 1
        assert len(result.data["failed"]) == 2
        categories = {f["error_category"] for f in result.data["failed"]}
        assert "permission" in categories  # 403 via AuthenticationError
        assert "format" in categories  # 400 raw HTTPError

    async def test_updated_counter_increments(self, mock_client: ConfluenceClient) -> None:
        # covers line 269: updated += 1 branch
        mock_client._confluence_instance.get_page_by_title.side_effect = [
            {"id": "1", "title": "A"},
            {"id": "2", "title": "B"},
        ]
        mock_client._confluence_instance.update_page.side_effect = [
            {"id": "1", "version": {"number": 2}, "_links": {"webui": "/p/1"}},
            {"id": "2", "version": {"number": 3}, "_links": {"webui": "/p/2"}},
        ]
        result = await upsert_pages(
            mock_client,
            pages=[
                {"space": "SP", "title": "A", "content": "hi"},
                {"space": "SP", "title": "B", "content": "hi"},
            ],
        )
        assert result.data["summary"] == {"total": 2, "created": 0, "updated": 2, "failed": 0}

    async def test_conflict_and_other_error_categories(self, mock_client: ConfluenceClient) -> None:
        # covers lines 233-237: conflict (409) and other error categories
        from requests.exceptions import HTTPError
        from requests.models import Response

        def _err(status: int) -> HTTPError:
            r = Response()
            r.status_code = status
            return HTTPError(response=r)

        mock_client._confluence_instance.get_page_by_title.return_value = None
        mock_client._confluence_instance.create_page.side_effect = [
            _err(409),
            RuntimeError("unexpected"),
        ]
        result = await upsert_pages(
            mock_client,
            pages=[
                {"space": "SP", "title": "X", "content": "hi"},
                {"space": "SP", "title": "Y", "content": "hi"},
            ],
        )
        categories = {f["error_category"] for f in result.data["failed"]}
        assert "conflict" in categories
        assert "other" in categories

    async def test_empty_batch(self, mock_client: ConfluenceClient) -> None:
        result = await upsert_pages(mock_client, pages=[])
        assert result.data["summary"] == {"total": 0, "created": 0, "updated": 0, "failed": 0}


class TestUpsertKnobs:
    async def test_labels_applied_after_save(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_title.return_value = None
        mock_client._confluence_instance.create_page.return_value = {
            "id": "9",
            "version": {"number": 1},
            "_links": {"webui": "/p/9"},
        }
        await upsert_page(
            mock_client,
            space="SP",
            title="T",
            content="x",
            parent_id=None,
            page_id=None,
            content_format="markdown",
            page_width=None,
            emoji=None,
            labels=["alpha", "beta"],
        )
        calls = mock_client._confluence_instance.set_page_label.call_args_list
        assert len(calls) == 2
        assert {c.args[1] for c in calls} == {"alpha", "beta"}
        assert all(c.args[0] == "9" for c in calls)

    async def test_emoji_and_page_width_create_property_when_missing(self, mock_client: ConfluenceClient) -> None:
        from atlassian.errors import ApiError

        mock_client._confluence_instance.get_page_by_title.return_value = None
        mock_client._confluence_instance.create_page.return_value = {
            "id": "9",
            "version": {"number": 1},
            "_links": {"webui": "/p/9"},
        }
        mock_client._confluence_instance.get_page_property.side_effect = ApiError("not found")
        await upsert_page(
            mock_client,
            space="SP",
            title="T",
            content="x",
            parent_id=None,
            page_id=None,
            content_format="markdown",
            page_width="full-width",
            emoji="📄",
            labels=None,
        )
        set_calls = mock_client._confluence_instance.set_page_property.call_args_list
        keys_set = {c.args[1]["key"] for c in set_calls}
        assert keys_set == {"emoji-title-published", "content-appearance-published"}
        mock_client._confluence_instance.update_page_property.assert_not_called()

    async def test_page_width_updates_existing_property_with_version_bump(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_title.return_value = {"id": "9", "title": "T"}
        mock_client._confluence_instance.update_page.return_value = {
            "id": "9",
            "version": {"number": 2},
            "_links": {"webui": "/p/9"},
        }
        mock_client._confluence_instance.get_page_property.return_value = {
            "key": "content-appearance-published",
            "value": "fixed-width",
            "version": {"number": 3},
        }
        await upsert_page(
            mock_client,
            space="SP",
            title="T",
            content="x",
            parent_id=None,
            page_id=None,
            content_format="markdown",
            page_width="full-width",
            emoji=None,
            labels=None,
        )
        update_calls = mock_client._confluence_instance.update_page_property.call_args_list
        assert len(update_calls) == 1
        payload = update_calls[0].args[1]
        assert payload["key"] == "content-appearance-published"
        assert payload["value"] == "full-width"
        assert payload["version"] == {"number": 4}
        mock_client._confluence_instance.set_page_property.assert_not_called()

    async def test_page_width_none_on_update_does_not_touch_property(self, mock_client: ConfluenceClient) -> None:
        mock_client._confluence_instance.get_page_by_title.return_value = {"id": "9", "title": "T"}
        mock_client._confluence_instance.update_page.return_value = {
            "id": "9",
            "version": {"number": 2},
            "_links": {"webui": "/p/9"},
        }
        mock_client._confluence_instance.set_page_property.reset_mock()
        await upsert_page(
            mock_client,
            space="SP",
            title="T",
            content="x",
            parent_id=None,
            page_id=None,
            content_format="markdown",
            page_width=None,
            emoji=None,
            labels=None,
        )
        mock_client._confluence_instance.set_page_property.assert_not_called()
        mock_client._confluence_instance.update_page_property.assert_not_called()
