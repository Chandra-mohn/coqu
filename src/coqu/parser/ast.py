# coqu.parser.ast - AST node definitions
"""
AST node definitions for COBOL programs.
All nodes are dataclasses for easy serialization with MessagePack.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SourceLocation:
    """Source code location information."""
    line_start: int
    line_end: int
    col_start: int = 0
    col_end: int = 0

    def __str__(self) -> str:
        if self.line_start == self.line_end:
            return f"line {self.line_start}"
        return f"lines {self.line_start}-{self.line_end}"


@dataclass
class CopybookRef:
    """Reference to a COPY statement."""
    name: str
    line: int
    resolved_path: Optional[Path] = None
    replacing: Optional[str] = None
    status: str = "unresolved"  # resolved, unresolved, error

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "line": self.line,
            "resolved_path": str(self.resolved_path) if self.resolved_path else None,
            "replacing": self.replacing,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CopybookRef":
        return cls(
            name=data["name"],
            line=data["line"],
            resolved_path=Path(data["resolved_path"]) if data.get("resolved_path") else None,
            replacing=data.get("replacing"),
            status=data.get("status", "unresolved"),
        )


@dataclass
class DataItem:
    """COBOL data item (variable) definition."""
    name: str
    level: int
    location: SourceLocation
    pic: Optional[str] = None
    usage: Optional[str] = None
    value: Optional[str] = None
    occurs: Optional[int] = None
    redefines: Optional[str] = None
    children: list["DataItem"] = field(default_factory=list)
    body: Optional[str] = None  # Full source text, lazy loaded

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "level": self.level,
            "line_start": self.location.line_start,
            "line_end": self.location.line_end,
            "pic": self.pic,
            "usage": self.usage,
            "value": self.value,
            "occurs": self.occurs,
            "redefines": self.redefines,
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DataItem":
        return cls(
            name=data["name"],
            level=data["level"],
            location=SourceLocation(
                line_start=data["line_start"],
                line_end=data["line_end"],
            ),
            pic=data.get("pic"),
            usage=data.get("usage"),
            value=data.get("value"),
            occurs=data.get("occurs"),
            redefines=data.get("redefines"),
            children=[cls.from_dict(c) for c in data.get("children", [])],
        )


@dataclass
class Statement:
    """COBOL statement (MOVE, CALL, PERFORM, etc.)."""
    type: str  # move, call, perform, if, evaluate, etc.
    location: SourceLocation
    target: Optional[str] = None  # For CALL/PERFORM: target name
    arguments: list[str] = field(default_factory=list)
    body: Optional[str] = None  # Full source text

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "line_start": self.location.line_start,
            "line_end": self.location.line_end,
            "target": self.target,
            "arguments": self.arguments,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Statement":
        return cls(
            type=data["type"],
            location=SourceLocation(
                line_start=data["line_start"],
                line_end=data["line_end"],
            ),
            target=data.get("target"),
            arguments=data.get("arguments", []),
        )


@dataclass
class Paragraph:
    """COBOL paragraph in PROCEDURE DIVISION."""
    name: str
    location: SourceLocation
    statements: list[Statement] = field(default_factory=list)
    body: Optional[str] = None  # Full source text, lazy loaded
    performs: list[str] = field(default_factory=list)  # Paragraphs called via PERFORM
    calls: list[str] = field(default_factory=list)  # Programs called via CALL

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "line_start": self.location.line_start,
            "line_end": self.location.line_end,
            "statements": [s.to_dict() for s in self.statements],
            "performs": self.performs,
            "calls": self.calls,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Paragraph":
        return cls(
            name=data["name"],
            location=SourceLocation(
                line_start=data["line_start"],
                line_end=data["line_end"],
            ),
            statements=[Statement.from_dict(s) for s in data.get("statements", [])],
            performs=data.get("performs", []),
            calls=data.get("calls", []),
        )


@dataclass
class Section:
    """COBOL section (in any division)."""
    name: str
    location: SourceLocation
    paragraphs: list[Paragraph] = field(default_factory=list)
    data_items: list[DataItem] = field(default_factory=list)
    body: Optional[str] = None  # Full source text, lazy loaded

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "line_start": self.location.line_start,
            "line_end": self.location.line_end,
            "paragraphs": [p.to_dict() for p in self.paragraphs],
            "data_items": [d.to_dict() for d in self.data_items],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Section":
        return cls(
            name=data["name"],
            location=SourceLocation(
                line_start=data["line_start"],
                line_end=data["line_end"],
            ),
            paragraphs=[Paragraph.from_dict(p) for p in data.get("paragraphs", [])],
            data_items=[DataItem.from_dict(d) for d in data.get("data_items", [])],
        )


@dataclass
class Division:
    """COBOL division (IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE)."""
    name: str  # IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE
    location: SourceLocation
    sections: list[Section] = field(default_factory=list)
    paragraphs: list[Paragraph] = field(default_factory=list)  # For PROCEDURE DIVISION
    body: Optional[str] = None  # Full source text, lazy loaded

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "line_start": self.location.line_start,
            "line_end": self.location.line_end,
            "sections": [s.to_dict() for s in self.sections],
            "paragraphs": [p.to_dict() for p in self.paragraphs],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Division":
        return cls(
            name=data["name"],
            location=SourceLocation(
                line_start=data["line_start"],
                line_end=data["line_end"],
            ),
            sections=[Section.from_dict(s) for s in data.get("sections", [])],
            paragraphs=[Paragraph.from_dict(p) for p in data.get("paragraphs", [])],
        )


@dataclass
class Comment:
    """COBOL comment line."""
    text: str
    line: int
    is_inline: bool = False  # True for *> comments

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "line": self.line,
            "is_inline": self.is_inline,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Comment":
        return cls(
            text=data["text"],
            line=data["line"],
            is_inline=data.get("is_inline", False),
        )


@dataclass
class CobolProgram:
    """Complete COBOL program AST."""
    program_id: str
    source_path: Optional[Path]
    source_hash: str
    lines: int
    divisions: list[Division] = field(default_factory=list)
    copybook_refs: list[CopybookRef] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    source_lines: Optional[list[str]] = None  # Original source, for --body queries

    def get_division(self, name: str) -> Optional[Division]:
        """Get division by name (partial match supported)."""
        name_upper = name.upper()
        for div in self.divisions:
            # Exact match or partial match (e.g., "PROCEDURE" matches "PROCEDURE DIVISION")
            if div.name.upper() == name_upper or name_upper in div.name.upper():
                return div
        return None

    def get_all_sections(self) -> list[Section]:
        """Get all sections from all divisions."""
        sections: list[Section] = []
        for div in self.divisions:
            sections.extend(div.sections)
        return sections

    def get_procedure_sections(self) -> list[Section]:
        """Get sections from PROCEDURE DIVISION only."""
        proc_div = self.get_division("PROCEDURE")
        if not proc_div:
            return []
        return list(proc_div.sections)

    def get_all_paragraphs(self) -> list[Paragraph]:
        """Get all paragraphs from PROCEDURE DIVISION."""
        proc_div = self.get_division("PROCEDURE")
        if not proc_div:
            return []

        paragraphs = list(proc_div.paragraphs)
        for section in proc_div.sections:
            paragraphs.extend(section.paragraphs)
        return paragraphs

    def get_paragraph(self, name: str) -> Optional[Paragraph]:
        """Get paragraph by name."""
        name_upper = name.upper()
        for para in self.get_all_paragraphs():
            if para.name.upper() == name_upper:
                return para
        return None

    def get_working_storage_items(self, level: Optional[int] = None) -> list[DataItem]:
        """Get WORKING-STORAGE data items."""
        data_div = self.get_division("DATA")
        if not data_div:
            return []

        items: list[DataItem] = []
        for section in data_div.sections:
            if "WORKING-STORAGE" in section.name.upper():
                if level is not None:
                    items.extend([d for d in section.data_items if d.level == level])
                else:
                    items.extend(section.data_items)
        return items

    def get_body(self, location: SourceLocation) -> str:
        """Extract source body for a location."""
        if not self.source_lines:
            return ""
        start = location.line_start - 1
        end = location.line_end
        return "\n".join(self.source_lines[start:end])

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "program_id": self.program_id,
            "source_path": str(self.source_path) if self.source_path else None,
            "source_hash": self.source_hash,
            "lines": self.lines,
            "divisions": [d.to_dict() for d in self.divisions],
            "copybook_refs": [c.to_dict() for c in self.copybook_refs],
            "comments": [c.to_dict() for c in self.comments],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CobolProgram":
        """Create from dictionary."""
        return cls(
            program_id=data["program_id"],
            source_path=Path(data["source_path"]) if data.get("source_path") else None,
            source_hash=data["source_hash"],
            lines=data["lines"],
            divisions=[Division.from_dict(d) for d in data.get("divisions", [])],
            copybook_refs=[CopybookRef.from_dict(c) for c in data.get("copybook_refs", [])],
            comments=[Comment.from_dict(c) for c in data.get("comments", [])],
        )
