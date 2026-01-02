# coqu.workspace.workspace - Main workspace management
"""
Manages multiple loaded COBOL programs and copybook resolution.
"""
from pathlib import Path
from typing import Optional, Iterator
import time

from coqu.parser.cobol_parser import CobolParser
from coqu.parser.ast import CobolProgram
from coqu.workspace.program import LoadedProgram
from coqu.workspace.copybook import CopybookResolver


class Workspace:
    """
    Manages a collection of loaded COBOL programs.

    Features:
    - Load/unload programs
    - Copybook path management
    - Cache integration
    - Batch operations
    """

    def __init__(
        self,
        copybook_paths: Optional[list[Path]] = None,
        cache_manager=None,
        use_indexer_only: bool = False,
    ):
        """
        Initialize workspace.

        Args:
            copybook_paths: Paths to search for copybooks
            cache_manager: Optional cache manager for AST caching
            use_indexer_only: Use fast indexer instead of full ANTLR parse
        """
        self.programs: dict[str, LoadedProgram] = {}
        self.copybook_resolver = CopybookResolver(copybook_paths)
        self.cache_manager = cache_manager
        self.use_indexer_only = use_indexer_only

        # Create parser with copybook paths
        self._parser = CobolParser(
            copybook_paths=copybook_paths,
            use_indexer_only=use_indexer_only,
        )

    @property
    def copybook_paths(self) -> list[Path]:
        """Get copybook search paths."""
        return self.copybook_resolver.search_paths

    def add_copybook_path(self, path: Path) -> None:
        """Add a copybook search path."""
        self.copybook_resolver.add_path(path)
        self._parser.add_copybook_path(path)

    def load(self, path: Path, force_reparse: bool = False) -> LoadedProgram:
        """
        Load a COBOL program into the workspace.

        Args:
            path: Path to COBOL source file
            force_reparse: Force parsing even if cached

        Returns:
            LoadedProgram instance
        """
        path = path.resolve()
        name = path.stem.upper()

        # Check if already loaded
        if name in self.programs and not force_reparse:
            existing = self.programs[name]
            if existing.path == path:
                return existing

        # Read source for hash calculation
        source = path.read_text()
        import hashlib
        source_hash = hashlib.sha256(source.encode()).hexdigest()

        # Try cache first
        program: Optional[CobolProgram] = None
        from_cache = False

        if self.cache_manager and not force_reparse:
            program = self.cache_manager.get(source_hash)
            if program:
                from_cache = True

        # Parse if not cached
        parse_time_ms = 0.0
        if not program:
            start = time.perf_counter()
            program = self._parser.parse_file(path)
            parse_time_ms = (time.perf_counter() - start) * 1000

            # Cache the result
            if self.cache_manager:
                self.cache_manager.put(source_hash, program)

        # Create loaded program
        loaded = LoadedProgram(
            name=name,
            path=path,
            program=program,
            from_cache=from_cache,
            parse_time_ms=parse_time_ms,
        )

        self.programs[name] = loaded
        return loaded

    def load_directory(
        self,
        directory: Path,
        pattern: str = "*.cbl",
        recursive: bool = False,
    ) -> list[LoadedProgram]:
        """
        Load all COBOL files in a directory.

        Args:
            directory: Directory to scan
            pattern: Glob pattern for files
            recursive: Search subdirectories

        Returns:
            List of loaded programs
        """
        loaded = []

        if recursive:
            files = directory.rglob(pattern)
        else:
            files = directory.glob(pattern)

        for path in files:
            if path.is_file():
                try:
                    prog = self.load(path)
                    loaded.append(prog)
                except Exception:
                    pass  # Skip files that fail to parse

        return loaded

    def unload(self, name: str) -> bool:
        """
        Unload a program from the workspace.

        Args:
            name: Program name (filename stem)

        Returns:
            True if program was unloaded
        """
        name_upper = name.upper()
        if name_upper in self.programs:
            del self.programs[name_upper]
            return True
        return False

    def unload_all(self) -> int:
        """
        Unload all programs.

        Returns:
            Number of programs unloaded
        """
        count = len(self.programs)
        self.programs.clear()
        return count

    def reload(self, name: str) -> Optional[LoadedProgram]:
        """
        Reload a program (reparse from source).

        Args:
            name: Program name

        Returns:
            Reloaded program or None if not found
        """
        name_upper = name.upper()
        if name_upper not in self.programs:
            return None

        path = self.programs[name_upper].path
        return self.load(path, force_reparse=True)

    def reload_all(self) -> list[LoadedProgram]:
        """
        Reload all programs.

        Returns:
            List of reloaded programs
        """
        paths = [prog.path for prog in self.programs.values()]
        self.programs.clear()

        reloaded = []
        for path in paths:
            try:
                prog = self.load(path, force_reparse=True)
                reloaded.append(prog)
            except Exception:
                pass

        return reloaded

    def get(self, name: str) -> Optional[LoadedProgram]:
        """
        Get a loaded program by name.

        Args:
            name: Program name

        Returns:
            LoadedProgram or None
        """
        return self.programs.get(name.upper())

    def __getitem__(self, name: str) -> LoadedProgram:
        """Get program by name (raises KeyError if not found)."""
        prog = self.get(name)
        if prog is None:
            raise KeyError(f"Program '{name}' not loaded")
        return prog

    def __contains__(self, name: str) -> bool:
        """Check if program is loaded."""
        return name.upper() in self.programs

    def __iter__(self) -> Iterator[LoadedProgram]:
        """Iterate over loaded programs."""
        return iter(self.programs.values())

    def __len__(self) -> int:
        """Get number of loaded programs."""
        return len(self.programs)

    def list_programs(self) -> list[str]:
        """Get list of loaded program names."""
        return list(self.programs.keys())

    def get_stats(self) -> dict:
        """
        Get workspace statistics.

        Returns:
            Dictionary with stats
        """
        total_lines = sum(p.lines for p in self.programs.values())
        cached_count = sum(1 for p in self.programs.values() if p.from_cache)

        return {
            "program_count": len(self.programs),
            "total_lines": total_lines,
            "cached_count": cached_count,
            "copybook_paths": len(self.copybook_paths),
        }

    def find_program_by_id(self, program_id: str) -> Optional[LoadedProgram]:
        """
        Find program by PROGRAM-ID.

        Args:
            program_id: The PROGRAM-ID to search for

        Returns:
            LoadedProgram or None
        """
        program_id_upper = program_id.upper()
        for prog in self.programs.values():
            if prog.program_id.upper() == program_id_upper:
                return prog
        return None

    def find_callers(self, program_id: str) -> list[tuple[str, str]]:
        """
        Find all programs that CALL a given program.

        Args:
            program_id: Target program ID

        Returns:
            List of (program_name, paragraph_name) tuples
        """
        callers = []
        target = program_id.upper()

        for prog in self.programs.values():
            for para in prog.get_all_paragraphs():
                if target in [c.upper() for c in para.calls]:
                    callers.append((prog.name, para.name))

        return callers

    def get_call_graph(self) -> dict[str, list[str]]:
        """
        Build call graph for all loaded programs.

        Returns:
            Dictionary mapping program IDs to called program IDs
        """
        graph = {}

        for prog in self.programs.values():
            calls = set()
            for para in prog.get_all_paragraphs():
                calls.update(c.upper() for c in para.calls)

            graph[prog.program_id] = sorted(calls)

        return graph
