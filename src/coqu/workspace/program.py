# coqu.workspace.program - Loaded program representation
"""
Represents a loaded COBOL program in the workspace.
Wraps the parsed AST with workspace-specific metadata.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import time

from coqu.parser.ast import CobolProgram


@dataclass
class LoadedProgram:
    """
    A COBOL program loaded into the workspace.

    Tracks loading metadata and provides convenience accessors.
    """
    name: str  # Program identifier (filename without extension)
    path: Path  # Full path to source file
    program: CobolProgram  # Parsed AST
    loaded_at: float = field(default_factory=time.time)  # Timestamp
    from_cache: bool = False  # Whether loaded from cache
    parse_time_ms: float = 0.0  # Time to parse (if not from cache)

    @property
    def program_id(self) -> str:
        """Get PROGRAM-ID from AST."""
        return self.program.program_id

    @property
    def source_hash(self) -> str:
        """Get source hash for cache validation."""
        return self.program.source_hash

    @property
    def lines(self) -> int:
        """Get line count."""
        return self.program.lines

    @property
    def divisions(self) -> list:
        """Get all divisions."""
        return self.program.divisions

    @property
    def copybook_refs(self) -> list:
        """Get copybook references."""
        return self.program.copybook_refs

    def get_division(self, name: str):
        """Get division by name."""
        return self.program.get_division(name)

    def get_paragraph(self, name: str):
        """Get paragraph by name."""
        return self.program.get_paragraph(name)

    def get_all_paragraphs(self) -> list:
        """Get all paragraphs."""
        return self.program.get_all_paragraphs()

    def get_working_storage_items(self, level: Optional[int] = None) -> list:
        """Get WORKING-STORAGE data items."""
        return self.program.get_working_storage_items(level)

    def get_body(self, location) -> str:
        """Get source body for a location."""
        return self.program.get_body(location)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "path": str(self.path),
            "program": self.program.to_dict(),
            "loaded_at": self.loaded_at,
            "from_cache": self.from_cache,
            "parse_time_ms": self.parse_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LoadedProgram":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            path=Path(data["path"]),
            program=CobolProgram.from_dict(data["program"]),
            loaded_at=data.get("loaded_at", time.time()),
            from_cache=data.get("from_cache", False),
            parse_time_ms=data.get("parse_time_ms", 0.0),
        )

    def __str__(self) -> str:
        cache_str = " (cached)" if self.from_cache else ""
        return f"{self.name}: {self.program_id} ({self.lines} lines){cache_str}"
