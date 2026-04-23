"""Tests for connection storage — save/load/list/delete TOML files."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING

import pytest

from a2atlassian.connections import ConnectionInfo, ConnectionStore

if TYPE_CHECKING:
    from pathlib import Path


class TestConnectionInfo:
    def test_frozen_dataclass(self, sample_connection: ConnectionInfo) -> None:
        with pytest.raises(AttributeError):
            sample_connection.connection = "other"  # type: ignore[misc]

    def test_resolved_token_literal(self) -> None:
        info = ConnectionInfo(connection="p", url="https://x.atlassian.net", email="a@b.com", token="literal-token")
        assert info.resolved_token == "literal-token"

    def test_resolved_token_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_TOKEN", "secret-from-env")
        info = ConnectionInfo(connection="p", url="https://x.atlassian.net", email="a@b.com", token="${MY_TOKEN}")
        assert info.resolved_token == "secret-from-env"

    def test_resolved_token_missing_env_var(self) -> None:
        info = ConnectionInfo(connection="p", url="https://x.atlassian.net", email="a@b.com", token="${NONEXISTENT_VAR}")
        assert info.resolved_token == "${NONEXISTENT_VAR}"

    def test_read_only_default(self) -> None:
        info = ConnectionInfo(connection="p", url="https://x.atlassian.net", email="a@b.com", token="t")
        assert info.read_only is True


class TestConnectionStore:
    def test_save_and_load(self, tmp_config_dir: Path, sample_connection: ConnectionInfo) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save(
            sample_connection.connection,
            sample_connection.url,
            sample_connection.email,
            sample_connection.token,
            read_only=sample_connection.read_only,
        )
        loaded = store.load(sample_connection.connection)
        assert loaded.connection == sample_connection.connection
        assert loaded.url == sample_connection.url
        assert loaded.email == sample_connection.email
        assert loaded.token == sample_connection.token
        assert loaded.read_only == sample_connection.read_only

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "new" / "nested" / "dir"
        store = ConnectionStore(config_dir)
        store.save("proj", "https://x.atlassian.net", "a@b.com", "tok")
        assert (config_dir / "proj.toml").exists()

    def test_save_file_permissions(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        path = store.save("proj", "https://x.atlassian.net", "a@b.com", "tok")
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600

    def test_save_read_write(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save("proj", "https://x.atlassian.net", "a@b.com", "tok", read_only=False)
        loaded = store.load("proj")
        assert loaded.read_only is False

    def test_load_not_found(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        with pytest.raises(FileNotFoundError, match="Connection not found: nonexistent"):
            store.load("nonexistent")

    def test_delete(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save("proj", "https://x.atlassian.net", "a@b.com", "tok")
        store.delete("proj")
        with pytest.raises(FileNotFoundError):
            store.load("proj")

    def test_delete_not_found(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        with pytest.raises(FileNotFoundError, match="Connection not found: ghost"):
            store.delete("ghost")

    def test_list_connections_empty(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        assert store.list_connections() == []

    def test_list_connections(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save("alpha", "https://a.atlassian.net", "a@b.com", "t1")
        store.save("beta", "https://b.atlassian.net", "b@b.com", "t2")
        results = store.list_connections()
        assert len(results) == 2
        assert results[0].connection == "alpha"
        assert results[1].connection == "beta"

    def test_list_connections_filter(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save("alpha", "https://a.atlassian.net", "a@b.com", "t1")
        store.save("beta", "https://b.atlassian.net", "b@b.com", "t2")
        results = store.list_connections(connection="alpha")
        assert len(results) == 1
        assert results[0].connection == "alpha"

    def test_list_connections_no_dir(self, tmp_path: Path) -> None:
        store = ConnectionStore(tmp_path / "nonexistent")
        assert store.list_connections() == []

    def test_save_overwrites(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        store.save("proj", "https://old.atlassian.net", "a@b.com", "old-tok")
        store.save("proj", "https://new.atlassian.net", "a@b.com", "new-tok")
        loaded = store.load("proj")
        assert loaded.url == "https://new.atlassian.net"
        assert loaded.token == "new-tok"

    def test_token_with_special_chars(self, tmp_config_dir: Path) -> None:
        store = ConnectionStore(tmp_config_dir)
        token = 'token"with\\special'
        store.save("proj", "https://x.atlassian.net", "a@b.com", token)
        loaded = store.load("proj")
        assert loaded.token == token
