"""Local filesystem implementation of StorageRepository.

Enforces the path pattern:
    {storage_root}/users/{user_id}/sessions/{session_id}/{filename}

per Constitution II: "File storage paths MUST follow the pattern
/users/{user_id}/sessions/{session_id}/…"
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class StorageRepository:
    """Saves user-generated files to the local filesystem.

    All file writes MUST go through this class — direct open() calls
    outside it are a Constitution II violation.
    """

    def __init__(self, storage_root: str) -> None:
        self._root = storage_root

    def save_file(
        self,
        user_id: int,
        session_id: str,
        filename: str,
        data: bytes,
    ) -> str:
        """Save binary data and return the relative file path.

        The returned path follows the mandatory pattern:
            users/{user_id}/sessions/{session_id}/{filename}

        Args:
            user_id: Telegram user ID (owner).
            session_id: Session UUID.
            filename: File name including extension.
            data: Raw binary content.

        Returns:
            Relative path string (relative to storage_root).
        """
        relative_path = os.path.join("users", str(user_id), "sessions", session_id, filename)
        abs_path = os.path.join(self._root, relative_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as fh:
            fh.write(data)
        logger.debug("Saved file: %s", abs_path)
        return relative_path

    def get_abs_path(self, relative_path: str) -> str:
        """Return the absolute path for a relative storage path."""
        return os.path.join(self._root, relative_path)

    def file_exists(self, relative_path: str) -> bool:
        """Return True if the file exists at the given relative path."""
        return os.path.isfile(self.get_abs_path(relative_path))
