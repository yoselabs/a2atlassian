"""Decorators for tool access control."""

from __future__ import annotations

import functools
import inspect
import typing
from typing import TYPE_CHECKING, Any, Literal, get_args, get_origin

from a2atlassian.formatter import format_result

if TYPE_CHECKING:
    from a2atlassian.connections import ConnectionInfo
    from a2atlassian.errors import ErrorEnricher


def check_writable(conn: ConnectionInfo, connection_name: str) -> None:
    """Raise RuntimeError if the connection is read-only. Caught by @mcp_tool and enriched."""
    if conn.read_only:
        raise RuntimeError(f"Connection '{connection_name}' is read-only. Run: a2atlassian login -c {connection_name} --no-read-only")


def _collect_literal_params(fn: Any) -> dict[str, tuple[object, ...]]:
    """Return a mapping of parameter name to its Literal choices for parameters annotated with Literal[...]."""
    try:
        hints = typing.get_type_hints(fn, include_extras=False)
    except Exception:  # noqa: BLE001
        hints = {}
    literals: dict[str, tuple[object, ...]] = {}
    for name, hint in hints.items():
        if get_origin(hint) is Literal:
            literals[name] = get_args(hint)
    return literals


def mcp_tool(
    enricher: ErrorEnricher,
) -> Any:
    """Wrap an async MCP tool coroutine that returns OperationResult.

    Responsibilities:
    - Validate Literal[...] parameters at call time (enum validation).
    - Run the wrapped coroutine; enrich any raised exception into a user-facing error string.
    - Format the OperationResult using the tool's format argument (or 'toon' default).
    """

    def decorator(fn: Any) -> Any:
        literals = _collect_literal_params(fn)
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> str:
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()

            for param, choices in literals.items():
                if param not in bound.arguments:
                    continue
                value = bound.arguments[param]
                if value not in choices:
                    return enricher.enum_mismatch(param, value, choices)

            connection = bound.arguments.get("connection") or bound.arguments.get("project")
            try:
                result = await fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                ctx: dict[str, Any] = {}
                if connection is not None:
                    ctx["connection"] = connection
                return enricher.enrich(str(exc), ctx)

            if isinstance(result, str):
                return result
            fmt = bound.arguments.get("format", "toon")
            return format_result(result, fmt=fmt)

        # The wrapper always returns `str` (formatted output), not OperationResult.
        # FastMCP inspects annotations with inspect.signature(follow_wrapped=True,
        # eval_str=True), which reaches through @functools.wraps to fn itself.
        # Overwrite the return on BOTH objects so FastMCP builds an output_schema
        # matching the wrapper's actual return value — otherwise it validates the
        # formatted JSON string against OperationResult's dict schema and raises
        # "Input should be a valid dictionary or object to extract fields from".
        fn.__annotations__ = {**fn.__annotations__, "return": str}
        wrapper.__annotations__ = {**wrapper.__annotations__, "return": str}

        return wrapper

    return decorator
