"""Decorators for tool access control."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any

from a2atlassian.config import DEFAULT_CONFIG_DIR
from a2atlassian.connections import ConnectionStore
from a2atlassian.errors import WriteAccessDeniedError

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
