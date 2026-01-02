# coqu.parser.chunk_analyzer - Targeted chunk analysis
"""
Chunk-based semantic analyzer for COBOL code.

Instead of parsing entire files with ANTLR (slow for large files),
this module extracts and analyzes small chunks on-demand using
regex patterns for PERFORM, CALL, and other semantic information.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChunkAnalysis:
    """Result of analyzing a code chunk."""
    performs: list[str] = field(default_factory=list)  # PERFORM targets
    calls: list[str] = field(default_factory=list)  # CALL targets
    moves: list[tuple[str, str]] = field(default_factory=list)  # (from, to) pairs
    conditions: list[str] = field(default_factory=list)  # IF/EVALUATE conditions
    data_refs: list[str] = field(default_factory=list)  # Referenced data items


class ChunkAnalyzer:
    """
    Analyzes small chunks of COBOL code for semantic information.

    This is much faster than full ANTLR parsing for targeted queries.
    For a 50-line paragraph, analysis takes ~1ms vs seconds for full file.
    """

    # PERFORM patterns
    # PERFORM para-name
    # PERFORM para-name THRU para-name
    # PERFORM para-name UNTIL condition
    # PERFORM para-name VARYING ...
    PERFORM_SIMPLE = re.compile(
        r"\bPERFORM\s+([A-Z][A-Z0-9-]{0,29})\b",
        re.IGNORECASE,
    )

    PERFORM_THRU = re.compile(
        r"\bPERFORM\s+([A-Z][A-Z0-9-]{0,29})\s+(?:THRU|THROUGH)\s+([A-Z][A-Z0-9-]{0,29})\b",
        re.IGNORECASE,
    )

    # CALL patterns
    # CALL 'program-name'
    # CALL "program-name"
    # CALL identifier
    CALL_LITERAL = re.compile(
        r"\bCALL\s+['\"]([A-Z][A-Z0-9-]*)['\"]",
        re.IGNORECASE,
    )

    CALL_IDENTIFIER = re.compile(
        r"\bCALL\s+([A-Z][A-Z0-9-]+)\b(?!\s*['\"])",
        re.IGNORECASE,
    )

    # MOVE patterns
    # MOVE value TO target
    # MOVE CORRESPONDING source TO target
    MOVE_PATTERN = re.compile(
        r"\bMOVE\s+(?:CORRESPONDING\s+)?(\S+)\s+TO\s+([A-Z][A-Z0-9-]*)",
        re.IGNORECASE,
    )

    # GO TO pattern
    GOTO_PATTERN = re.compile(
        r"\bGO\s+TO\s+([A-Z][A-Z0-9-]{0,29})\b",
        re.IGNORECASE,
    )

    # Data reference pattern (variable names in statements)
    DATA_REF_PATTERN = re.compile(
        r"\b([A-Z][A-Z0-9-]*(?:-[A-Z0-9]+)+)\b",
        re.IGNORECASE,
    )

    # Keywords to exclude from PERFORM targets
    PERFORM_KEYWORDS = {
        "UNTIL", "VARYING", "TIMES", "WITH", "TEST", "BEFORE", "AFTER",
        "THRU", "THROUGH", "END-PERFORM",
    }

    # Keywords to exclude from data references
    COBOL_KEYWORDS = {
        "IDENTIFICATION", "DIVISION", "PROGRAM-ID", "ENVIRONMENT", "DATA",
        "PROCEDURE", "WORKING-STORAGE", "SECTION", "LINKAGE", "FILE",
        "MOVE", "TO", "FROM", "PERFORM", "CALL", "USING", "BY", "REFERENCE",
        "CONTENT", "VALUE", "IF", "ELSE", "END-IF", "EVALUATE", "WHEN",
        "END-EVALUATE", "DISPLAY", "ACCEPT", "COMPUTE", "ADD", "SUBTRACT",
        "MULTIPLY", "DIVIDE", "STRING", "UNSTRING", "INSPECT", "REPLACING",
        "READ", "WRITE", "REWRITE", "DELETE", "START", "OPEN", "CLOSE",
        "INPUT", "OUTPUT", "I-O", "EXTEND", "GO", "STOP", "RUN", "EXIT",
        "CONTINUE", "INITIALIZE", "SET", "TRUE", "FALSE", "SPACES", "ZEROS",
        "HIGH-VALUES", "LOW-VALUES", "CORRESPONDING", "CORR", "NOT", "AND",
        "OR", "GREATER", "LESS", "EQUAL", "THAN", "PIC", "PICTURE", "OCCURS",
        "TIMES", "INDEXED", "REDEFINES", "FILLER", "COPY", "REPLACING",
    }

    def analyze(self, chunk: str) -> ChunkAnalysis:
        """
        Analyze a code chunk for semantic information.

        Args:
            chunk: COBOL source code (typically a paragraph or section)

        Returns:
            ChunkAnalysis with extracted semantic information
        """
        result = ChunkAnalysis()

        # Normalize to uppercase for matching
        chunk_upper = chunk.upper()

        # Extract PERFORM targets
        result.performs = self._extract_performs(chunk_upper)

        # Extract CALL targets
        result.calls = self._extract_calls(chunk_upper)

        # Extract MOVE operations
        result.moves = self._extract_moves(chunk_upper)

        # Extract GO TO targets (add to performs for flow analysis)
        gotos = self._extract_gotos(chunk_upper)
        for goto in gotos:
            if goto not in result.performs:
                result.performs.append(goto)

        # Extract data references
        result.data_refs = self._extract_data_refs(chunk_upper)

        return result

    def _extract_performs(self, chunk: str) -> list[str]:
        """Extract PERFORM targets from chunk."""
        performs = []

        # First check for PERFORM THRU patterns
        thru_targets = set()
        for match in self.PERFORM_THRU.finditer(chunk):
            start_para = match.group(1).upper()
            end_para = match.group(2).upper()
            if start_para not in self.PERFORM_KEYWORDS:
                performs.append(start_para)
                thru_targets.add(start_para)
            if end_para not in self.PERFORM_KEYWORDS:
                if end_para not in performs:
                    performs.append(end_para)
                thru_targets.add(end_para)

        # Then get simple PERFORM targets
        for match in self.PERFORM_SIMPLE.finditer(chunk):
            target = match.group(1).upper()
            # Skip if it's a keyword or already found in THRU
            if target in self.PERFORM_KEYWORDS:
                continue
            if target in thru_targets:
                continue
            if target not in performs:
                performs.append(target)

        return performs

    def _extract_calls(self, chunk: str) -> list[str]:
        """Extract CALL targets from chunk."""
        calls = []

        # Literal calls: CALL 'PROGRAM'
        for match in self.CALL_LITERAL.finditer(chunk):
            target = match.group(1).upper()
            if target not in calls:
                calls.append(target)

        # Identifier calls: CALL WS-PROGRAM-NAME
        for match in self.CALL_IDENTIFIER.finditer(chunk):
            target = match.group(1).upper()
            # Skip common keywords
            if target in {"USING", "BY", "REFERENCE", "CONTENT", "VALUE"}:
                continue
            if target not in calls:
                calls.append(target)

        return calls

    def _extract_moves(self, chunk: str) -> list[tuple[str, str]]:
        """Extract MOVE source/target pairs from chunk."""
        moves = []

        for match in self.MOVE_PATTERN.finditer(chunk):
            source = match.group(1).upper()
            target = match.group(2).upper()
            moves.append((source, target))

        return moves

    def _extract_gotos(self, chunk: str) -> list[str]:
        """Extract GO TO targets from chunk."""
        gotos = []

        for match in self.GOTO_PATTERN.finditer(chunk):
            target = match.group(1).upper()
            if target not in gotos:
                gotos.append(target)

        return gotos

    def _extract_data_refs(self, chunk: str) -> list[str]:
        """Extract referenced data item names from chunk."""
        refs = []

        for match in self.DATA_REF_PATTERN.finditer(chunk):
            name = match.group(1).upper()
            # Skip COBOL keywords
            if name in self.COBOL_KEYWORDS:
                continue
            # Skip if looks like a paragraph name (no hyphens typically)
            # Data items usually have hyphens: WS-CUSTOMER-ID
            if '-' not in name:
                continue
            if name not in refs:
                refs.append(name)

        return refs

    def analyze_paragraph(
        self,
        source_lines: list[str],
        line_start: int,
        line_end: int,
    ) -> ChunkAnalysis:
        """
        Analyze a paragraph given line range.

        Args:
            source_lines: Full source as list of lines
            line_start: Starting line (1-based)
            line_end: Ending line (1-based)

        Returns:
            ChunkAnalysis for the paragraph
        """
        # Extract chunk (convert to 0-based index)
        chunk_lines = source_lines[line_start - 1:line_end]
        chunk = "\n".join(chunk_lines)

        return self.analyze(chunk)

    def get_chunk(
        self,
        source_lines: list[str],
        line_start: int,
        line_end: int,
    ) -> str:
        """
        Extract a chunk of source code.

        Args:
            source_lines: Full source as list of lines
            line_start: Starting line (1-based)
            line_end: Ending line (1-based)

        Returns:
            Source code chunk as string
        """
        chunk_lines = source_lines[line_start - 1:line_end]
        return "\n".join(chunk_lines)


# Singleton instance for convenience
_analyzer = ChunkAnalyzer()


def analyze_chunk(chunk: str) -> ChunkAnalysis:
    """Convenience function to analyze a chunk."""
    return _analyzer.analyze(chunk)


def analyze_paragraph(
    source_lines: list[str],
    line_start: int,
    line_end: int,
) -> ChunkAnalysis:
    """Convenience function to analyze a paragraph."""
    return _analyzer.analyze_paragraph(source_lines, line_start, line_end)
