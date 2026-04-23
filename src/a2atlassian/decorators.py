"""Decorators for tool access control."""

from __future__ import annotations

import functools
import inspect
import typing
from typing import TYPE_CHECKING, Any, Literal, get_args, get_origin

from a2atlassian.config import DEFAULT_CONFIG_DIR
from a2atlassian.connections import ConnectionStore
from a2atlassian.errors import ErrorEnricher, WriteAccessDeniedError
from a2atlassian.formatter import format_result

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


def _default_store() -> ConnectionStore:
    return ConnectionStore(DEFAULT_CONFIG_DIR)


def write_operation(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
    """Decorator for tools that modify data. Checks read_only flag before executing.

    Accepts an optional _store kwarg for testing. Removes it before calling the inner function.
    """

    @functools.wraps(func)
    async def wrapper(**kwargs: Any) -> Any:
        store = kwargs.pop("_store", None) or _default_store()
        project = kwargs["project"]
        conn = store.load(project)
        if conn.read_only:
            raise WriteAccessDeniedError(
                f"Connection '{project}' is read-only. Re-run 'a2atlassian login -p {project} --read-only false' to enable writes."
            )
        return await func(**kwargs)

    return wrapper


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

            fmt = bound.arguments.get("format", "toon")
            return format_result(result, fmt=fmt)

        return wrapper

    return decorator
