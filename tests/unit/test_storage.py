"""Unit tests for StorageRepository — T020."""
from __future__ import annotations

import os
import tempfile

import pytest

from glucotrack.storage.local_storage import StorageRepository


class TestStorageRepository:
    """Tests for local filesystem StorageRepository."""

    def test_save_file_returns_correct_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = StorageRepository(tmpdir)
            path = repo.save_file(
                user_id=123,
                session_id="sess-abc",
                filename="food_001.jpg",
                data=b"fake_image",
            )
            assert path == os.path.join("users", "123", "sessions", "sess-abc", "food_001.jpg")

    def test_save_file_writes_data_to_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = StorageRepository(tmpdir)
            data = b"image_bytes_here"
            path = repo.save_file(123, "sess-abc", "food_001.jpg", data)
            abs_path = os.path.join(tmpdir, path)
            assert os.path.isfile(abs_path)
            with open(abs_path, "rb") as fh:
                assert fh.read() == data

    def test_path_is_isolated_per_user_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = StorageRepository(tmpdir)
            path_a = repo.save_file(111, "sess-1", "food.jpg", b"a")
            path_b = repo.save_file(222, "sess-1", "food.jpg", b"b")
            assert "111" in path_a
            assert "222" in path_b
            assert path_a != path_b

    def test_path_is_isolated_per_session_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = StorageRepository(tmpdir)
            path_1 = repo.save_file(123, "sess-001", "food.jpg", b"x")
            path_2 = repo.save_file(123, "sess-002", "food.jpg", b"y")
            assert "sess-001" in path_1
            assert "sess-002" in path_2
            assert path_1 != path_2

    def test_path_follows_constitution_ii_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = StorageRepository(tmpdir)
            path = repo.save_file(42, "session-xyz", "cgm_001.jpg", b"data")
            # Must follow: users/{user_id}/sessions/{session_id}/{filename}
            parts = path.replace("\\", "/").split("/")
            assert parts[0] == "users"
            assert parts[1] == "42"
            assert parts[2] == "sessions"
            assert parts[3] == "session-xyz"
            assert parts[4] == "cgm_001.jpg"

    def test_file_exists_returns_true_after_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = StorageRepository(tmpdir)
            path = repo.save_file(1, "s1", "test.jpg", b"data")
            assert repo.file_exists(path) is True

    def test_file_exists_returns_false_for_unknown_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = StorageRepository(tmpdir)
            assert repo.file_exists("users/999/sessions/x/missing.jpg") is False

    def test_get_abs_path_includes_storage_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = StorageRepository(tmpdir)
            abs_path = repo.get_abs_path("users/1/sessions/s/f.jpg")
            assert abs_path.startswith(tmpdir)
