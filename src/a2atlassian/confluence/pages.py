"""Confluence page operations — read, search, and batch upsert."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from a2atlassian.confluence.content_format import markdown_to_storage
from a2atlassian.errors import AuthenticationError
from a2atlassian.formatter import OperationResult

if TYPE_CHECKING:
    from a2atlassian.confluence_client import ConfluenceClient


DEFAULT_PAGE_EXPAND = "body.storage,version,space"


def _extract_page_detail(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten a Confluence page response into a single-entity shape."""
    space = raw.get("space") or {}
    version = raw.get("version") or {}
    body = (raw.get("body") or {}).get("storage") or {}
    links = raw.get("_links") or {}
    return {
        "id": raw.get("id", ""),
        "title": raw.get("title", ""),
        "space_key": space.get("key", ""),
        "space_name": space.get("name", ""),
        "version": version.get("number", 0),
        "updated": version.get("when", ""),
        "url": links.get("webui", ""),
        "body": body.get("value", ""),
    }


async def get_page(
    client: ConfluenceClient,
    page_id: str,
    expand: str | None = None,
) -> OperationResult:
    """Fetch a single Confluence page by id."""
    t0 = time.monotonic()
    raw = await client._call(
        client._confluence.get_page_by_id,
        page_id,
        expand=expand or DEFAULT_PAGE_EXPAND,
    )
    elapsed = int((time.monotonic() - t0) * 1000)

    return OperationResult(
        name="get_page",
        data=_extract_page_detail(raw),
        count=1,
        truncated=False,
        time_ms=elapsed,
    )


def _extract_child_summary(raw: dict[str, Any]) -> dict[str, Any]:
    version = raw.get("version") or {}
    links = raw.get("_links") or {}
    return {
        "id": raw.get("id", ""),
        "title": raw.get("title", ""),
        "version": version.get("number", 0),
        "url": links.get("webui", ""),
    }


async def get_page_children(
    client: ConfluenceClient,
    page_id: str,
    limit: int = 50,
    offset: int = 0,
) -> OperationResult:
    """List direct children of a Confluence page."""
    t0 = time.monotonic()
    raw = await client._call(
        client._confluence.get_page_child_by_type,
        page_id,
        type="page",
        start=offset,
        limit=limit,
    )
    elapsed = int((time.monotonic() - t0) * 1000)

    items = raw if isinstance(raw, list) else (raw or {}).get("results", [])
    return OperationResult(
        name="get_page_children",
        data=[_extract_child_summary(item) for item in items],
        count=len(items),
        truncated=len(items) >= limit,
        time_ms=elapsed,
    )


async def resolve_page_identity(
    client: ConfluenceClient,
    space: str,
    title: str,
    page_id: str | None,
    parent_id: str | None,
) -> str | None:
    """Resolve a page id for upsert. Returns the id if an existing page matches, None if not.

    Precedence:
      1. page_id given → must exist; raise if missing.
      2. parent_id given → search that parent's children for a title match (this parent only).
      3. Otherwise → search the space root by title.

    Per-parent scope is deliberate: same title under a different parent counts as a miss.
    """
    if page_id:
        existing = await client._call(client._confluence.get_page_by_id, page_id)
        if not existing:
            msg = f"page_id {page_id} not found"
            raise ValueError(msg)
        return page_id

    if parent_id:
        children = await client._call(client._confluence.get_page_child_by_type, parent_id, type="page", start=0, limit=200)
        items = children if isinstance(children, list) else (children or {}).get("results", [])
        for child in items:
            if child.get("title") == title:
                return str(child.get("id"))
        return None

    top = await client._call(client._confluence.get_page_by_title, space=space, title=title)
    if top:
        return str(top.get("id"))
    return None


async def _apply_labels(client: ConfluenceClient, page_id: str, labels: list[str] | None) -> None:
    if not labels:
        return
    for label in labels:
        await client._call(client._confluence.set_page_label, page_id, label)


