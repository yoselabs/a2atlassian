"""Connection storage — save/load/list/delete Atlassian connections as TOML files.

ConnectionInfo is a frozen Pydantic model. TOML on-disk schema mirrors it 1:1
with the v0.5.0 format; there is no backwards-compat layer for the v0.2-0.4
`project` key. Delete old connections and re-`login` if you see the upgrade error.
"""

from __future__ import annotations

import re
import shutil
import stat
import subprocess
import tempfile
import tomllib
from os import environ
from pathlib import Path

import tomli_w
from pydantic import BaseModel, ConfigDict, Field, field_validator

_ENV_REF_RE = re.compile(r"\$\{(\w+)\}")
_OP_REF_RE = re.compile(r"^op://[^\s]+$")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ConnectionInfo(BaseModel):
    """A saved Atlassian connection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    connection: str = Field(min_length=1)
    url: str
    email: str
    token: str
    read_only: bool = True
    timezone: str = "UTC"
    worklog_admins: tuple[str, ...] = ()

    @field_validator("connection")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not _NAME_RE.match(v):
            msg = f"Invalid connection name {v!r}: must start with alphanumeric, contain only [A-Za-z0-9._-]"
            raise ValueError(msg)
        return v

    @property
    def resolved_token(self) -> str:
        """Token with ${ENV_VAR} or op:// references resolved at access time.

        `${ENV_VAR}` reads from the environment (unresolved refs pass through literally
        so the failure surfaces at the call site, not here).
        `op://vault/item/field` invokes the 1Password CLI (`op read`); if `op` is not
        installed or the fetch fails, the reference passes through literally.
        """
        if _OP_REF_RE.match(self.token):
            return _resolve_op_ref(self.token)
        return _ENV_REF_RE.sub(lambda m: environ.get(m.group(1), m.group(0)), self.token)


def _resolve_op_ref(ref: str) -> str:
    """Resolve an `op://...` reference via the 1Password CLI. Returns ref unchanged on failure."""
    if shutil.which("op") is None:
        return ref
    try:
        result = subprocess.run(  # noqa: S603
            ["op", "read", ref],  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ref
    return result.stdout.rstrip("\n")


class ConnectionStore:
    """Manages connection TOML files in a config directory."""

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir

    def _path(self, connection: str) -> Path:
        if not _NAME_RE.match(connection):
            msg = f"Invalid connection name {connection!r}"
            raise ValueError(msg)
        return self.config_dir / f"{connection}.toml"

    def save(self, info: ConnectionInfo) -> Path:
        """Save a connection atomically. Creates or overwrites the TOML file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(info.connection)
        data = info.model_dump(mode="python")
        # tomli_w accepts dicts; tuple → list for TOML arrays.
        data["worklog_admins"] = list(data["worklog_admins"])
        payload = tomli_w.dumps(data).encode("utf-8")

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=self.config_dir, prefix=f".{info.connection}.", suffix=".tmp") as tmp:
            tmp.write(payload)
            tmp_path = Path(tmp.name)
        tmp_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
        tmp_path.replace(path)
        return path

    def load(self, connection: str) -> ConnectionInfo:
        """Load a connection by name. Raises FileNotFoundError if missing."""
        path = self._path(connection)
        if not path.exists():
            msg = f"Connection not found: {connection}"
            raise FileNotFoundError(msg)
        data = tomllib.loads(path.read_text())
        if "project" in data and "connection" not in data:
            msg = (
                f"Connection {connection!r} uses the pre-v0.5.0 on-disk format (key 'project'). "
                f"Delete {path} and re-run `a2atlassian login` to re-create it."
            )
            raise ValueError(msg)
        return ConnectionInfo.model_validate(data)

    def delete(self, connection: str) -> None:
        """Delete a connection. Raises FileNotFoundError if missing."""
        path = self._path(connection)
        if not path.exists():
            msg = f"Connection not found: {connection}"
            raise FileNotFoundError(msg)
        path.unlink()

    def list_connections(self) -> list[ConnectionInfo]:
        """List all saved connections."""
        if not self.config_dir.exists():
            return []
        results: list[ConnectionInfo] = []
        for path in sorted(self.config_dir.glob("*.toml")):
            data = tomllib.loads(path.read_text())
            if "project" in data and "connection" not in data:
                # Skip stale-format files in list view rather than crash the whole call.
                continue
            results.append(ConnectionInfo.model_validate(data))
        return results
