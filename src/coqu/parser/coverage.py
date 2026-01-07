# coqu.parser.coverage - Parser coverage analysis
"""
Coverage analysis for COBOL parser.
Compares parsed components against source to identify uncovered lines.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from coqu.parser.cobol_parser import CobolParser
from coqu.parser.indexer import StructuralIndexer, StructuralIndex
from coqu.parser.ast import CobolProgram


@dataclass
class CoverageResult:
    """Result of coverage analysis."""
    total_lines: int
    covered_lines: set[int] = field(default_factory=set)
    uncovered_lines: set[int] = field(default_factory=set)
    comment_lines: set[int] = field(default_factory=set)
    blank_lines: set[int] = field(default_factory=set)

    # Breakdown by component type
    division_lines: set[int] = field(default_factory=set)
    section_lines: set[int] = field(default_factory=set)
    paragraph_lines: set[int] = field(default_factory=set)
    statement_lines: set[int] = field(default_factory=set)
    data_item_lines: set[int] = field(default_factory=set)
    id_entry_lines: set[int] = field(default_factory=set)  # PROGRAM-ID, AUTHOR, etc.
    file_entry_lines: set[int] = field(default_factory=set)  # SELECT, FD, SD
    copybook_lines: set[int] = field(default_factory=set)  # COPY statements
    exec_lines: set[int] = field(default_factory=set)  # EXEC SQL/CICS blocks

    @property
    def code_lines(self) -> int:
        """Lines that are actual code (not comments or blank)."""
        return self.total_lines - len(self.comment_lines) - len(self.blank_lines)

    @property
    def coverage_percent(self) -> float:
        """Coverage percentage of code lines."""
        if self.code_lines == 0:
            return 100.0
        return (len(self.covered_lines) / self.code_lines) * 100

    def summary(self) -> str:
        """Return a summary string."""
        lines = [
            f"Total lines: {self.total_lines}",
            f"Code lines: {self.code_lines}",
            f"  - Comment lines: {len(self.comment_lines)}",
            f"  - Blank lines: {len(self.blank_lines)}",
            f"Covered lines: {len(self.covered_lines)}",
            f"Uncovered lines: {len(self.uncovered_lines)}",
            f"Coverage: {self.coverage_percent:.1f}%",
            "",
            "Breakdown by component:",
            f"  - Division headers: {len(self.division_lines)}",
            f"  - Section headers: {len(self.section_lines)}",
            f"  - Paragraph headers: {len(self.paragraph_lines)}",
            f"  - Statements: {len(self.statement_lines)}",
            f"  - Data items: {len(self.data_item_lines)}",
            f"  - ID entries (PROGRAM-ID, etc.): {len(self.id_entry_lines)}",
            f"  - File entries (SELECT, FD): {len(self.file_entry_lines)}",
            f"  - Copybook refs: {len(self.copybook_lines)}",
            f"  - EXEC SQL/CICS: {len(self.exec_lines)}",
        ]
        return "\n".join(lines)

    def uncovered_list(self) -> str:
        """Return list of uncovered line numbers."""
        if not self.uncovered_lines:
            return "No uncovered lines."

        sorted_lines = sorted(self.uncovered_lines)
        # Group consecutive lines into ranges
        ranges = []
        start = sorted_lines[0]
        end = start

        for line in sorted_lines[1:]:
            if line == end + 1:
                end = line
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = line
                end = line

        # Add last range
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")

        return f"Uncovered lines ({len(self.uncovered_lines)}): {', '.join(ranges)}"


class CoverageAnalyzer:
    """
    Analyzes parser coverage of COBOL source files.

    Compares what the parser captures against the original source
    to identify lines not covered by any parsed component.
    """

    def __init__(self):
        self.parser = CobolParser()
        self.indexer = StructuralIndexer()

    def _is_sequence_number_only(self, line: str) -> bool:
        """Check if line contains only a sequence number (mainframe format).

        Mainframe COBOL uses columns 1-6 for sequence numbers. A line with
        only a sequence number and nothing in columns 7+ is effectively blank.
        """
        if len(line) < 6:
            return False
        # Check if columns 1-6 are digits/spaces (sequence number area)
        seq_area = line[:6]
        if not seq_area.replace(' ', '').isdigit():
            return False
        # Check if columns 7+ are blank or don't exist
        if len(line) <= 6:
            return True
        return line[6:].strip() == ''

    def analyze_file(
        self,
        path: Path,
        mode: str = "both",
    ) -> dict[str, CoverageResult]:
        """
        Analyze coverage for a COBOL file.

        Args:
            path: Path to COBOL source file
            mode: "antlr", "indexer", or "both"

        Returns:
            Dict mapping mode name to CoverageResult
        """
        source = path.read_text()
        return self.analyze(source, mode)

    def analyze(
        self,
        source: str,
        mode: str = "both",
    ) -> dict[str, CoverageResult]:
        """
        Analyze coverage for COBOL source.

        Args:
            source: COBOL source code
            mode: "antlr", "indexer", or "both"

        Returns:
            Dict mapping mode name to CoverageResult
        """
        results = {}

        # Identify comment and blank lines first
        lines = source.split("\n")
        comment_lines = set()
        blank_lines = set()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                blank_lines.add(i)
            elif len(line) > 6 and line[6] == '*':
                # Traditional COBOL comment (indicator in column 7)
                comment_lines.add(i)
            elif stripped.startswith('*>'):
                # Inline comment
                comment_lines.add(i)
            elif stripped.startswith('*'):
                # Free-format comment
                comment_lines.add(i)
            elif self._is_sequence_number_only(line):
                # Mainframe format: line with only sequence number (columns 1-6)
                blank_lines.add(i)

        if mode in ("antlr", "both"):
            result = self._analyze_antlr(source, lines, comment_lines, blank_lines)
            results["antlr"] = result

        if mode in ("indexer", "both"):
            result = self._analyze_indexer(source, lines, comment_lines, blank_lines)
            results["indexer"] = result

        return results

    def _analyze_antlr(
        self,
        source: str,
        lines: list[str],
        comment_lines: set[int],
        blank_lines: set[int],
    ) -> CoverageResult:
        """Analyze coverage using ANTLR parser."""
        total_lines = len(lines)
        result = CoverageResult(
            total_lines=total_lines,
            comment_lines=comment_lines.copy(),
            blank_lines=blank_lines.copy(),
        )

        try:
            program = self.parser.parse(source, preprocess=False)
        except Exception:
            # If parsing fails, return empty coverage
            result.uncovered_lines = set(range(1, total_lines + 1)) - comment_lines - blank_lines
            return result

        # Collect covered lines from all components
        self._collect_from_program(program, result)

        # Calculate uncovered
        all_lines = set(range(1, total_lines + 1))
        code_lines = all_lines - comment_lines - blank_lines
        result.uncovered_lines = code_lines - result.covered_lines

        return result

    def _analyze_indexer(
        self,
        source: str,
        lines: list[str],
        comment_lines: set[int],
        blank_lines: set[int],
    ) -> CoverageResult:
        """Analyze coverage using regex indexer."""
        total_lines = len(lines)
        result = CoverageResult(
            total_lines=total_lines,
            comment_lines=comment_lines.copy(),
            blank_lines=blank_lines.copy(),
        )

        index = self.indexer.index(source)
        self._collect_from_index(index, result)

        # Calculate uncovered
        all_lines = set(range(1, total_lines + 1))
        code_lines = all_lines - comment_lines - blank_lines
        result.uncovered_lines = code_lines - result.covered_lines

        return result

    def _collect_from_program(self, program: CobolProgram, result: CoverageResult) -> None:
        """Collect covered lines from ANTLR-parsed program."""
        for div in program.divisions:
            # Division header line
            result.division_lines.add(div.location.line_start)
            result.covered_lines.add(div.location.line_start)

            for section in div.sections:
                # Section header line
                result.section_lines.add(section.location.line_start)
                result.covered_lines.add(section.location.line_start)

                # Data items in section
                for item in section.data_items:
                    for line in range(item.location.line_start, item.location.line_end + 1):
                        result.data_item_lines.add(line)
                        result.covered_lines.add(line)

                # Paragraphs in section
                for para in section.paragraphs:
                    result.paragraph_lines.add(para.location.line_start)
                    result.covered_lines.add(para.location.line_start)

                    # Statements in paragraph
                    for stmt in para.statements:
                        for line in range(stmt.location.line_start, stmt.location.line_end + 1):
                            result.statement_lines.add(line)
                            result.covered_lines.add(line)

            # Top-level paragraphs in division
            for para in div.paragraphs:
                result.paragraph_lines.add(para.location.line_start)
                result.covered_lines.add(para.location.line_start)

                for stmt in para.statements:
                    for line in range(stmt.location.line_start, stmt.location.line_end + 1):
                        result.statement_lines.add(line)
                        result.covered_lines.add(line)

    def _collect_from_index(self, index: StructuralIndex, result: CoverageResult) -> None:
        """Collect covered lines from indexed structure."""
        # Divisions
        for div in index.divisions:
            result.division_lines.add(div.line_start)
            result.covered_lines.add(div.line_start)

        # Sections
        for sec in index.sections:
            result.section_lines.add(sec.line_start)
            result.covered_lines.add(sec.line_start)

        # Paragraphs
        for para in index.paragraphs:
            result.paragraph_lines.add(para.line_start)
            result.covered_lines.add(para.line_start)

        # Data items (all levels)
        for item in index.data_items_all:
            result.data_item_lines.add(item.line_start)
            result.covered_lines.add(item.line_start)

        # Statements
        for stmt in index.statements:
            result.statement_lines.add(stmt.line_start)
            result.covered_lines.add(stmt.line_start)

        # IDENTIFICATION DIVISION entries (PROGRAM-ID, AUTHOR, etc.)
        for entry in index.id_division_entries:
            result.id_entry_lines.add(entry.line_start)
            result.covered_lines.add(entry.line_start)

        # FILE-CONTROL entries (SELECT, FD, SD)
        for entry in index.file_entries:
            result.file_entry_lines.add(entry.line_start)
            result.covered_lines.add(entry.line_start)

        # Copybook references
        for entry in index.copybooks:
            result.copybook_lines.add(entry.line_start)
            result.covered_lines.add(entry.line_start)

        # EXEC SQL/CICS blocks (multi-line)
        for stmt in index.exec_statements:
            for line in range(stmt.line_start, stmt.line_end + 1):
                result.exec_lines.add(line)
                result.covered_lines.add(line)


def analyze_coverage(
    path: Path,
    mode: str = "both",
) -> dict[str, CoverageResult]:
    """
    Convenience function to analyze coverage.

    Args:
        path: Path to COBOL file
        mode: "antlr", "indexer", or "both"

    Returns:
        Dict mapping mode name to CoverageResult
    """
    analyzer = CoverageAnalyzer()
    return analyzer.analyze_file(path, mode)