async def _apply_emoji(client: ConfluenceClient, page_id: str, emoji: str | None) -> None:
    if emoji is None:
        return
    await client._call(
        client._confluence.set_page_property,
        page_id,
        {"key": "emoji-title-published", "value": emoji},
    )


async def _apply_page_width(client: ConfluenceClient, page_id: str, page_width: str | None) -> None:
    if page_width is None:
        return
    await client._call(
        client._confluence.set_page_property,
        page_id,
        {"key": "content-appearance-published", "value": page_width},
    )


async def upsert_page(
    client: ConfluenceClient,
    *,
    space: str,
    title: str,
    content: str,
    parent_id: str | None,
    page_id: str | None,
    content_format: str,
    page_width: str | None,
    emoji: str | None,
    labels: list[str] | None,
) -> dict[str, Any]:
    """Create or update a single Confluence page. Returns a succeeded-shaped dict.

    Caller (batch upsert) wraps exceptions; this function may raise.
    """
    body = content if content_format == "storage" else markdown_to_storage(content)
    resolved = await resolve_page_identity(client, space=space, title=title, page_id=page_id, parent_id=parent_id)

    if resolved is None:
        raw = await client._call(
            client._confluence.create_page,
            space=space,
            title=title,
            body=body,
            parent_id=parent_id,
            type="page",
            representation="storage",
        )
        status = "created"
    else:
        raw = await client._call(
            client._confluence.update_page,
            page_id=resolved,
            title=title,
            body=body,
            parent_id=parent_id,
            representation="storage",
        )
        status = "updated"

    links = raw.get("_links") or {}
    version = (raw.get("version") or {}).get("number", 0)
    page_id_out = str(raw.get("id", resolved or ""))

    await _apply_labels(client, page_id_out, labels)
    await _apply_emoji(client, page_id_out, emoji)
    # On create, default page_width to "fixed-width" if caller did not specify.
    effective_width = page_width if page_width is not None else ("fixed-width" if status == "created" else None)
    await _apply_page_width(client, page_id_out, effective_width)

    return {
        "title": title,
        "page_id": page_id_out,
        "status": status,
        "url": links.get("webui", ""),
        "version": version,
    }


def _classify_error(exc: BaseException) -> str:
    if isinstance(exc, AuthenticationError):
        return "permission"
    status = None
    from requests.exceptions import HTTPError  # noqa: PLC0415

    if isinstance(exc, HTTPError):
        status = getattr(exc.response, "status_code", None)
    if status == 400:
        return "format"
    if status == 409:
        return "conflict"
    if status in (401, 403):
        return "permission"
    return "other"


async def upsert_pages(
    client: ConfluenceClient,
    pages: list[dict[str, Any]],
) -> OperationResult:
    """Batch create-or-update. Returns per-page outcomes; never raises on partial failure."""
    t0 = time.monotonic()
    succeeded: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    created = updated = 0

    for page in pages:
        title = page.get("title", "")
        try:
            out = await upsert_page(
                client,
                space=page["space"],
                title=title,
                content=page["content"],
                parent_id=page.get("parent_id"),
                page_id=page.get("page_id"),
                content_format=page.get("content_format", "markdown"),
                page_width=page.get("page_width"),
                emoji=page.get("emoji"),
                labels=page.get("labels"),
            )
            succeeded.append(out)
            if out["status"] == "created":
                created += 1
            else:
                updated += 1
        except Exception as exc:  # noqa: BLE001 — batch semantics require swallowing per-page errors
            failed.append({"title": title, "error": str(exc), "error_category": _classify_error(exc)})

    elapsed = int((time.monotonic() - t0) * 1000)
    summary = {"total": len(pages), "created": created, "updated": updated, "failed": len(failed)}

    return OperationResult(
        name="upsert_pages",
        data={"succeeded": succeeded, "failed": failed, "summary": summary},
        count=len(pages),
        truncated=False,
        time_ms=elapsed,
    )
