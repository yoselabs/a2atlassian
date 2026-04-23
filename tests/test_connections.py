"""Tests for connection storage — save/load/list/delete TOML files."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from a2atlassian.connections import ConnectionInfo, ConnectionStore

if TYPE_CHECKING:
    from pathlib import Path


def _info(**overrides: object) -> ConnectionInfo:
    defaults = {
        "connection": "proj",
        "url": "https://x.atlassian.net",
        "email": "a@b.com",
        "token": "tok",
    }
    defaults.update(overrides)
    return ConnectionInfo(**defaults)  # type: ignore[arg-type]


class TestConnectionInfo:
    def test_frozen(self, sample_connection: ConnectionInfo) -> None:
        with pytest.raises(ValidationError):
            sample_connection.connection = "other"  # type: ignore[misc]

    def test_resolved_token_literal(self) -> None:
        info = _info(token="literal-token")
        assert info.resolved_token == "literal-token"

    def test_resolved_token_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_TOKEN", "secret-from-env")
        info = _info(token="${MY_TOKEN}")
        assert info.resolved_token == "secret-from-env"

    def test_resolved_token_missing_env_var(self) -> None:
        info = _info(token="${NONEXISTENT_VAR}")
        assert info.resolved_token == "${NONEXISTENT_VAR}"

    def test_read_only_default(self) -> None:
        assert _info().read_only is True

    def test_invalid_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _info(connection="../evil")
        with pytest.raises(ValidationError):
            _info(connection=".hidden")
        with pytest.raises(ValidationError):
            _info(connection="has/slash")
        with pytest.raises(ValidationError):
            _info(connection="")

    def test_valid_names(self) -> None:
        _info(connection="proj")
        _info(connection="proj-1")
        _info(connection="proj_1")
        _info(connection="proj.1")
        _info(connection="Proj1")

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ConnectionInfo.model_validate({"connection": "p", "url": "https://x", "email": "a@b", "token": "t", "rogue": "x"})


class TestOpReference:
    def test_op_ref_without_op_cli_passes_through(self) -> None:
        info = _info(token="op://vault/item/field")
        with patch("a2atlassian.connections.shutil.which", return_value=None):
            assert info.resolved_token == "op://vault/item/field"

    def test_op_ref_success(self) -> None:
        info = _info(token="op://vault/item/field")
        with (
            patch("a2atlassian.connections.shutil.which", return_value="/usr/local/bin/op"),
            patch("a2atlassian.connections.subprocess.run") as run,
        ):
            run.return_value.stdout = "secret-from-op\n"
            assert info.resolved_token == "secret-from-op"
            run.assert_called_once()
            args = run.call_args.args[0]
            assert args[:2] == ["op", "read"]
            assert args[2] == "op://vault/item/field"

    def test_op_ref_failure_passes_through(self) -> None:
        import subprocess as sp

        info = _info(token="op://vault/item/field")
        with (
            patch("a2atlassian.connections.shutil.which", return_value="/usr/local/bin/op"),
            patch(
                "a2atlassian.connections.subprocess.run",
                side_effect=sp.CalledProcessError(1, "op"),
            ),
        ):
            assert info.resolved_token == "op://vault/item/field"


class TestConnectionStore:
    def test_save_and_load_roundtrip(self, tmp_config_dir: Path, sample_connection: ConnectionInfo) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save(sample_connection)
        loaded = store.load(sample_connection.connection)
        assert loaded == sample_connection

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        store = ConnectionStore(tmp_path / "new" / "nested" / "dir")
        store.save(_info())
        assert (tmp_path / "new" / "nested" / "dir" / "proj.toml").exists()

    def test_save_file_permissions(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        path = store.save(_info())
        assert stat.S_IMODE(path.stat().st_mode) == 0o600

    def test_save_read_write(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save(_info(read_only=False))
        assert store.load("proj").read_only is False

    def test_load_not_found(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        with pytest.raises(FileNotFoundError, match="Connection not found: nonexistent"):
            store.load("nonexistent")

    def test_load_rejects_legacy_format(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        path = tmp_config_dir / "old.toml"
        tmp_config_dir.mkdir(parents=True, exist_ok=True)
        path.write_text('project = "old"\nurl = "https://x.atlassian.net"\nemail = "a@b.com"\ntoken = "t"\nread_only = true\n')
        with pytest.raises(ValueError, match=r"pre-v0\.5\.0 on-disk format"):
            store.load("old")

    def test_delete(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save(_info())
        store.delete("proj")
        with pytest.raises(FileNotFoundError):
            store.load("proj")

    def test_delete_not_found(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        with pytest.raises(FileNotFoundError, match="Connection not found: ghost"):
            store.delete("ghost")

    def test_list_empty(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        assert store.list_connections() == []

    def test_list_multiple(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save(_info(connection="alpha", url="https://a.atlassian.net"))
        store.save(_info(connection="beta", url="https://b.atlassian.net"))
        results = store.list_connections()
        names = [r.connection for r in results]
        assert names == ["alpha", "beta"]

    def test_list_skips_legacy_files(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        tmp_config_dir.mkdir(parents=True, exist_ok=True)
        (tmp_config_dir / "legacy.toml").write_text('project = "legacy"\nurl = "x"\nemail = "a@b"\ntoken = "t"\n')
        store.save(_info(connection="alpha"))
        names = [r.connection for r in store.list_connections()]
        assert names == ["alpha"]

    def test_list_no_dir(self, tmp_path: Path) -> None:
        store = ConnectionStore(tmp_path / "nonexistent")
        assert store.list_connections() == []

    def test_save_overwrites(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save(_info(url="https://old.atlassian.net", token="old-tok"))
        store.save(_info(url="https://new.atlassian.net", token="new-tok"))
        loaded = store.load("proj")
        assert loaded.url == "https://new.atlassian.net"
        assert loaded.token == "new-tok"

    def test_token_with_special_chars(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        token = 'token"with\\special'
        store.save(_info(token=token))
        assert store.load("proj").token == token

    def test_save_is_atomic_no_leftover_tmp(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save(_info())
        tmps = list(tmp_config_dir.glob(".*.tmp"))
        assert tmps == []

    def test_save_rejects_traversal_via_info(self) -> None:
        with pytest.raises(ValidationError):
            _info(connection="../etc/passwd")

    def test_load_rejects_traversal_name(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        with pytest.raises(ValueError, match="Invalid connection name"):
            store.load("../etc/passwd")

    def test_delete_rejects_traversal_name(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        with pytest.raises(ValueError, match="Invalid connection name"):
            store.delete("../etc/passwd")


class TestTimezone:
    def test_default_is_utc(self, tmp_path: Path) -> None:
        store = ConnectionStore(tmp_path)
        store.save(_info(connection="c"))
        assert store.load("c").timezone == "UTC"

    def test_roundtrip(self, tmp_path: Path) -> None:
        store = ConnectionStore(tmp_path)
        store.save(_info(connection="c", timezone="Europe/Istanbul"))
        assert store.load("c").timezone == "Europe/Istanbul"


class TestWorklogAdmins:
    def test_default_empty(self, tmp_path: Path) -> None:
        store = ConnectionStore(tmp_path)
        store.save(_info(connection="c"))
        assert store.load("c").worklog_admins == ()

    def test_roundtrip(self, tmp_path: Path) -> None:
        store = ConnectionStore(tmp_path)
        store.save(_info(connection="c", worklog_admins=("a@x.com", "b@x.com")))
        assert store.load("c").worklog_admins == ("a@x.com", "b@x.com")
