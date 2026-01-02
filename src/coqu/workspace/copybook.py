# coqu.workspace.copybook - Copybook resolution and management
"""
Manages copybook search paths and resolution.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import re


@dataclass
class CopybookInfo:
    """Information about a resolved copybook."""
    name: str
    path: Path
    size: int  # File size in bytes
    lines: int  # Line count
    nested_refs: list[str] = field(default_factory=list)  # Nested COPY statements


class CopybookResolver:
    """
    Resolves copybook names to file paths.

    Supports:
    - Multiple search paths
    - Various file extensions
    - Case-insensitive matching
    - Nested copybook detection
    """

    # Common copybook extensions
    EXTENSIONS = [".cpy", ".copy", ".cbl", ".cob", ".CPY", ".COPY", ".CBL", ".COB", ""]

    # Pattern to find COPY statements
    COPY_PATTERN = re.compile(
        r"COPY\s+([A-Z][A-Z0-9-]*)",
        re.IGNORECASE,
    )

    def __init__(self, search_paths: Optional[list[Path]] = None):
        """
        Initialize resolver.

        Args:
            search_paths: Directories to search for copybooks
        """
        self.search_paths: list[Path] = search_paths or []
        self._cache: dict[str, Optional[Path]] = {}

    def add_path(self, path: Path) -> None:
        """Add a search path."""
        if path.is_dir() and path not in self.search_paths:
            self.search_paths.append(path)
            self._cache.clear()  # Invalidate cache

    def remove_path(self, path: Path) -> None:
        """Remove a search path."""
        if path in self.search_paths:
            self.search_paths.remove(path)
            self._cache.clear()

    def clear_paths(self) -> None:
        """Remove all search paths."""
        self.search_paths.clear()
        self._cache.clear()

    def resolve(self, name: str, source_path: Optional[Path] = None) -> Optional[Path]:
        """
        Resolve copybook name to file path.

        Search order:
        1. Same directory as source file (if provided)
        2. Configured search paths (in order)

        Args:
            name: Copybook name
            source_path: Path to source file (for relative resolution)

        Returns:
            Resolved path or None if not found
        """
        # Check cache
        cache_key = f"{name}:{source_path}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Build search order
        paths_to_search: list[Path] = []

        if source_path:
            paths_to_search.append(source_path.parent)

        paths_to_search.extend(self.search_paths)

        # Try each path with each extension
        name_lower = name.lower()
        name_upper = name.upper()

        for search_path in paths_to_search:
            if not search_path.exists():
                continue

            for ext in self.EXTENSIONS:
                # Try lowercase
                candidate = search_path / f"{name_lower}{ext}"
                if candidate.exists():
                    self._cache[cache_key] = candidate
                    return candidate

                # Try uppercase
                candidate = search_path / f"{name_upper}{ext}"
                if candidate.exists():
                    self._cache[cache_key] = candidate
                    return candidate

                # Try original case
                candidate = search_path / f"{name}{ext}"
                if candidate.exists():
                    self._cache[cache_key] = candidate
                    return candidate

        # Not found
        self._cache[cache_key] = None
        return None

    def get_info(self, name: str, source_path: Optional[Path] = None) -> Optional[CopybookInfo]:
        """
        Get detailed information about a copybook.

        Args:
            name: Copybook name
            source_path: Path to source file

        Returns:
            CopybookInfo or None if not found
        """
        resolved = self.resolve(name, source_path)
        if not resolved:
            return None

        try:
            content = resolved.read_text()
            lines = content.count("\n") + 1

            # Find nested COPY statements
            nested = []
            for match in self.COPY_PATTERN.finditer(content):
                nested_name = match.group(1).upper()
                if nested_name not in nested:
                    nested.append(nested_name)

            return CopybookInfo(
                name=name.upper(),
                path=resolved,
                size=resolved.stat().st_size,
                lines=lines,
                nested_refs=nested,
            )
        except Exception:
            return None

    def find_all_in_directory(self, directory: Path) -> list[CopybookInfo]:
        """
        Find all copybooks in a directory.

        Args:
            directory: Directory to scan

        Returns:
            List of CopybookInfo for found copybooks
        """
        results = []

        if not directory.exists():
            return results

        for ext in self.EXTENSIONS:
            if not ext:
                continue
            for path in directory.glob(f"*{ext}"):
                if path.is_file():
                    name = path.stem.upper()
                    info = self.get_info(name, path)
                    if info:
                        results.append(info)

        return results

    def get_dependency_tree(
        self,
        name: str,
        source_path: Optional[Path] = None,
        visited: Optional[set] = None,
    ) -> dict:
        """
        Build dependency tree for a copybook.

        Args:
            name: Copybook name
            source_path: Path to source file
            visited: Set of visited copybooks (for cycle detection)

        Returns:
            Dictionary with copybook info and nested dependencies
        """
        if visited is None:
            visited = set()

        name_upper = name.upper()

        # Check for circular reference
        if name_upper in visited:
            return {"name": name_upper, "circular": True}

        visited.add(name_upper)

        info = self.get_info(name, source_path)
        if not info:
            return {"name": name_upper, "resolved": False}

        # Build nested tree
        nested = []
        for nested_name in info.nested_refs:
            nested_tree = self.get_dependency_tree(
                nested_name, info.path, visited.copy()
            )
            nested.append(nested_tree)

        return {
            "name": name_upper,
            "resolved": True,
            "path": str(info.path),
            "lines": info.lines,
            "nested": nested,
        }
