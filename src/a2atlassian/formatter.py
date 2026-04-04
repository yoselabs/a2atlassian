"""Output formatting — TOON and JSON renderers for Atlassian API results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

FIELD_MAX_LENGTH = 2000


def _toon_encode(data: list[dict]) -> str:  # type: ignore[type-arg]
    """Fallback TOON encoder: header row + tab-separated data rows."""
    if not data:
        return ""
    keys = list(data[0].keys())
    header = "\t".join(keys)
    rows = "\n".join("\t".join(str(item.get(k, "")) for k in keys) for item in data)
    return f"{header}\n{rows}"


@dataclass
class OperationResult:
    """Result of a single API operation."""

    name: str
    data: Any  # dict for single entity, list[dict] for collections
    count: int
    truncated: bool
    time_ms: int = 0


def _truncate_fields(obj: Any) -> Any:
    """Recursively truncate string fields exceeding FIELD_MAX_LENGTH."""
    if isinstance(obj, str):
        if len(obj) > FIELD_MAX_LENGTH:
            return obj[:FIELD_MAX_LENGTH] + "... [truncated]"
        return obj
    if isinstance(obj, dict):
        return {k: _truncate_fields(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_truncate_fields(item) for item in obj]
    return obj


def _format_json(result: OperationResult) -> str:
    """Format as JSON with metadata."""
    truncated_data = _truncate_fields(result.data)
    output = {
        "data": truncated_data,
        "count": result.count,
        "truncated": result.truncated,
        "time_ms": result.time_ms,
    }
    return json.dumps(output, indent=2, default=str, ensure_ascii=False)


def _format_toon(result: OperationResult) -> str:
    """Format as TOON for list results, JSON for single entities."""
    # Single entities → JSON (TOON is for uniform arrays)
    if isinstance(result.data, dict):
        return _format_json(result)

    truncated_data = _truncate_fields(result.data)

    # Build TOON output with metadata header
    metadata = f"# {result.name} ({result.count} results, {result.time_ms}ms, truncated: {result.truncated})"
    toon_body = _toon_encode(truncated_data)
    return f"{metadata}\n{toon_body}"


def format_result(result: OperationResult, fmt: str = "toon") -> str:
    """Format an operation result in the specified format."""
    if fmt == "json":
        return _format_json(result)
    return _format_toon(result)
