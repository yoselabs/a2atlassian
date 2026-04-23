"""Connection storage — save/load/list/delete Atlassian connections as TOML files."""

from __future__ import annotations

import os
import re
import stat
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class ConnectionInfo:
    """A saved Atlassian connection."""

    connection: str
    url: str
    email: str
    token: str
    read_only: bool = True

    @property
    def resolved_token(self) -> str:
        """Token with ${ENV_VAR} references expanded from the environment."""
        return re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), m.group(0)), self.token)


class ConnectionStore:
    """Manages connection TOML files in a config directory."""

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir

    def _path(self, connection: str) -> Path:
        return self.config_dir / f"{connection}.toml"

    def save(self, connection: str, url: str, email: str, token: str, read_only: bool = True) -> Path:
        """Save a connection. Creates or overwrites the TOML file. Returns the path."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(connection)

        def _escape(value: str) -> str:
            return value.replace("\\", "\\\\").replace('"', '\\"')

        ro = "true" if read_only else "false"
        content = (
            f'project = "{_escape(connection)}"\n'
            f'url = "{_escape(url)}"\n'
            f'email = "{_escape(email)}"\n'
            f'token = "{_escape(token)}"\n'
            f"read_only = {ro}\n"
        )
        path.write_text(content)
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
        return path

    def load(self, connection: str) -> ConnectionInfo:
        """Load a connection by name. Raises FileNotFoundError if missing."""
        path = self._path(connection)
        if not path.exists():
            msg = f"Connection not found: {connection}"
            raise FileNotFoundError(msg)
        data = tomllib.loads(path.read_text())
        return ConnectionInfo(
            connection=data["project"],
            url=data["url"],
            email=data["email"],
            token=data["token"],
            read_only=data.get("read_only", True),
        )

    def delete(self, connection: str) -> None:
        """Delete a connection. Raises FileNotFoundError if missing."""
        path = self._path(connection)
        if not path.exists():
            msg = f"Connection not found: {connection}"
            raise FileNotFoundError(msg)
        path.unlink()

    def list_connections(self, connection: str | None = None) -> list[ConnectionInfo]:
        """List all saved connections, optionally filtered by connection name."""
        if not self.config_dir.exists():
            return []
        results = []
        for path in sorted(self.config_dir.glob("*.toml")):
            data = tomllib.loads(path.read_text())
            info = ConnectionInfo(
                connection=data["project"],
                url=data["url"],
                email=data["email"],
                token=data["token"],
                read_only=data.get("read_only", True),
            )
            if connection is None or info.connection == connection:
                results.append(info)
        return results
