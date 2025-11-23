"""File system search for feature flag references in codebase."""

import os
from dataclasses import dataclass

from ld_audit.config import DEFAULT_EXCLUDE_DIRS, MB_TO_BYTES


@dataclass
class FileLocation:
    """Represents a location in a file."""

    file_path: str
    line_number: int


class CodebaseScanner:
    """Scanner for finding flag references in codebase files."""

    def __init__(self, max_file_size_mb: int = 5, exclude_dirs: set[str] | None = None):
        """
        Initialize codebase scanner.

        Args:
            max_file_size_mb: Maximum file size in MB to scan
            exclude_dirs: Set of directory names to exclude
        """
        self.max_file_size_bytes = max_file_size_mb * MB_TO_BYTES
        self.exclude_dirs = exclude_dirs if exclude_dirs is not None else DEFAULT_EXCLUDE_DIRS

    def search_directory(
        self, directory: str, flag_keys: list[str], extensions: list[str] | None = None
    ) -> dict[str, list[FileLocation]]:
        """
        Search directory recursively for flag keys with exact string matching.

        Args:
            directory: Directory path to search
            flag_keys: List of flag keys to search for
            extensions: Optional list of file extensions to filter by

        Returns:
            Dictionary mapping flag keys to list of FileLocation objects
        """
        results = {key: [] for key in flag_keys}

        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for file in files:
                if not self._should_scan_file(file, extensions):
                    continue

                file_path = os.path.join(root, file)

                if not self._is_file_size_valid(file_path):
                    continue

                file_results = self._search_file(file_path, flag_keys)
                for key, locations in file_results.items():
                    results[key].extend(locations)

        return {k: v for k, v in results.items() if v}

    def _should_scan_file(self, filename: str, extensions: list[str] | None) -> bool:
        """Check if file should be scanned based on extension."""
        if not extensions:
            return True

        return any(filename.endswith(f".{ext}") for ext in extensions)

    def _is_file_size_valid(self, file_path: str) -> bool:
        """Check if file size is within limits."""
        try:
            return os.path.getsize(file_path) <= self.max_file_size_bytes
        except OSError:
            return False

    def _search_file(self, file_path: str, flag_keys: list[str]) -> dict[str, list[FileLocation]]:
        """Search a single file for flag keys."""
        file_results = self._search_file_with_encoding(file_path, flag_keys, "utf-8")

        if not file_results:
            file_results = self._search_file_with_encoding(file_path, flag_keys, "latin-1")

        return file_results

    def _search_file_with_encoding(
        self, file_path: str, flag_keys: list[str], encoding: str
    ) -> dict[str, list[FileLocation]]:
        """
        Search a single file for flag keys with a specific encoding.

        Args:
            file_path: Path to file to search
            flag_keys: List of flag keys to search for
            encoding: Character encoding to use

        Returns:
            Dictionary mapping flag keys to list of FileLocation objects
        """
        results = {key: [] for key in flag_keys}

        try:
            with open(file_path, encoding=encoding) as f:
                for line_num, line in enumerate(f, 1):
                    for flag_key in flag_keys:
                        if f'"{flag_key}"' in line or f"'{flag_key}'" in line:
                            results[flag_key].append(FileLocation(file_path=file_path, line_number=line_num))
        except (UnicodeDecodeError, OSError, PermissionError):
            pass

        return {k: v for k, v in results.items() if v}
