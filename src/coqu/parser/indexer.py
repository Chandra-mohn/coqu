# coqu.parser.indexer - Lightweight structural indexer
"""
Fast regex-based structural indexer for large COBOL files.
This provides quick navigation without full ANTLR parsing.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IndexEntry:
    """Entry in the structural index."""
    name: str
    type: str  # division, section, paragraph, copybook
    line_start: int
    line_end: int = 0  # Set during post-processing

    def __str__(self) -> str:
        return f"{self.type}: {self.name} (lines {self.line_start}-{self.line_end})"


@dataclass
class StructuralIndex:
    """Fast structural index of a COBOL program."""
    divisions: list[IndexEntry] = field(default_factory=list)
    sections: list[IndexEntry] = field(default_factory=list)
    paragraphs: list[IndexEntry] = field(default_factory=list)
    copybooks: list[IndexEntry] = field(default_factory=list)
    data_items_01: list[IndexEntry] = field(default_factory=list)
    total_lines: int = 0

    def get_division_names(self) -> list[str]:
        """Get list of division names."""
        return [d.name for d in self.divisions]

    def get_paragraph_names(self) -> list[str]:
        """Get list of paragraph names."""
        return [p.name for p in self.paragraphs]

    def get_section_names(self) -> list[str]:
        """Get list of section names."""
        return [s.name for s in self.sections]

    def get_entry(self, name: str, entry_type: str) -> Optional[IndexEntry]:
        """Get entry by name and type."""
        name_upper = name.upper()
        entries = {
            "division": self.divisions,
            "section": self.sections,
            "paragraph": self.paragraphs,
            "copybook": self.copybooks,
            "data_item": self.data_items_01,
        }.get(entry_type, [])

        for entry in entries:
            if entry.name.upper() == name_upper:
                return entry
        return None


class StructuralIndexer:
    """
    Fast regex-based indexer for COBOL structure.
    Designed for 2M+ line files where full parsing is slow.
    """

    # Regex patterns for COBOL structure
    # COBOL is column-sensitive: positions 1-6 are sequence, 7 is indicator,
    # 8-11 is Area A (divisions, sections, paragraph names), 12-72 is Area B

    # Division pattern: "IDENTIFICATION DIVISION" or "ID DIVISION", etc.
    DIVISION_PATTERN = re.compile(
        r"^\s{0,6}[\s\d]{0,6}\s*(IDENTIFICATION|ID|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION",
        re.IGNORECASE | re.MULTILINE,
    )

    # Section pattern: "WORKING-STORAGE SECTION", "INPUT-OUTPUT SECTION", etc.
    # Sections can appear with variable indentation depending on the division
    SECTION_PATTERN = re.compile(
        r"^\s{6,8}([A-Z0-9][A-Z0-9-]*)\s+SECTION\s*\.",
        re.IGNORECASE | re.MULTILINE,
    )

    # Paragraph pattern: paragraph name at start of line followed by period
    # COBOL paragraphs start in Area A (columns 8-11), which means they have
    # 6-8 leading spaces. They end with just a period on that line.
    PARAGRAPH_PATTERN = re.compile(
        r"^\s{6,8}([A-Z0-9][A-Z0-9-]*)\s*\.\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    # COPY statement
    COPY_PATTERN = re.compile(
        r"^\s{0,6}[\s\d]{0,6}\s*COPY\s+([A-Z][A-Z0-9-]*)",
        re.IGNORECASE | re.MULTILINE,
    )

    # Level 01 data items
    LEVEL_01_PATTERN = re.compile(
        r"^\s{0,6}[\s\d]{0,6}\s*01\s+([A-Z][A-Z0-9-]*)",
        re.IGNORECASE | re.MULTILINE,
    )

    def index(self, source: str) -> StructuralIndex:
        """
        Create structural index from COBOL source.

        Args:
            source: COBOL source code as string

        Returns:
            StructuralIndex with divisions, sections, paragraphs, etc.
        """
        index = StructuralIndex()
        lines = source.split("\n")
        index.total_lines = len(lines)

        # Track current context for determining paragraph scope
        current_division: Optional[str] = None
        in_procedure_division = False

        # Index divisions
        for match in self.DIVISION_PATTERN.finditer(source):
            line_num = source[:match.start()].count("\n") + 1
            div_name = match.group(1).upper()
            index.divisions.append(IndexEntry(
                name=f"{div_name} DIVISION",
                type="division",
                line_start=line_num,
            ))
            if div_name == "PROCEDURE":
                in_procedure_division = True

        # Index sections
        for match in self.SECTION_PATTERN.finditer(source):
            line_num = source[:match.start()].count("\n") + 1
            section_name = match.group(1).upper()
            index.sections.append(IndexEntry(
                name=f"{section_name} SECTION",
                type="section",
                line_start=line_num,
            ))

        # Index paragraphs (only in PROCEDURE DIVISION)
        # Find where PROCEDURE DIVISION starts
        proc_div_start = 0
        for div in index.divisions:
            if "PROCEDURE" in div.name:
                proc_div_start = div.line_start
                break

        if proc_div_start > 0:
            # Only look for paragraphs after PROCEDURE DIVISION
            proc_source = "\n".join(lines[proc_div_start - 1:])
            for match in self.PARAGRAPH_PATTERN.finditer(proc_source):
                line_num = proc_div_start + proc_source[:match.start()].count("\n")
                para_name = match.group(1).upper()

                # Skip if it looks like a section (followed by SECTION keyword)
                if "SECTION" in para_name:
                    continue

                # Skip common false positives
                if para_name in ("DIVISION", "SECTION", "END", "EXIT"):
                    continue

                index.paragraphs.append(IndexEntry(
                    name=para_name,
                    type="paragraph",
                    line_start=line_num,
                ))

        # Index COPY statements
        for match in self.COPY_PATTERN.finditer(source):
            line_num = source[:match.start()].count("\n") + 1
            copybook_name = match.group(1).upper()
            index.copybooks.append(IndexEntry(
                name=copybook_name,
                type="copybook",
                line_start=line_num,
            ))

        # Index level-01 data items
        for match in self.LEVEL_01_PATTERN.finditer(source):
            line_num = source[:match.start()].count("\n") + 1
            item_name = match.group(1).upper()
            index.data_items_01.append(IndexEntry(
                name=item_name,
                type="data_item",
                line_start=line_num,
            ))

        # Post-process: calculate line_end for each entry
        self._calculate_line_ends(index)

        return index

    def _calculate_line_ends(self, index: StructuralIndex) -> None:
        """Calculate line_end for each entry based on next entry start."""
        total = index.total_lines

        # Sort divisions by line and calculate ends
        if index.divisions:
            sorted_divs = sorted(index.divisions, key=lambda x: x.line_start)
            for i, div in enumerate(sorted_divs):
                if i + 1 < len(sorted_divs):
                    div.line_end = sorted_divs[i + 1].line_start - 1
                else:
                    div.line_end = total

        # Sort sections by line and calculate ends
        if index.sections:
            sorted_secs = sorted(index.sections, key=lambda x: x.line_start)
            for i, sec in enumerate(sorted_secs):
                if i + 1 < len(sorted_secs):
                    sec.line_end = sorted_secs[i + 1].line_start - 1
                else:
                    # Find the end of containing division
                    for div in index.divisions:
                        if div.line_start <= sec.line_start <= div.line_end:
                            sec.line_end = div.line_end
                            break
                    else:
                        sec.line_end = total

        # Sort paragraphs by line and calculate ends
        if index.paragraphs:
            sorted_paras = sorted(index.paragraphs, key=lambda x: x.line_start)
            for i, para in enumerate(sorted_paras):
                if i + 1 < len(sorted_paras):
                    para.line_end = sorted_paras[i + 1].line_start - 1
                else:
                    # Find the end of PROCEDURE DIVISION
                    for div in index.divisions:
                        if "PROCEDURE" in div.name:
                            para.line_end = div.line_end
                            break
                    else:
                        para.line_end = total

        # Copybooks and data items are single-line entries for now
        for entry in index.copybooks:
            entry.line_end = entry.line_start

        for entry in index.data_items_01:
            entry.line_end = entry.line_start


def index_source(source: str) -> StructuralIndex:
    """Convenience function to index COBOL source."""
    indexer = StructuralIndexer()
    return indexer.index(source)
