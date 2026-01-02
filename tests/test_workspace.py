# tests/test_workspace.py - Workspace tests
"""
Tests for the workspace module.
"""
import pytest
from pathlib import Path
import tempfile

from coqu.workspace import Workspace, LoadedProgram, CopybookResolver
from coqu.cache import CacheManager


# Fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_CBL = FIXTURES_DIR / "sample.cbl"
CALLER_CBL = FIXTURES_DIR / "caller.cbl"


class TestWorkspace:
    """Tests for the Workspace class."""

    def test_load_program(self):
        """Test loading a single program."""
        workspace = Workspace(use_indexer_only=True)
        prog = workspace.load(SAMPLE_CBL)

        assert prog.name == "SAMPLE"
        assert prog.program_id == "SAMPLE"
        assert prog.lines > 0

    def test_load_multiple_programs(self):
        """Test loading multiple programs."""
        workspace = Workspace(use_indexer_only=True)
        workspace.load(SAMPLE_CBL)
        workspace.load(CALLER_CBL)

        assert len(workspace) == 2
        assert "SAMPLE" in workspace
        assert "CALLER" in workspace

    def test_get_program(self):
        """Test getting a loaded program."""
        workspace = Workspace(use_indexer_only=True)
        workspace.load(SAMPLE_CBL)

        prog = workspace.get("SAMPLE")
        assert prog is not None
        assert prog.program_id == "SAMPLE"

        prog = workspace.get("NONEXISTENT")
        assert prog is None

    def test_unload_program(self):
        """Test unloading a program."""
        workspace = Workspace(use_indexer_only=True)
        workspace.load(SAMPLE_CBL)

        assert "SAMPLE" in workspace
        workspace.unload("SAMPLE")
        assert "SAMPLE" not in workspace

    def test_reload_program(self):
        """Test reloading a program."""
        workspace = Workspace(use_indexer_only=True)
        workspace.load(SAMPLE_CBL)

        prog = workspace.reload("SAMPLE")
        assert prog is not None
        assert not prog.from_cache

    def test_load_directory(self):
        """Test loading all files in a directory."""
        workspace = Workspace(use_indexer_only=True)
        programs = workspace.load_directory(FIXTURES_DIR, "*.cbl")

        assert len(programs) >= 2
        assert "SAMPLE" in workspace
        assert "CALLER" in workspace

    def test_list_programs(self):
        """Test listing program names."""
        workspace = Workspace(use_indexer_only=True)
        workspace.load(SAMPLE_CBL)
        workspace.load(CALLER_CBL)

        names = workspace.list_programs()
        assert "SAMPLE" in names
        assert "CALLER" in names

    def test_get_stats(self):
        """Test getting workspace stats."""
        workspace = Workspace(use_indexer_only=True)
        workspace.load(SAMPLE_CBL)
        workspace.load(CALLER_CBL)

        stats = workspace.get_stats()
        assert stats["program_count"] == 2
        assert stats["total_lines"] > 0

    def test_iteration(self):
        """Test iterating over programs."""
        workspace = Workspace(use_indexer_only=True)
        workspace.load(SAMPLE_CBL)
        workspace.load(CALLER_CBL)

        programs = list(workspace)
        assert len(programs) == 2

    def test_with_copybook_paths(self):
        """Test workspace with copybook paths."""
        workspace = Workspace(
            copybook_paths=[FIXTURES_DIR],
            use_indexer_only=True,
        )
        prog = workspace.load(SAMPLE_CBL)

        # Check copybook was resolved
        dateutil_ref = next(
            (r for r in prog.copybook_refs if r.name == "DATEUTIL"),
            None,
        )
        assert dateutil_ref is not None


class TestCopybookResolver:
    """Tests for the CopybookResolver class."""

    def test_resolve_copybook(self):
        """Test resolving a copybook."""
        resolver = CopybookResolver([FIXTURES_DIR])
        path = resolver.resolve("DATEUTIL")

        assert path is not None
        assert path.exists()

    def test_resolve_case_insensitive(self):
        """Test case-insensitive resolution."""
        resolver = CopybookResolver([FIXTURES_DIR])

        path1 = resolver.resolve("DATEUTIL")
        path2 = resolver.resolve("dateutil")

        # Both should resolve to the same file
        assert path1 is not None
        assert path2 is not None

    def test_get_info(self):
        """Test getting copybook info."""
        resolver = CopybookResolver([FIXTURES_DIR])
        info = resolver.get_info("DATEUTIL")

        assert info is not None
        assert info.name == "DATEUTIL"
        assert info.lines > 0

    def test_add_remove_path(self):
        """Test adding and removing paths."""
        resolver = CopybookResolver()

        resolver.add_path(FIXTURES_DIR)
        assert FIXTURES_DIR in resolver.search_paths

        resolver.remove_path(FIXTURES_DIR)
        assert FIXTURES_DIR not in resolver.search_paths


class TestCacheManager:
    """Tests for the CacheManager class."""

    def test_put_get(self):
        """Test storing and retrieving from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(Path(tmpdir))

            # Parse a program
            from coqu.parser import CobolParser
            parser = CobolParser(use_indexer_only=True)
            program = parser.parse_file(SAMPLE_CBL)

            # Cache it
            cache.put(program.source_hash, program)

            # Retrieve it
            cached = cache.get(program.source_hash)
            assert cached is not None
            assert cached.program_id == program.program_id

    def test_cache_miss(self):
        """Test cache miss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(Path(tmpdir))
            result = cache.get("nonexistent_hash")
            assert result is None

    def test_clear_cache(self):
        """Test clearing the cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(Path(tmpdir))

            # Add something
            from coqu.parser import CobolParser
            parser = CobolParser(use_indexer_only=True)
            program = parser.parse_file(SAMPLE_CBL)
            cache.put(program.source_hash, program)

            # Clear
            count = cache.clear()
            assert count == 1

            # Verify empty
            assert cache.get(program.source_hash) is None

    def test_cache_stats(self):
        """Test cache statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(Path(tmpdir))

            # Miss
            cache.get("nonexistent")

            stats = cache.get_stats()
            assert stats["misses"] == 1
            assert stats["hits"] == 0


class TestLoadedProgram:
    """Tests for the LoadedProgram class."""

    def test_properties(self):
        """Test LoadedProgram properties."""
        workspace = Workspace(use_indexer_only=True)
        prog = workspace.load(SAMPLE_CBL)

        assert prog.name == "SAMPLE"
        assert prog.program_id == "SAMPLE"
        assert prog.lines > 0
        assert len(prog.divisions) > 0

    def test_get_division(self):
        """Test getting division through LoadedProgram."""
        workspace = Workspace(use_indexer_only=True)
        prog = workspace.load(SAMPLE_CBL)

        div = prog.get_division("PROCEDURE")
        assert div is not None

    def test_get_paragraph(self):
        """Test getting paragraph through LoadedProgram."""
        workspace = Workspace(use_indexer_only=True)
        prog = workspace.load(SAMPLE_CBL)

        para = prog.get_paragraph("2100-VALIDATE")
        assert para is not None
