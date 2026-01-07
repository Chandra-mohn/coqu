# coqu.parser.indexer - Lightweight structural indexer
"""
Fast regex-based structural indexer for large COBOL files.
This provides quick navigation without full ANTLR parsing.
"""
import bisect
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
class StatementEntry:
    """Statement entry in the structural index."""
    type: str  # MOVE, CALL, PERFORM, IF, etc.
    line_start: int
    line_end: int = 0
    paragraph: str = ""  # Containing paragraph name

    def __str__(self) -> str:
        return f"{self.type} at line {self.line_start}"


@dataclass
class StructuralIndex:
    """Fast structural index of a COBOL program."""
    divisions: list[IndexEntry] = field(default_factory=list)
    sections: list[IndexEntry] = field(default_factory=list)
    paragraphs: list[IndexEntry] = field(default_factory=list)
    copybooks: list[IndexEntry] = field(default_factory=list)
    data_items_01: list[IndexEntry] = field(default_factory=list)
    data_items_all: list[IndexEntry] = field(default_factory=list)  # All levels
    statements: list[StatementEntry] = field(default_factory=list)
    id_division_entries: list[IndexEntry] = field(default_factory=list)  # PROGRAM-ID, AUTHOR, etc.
    file_entries: list[IndexEntry] = field(default_factory=list)  # SELECT, FD, SD
    exec_statements: list[StatementEntry] = field(default_factory=list)  # EXEC SQL/CICS blocks
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
    #
    # Supported formats:
    # 1. Traditional mainframe: 6 digits in columns 1-6 ("000100")
    # 2. Free format: leading spaces ("      ")
    # 3. Panvalet/Librarian: version markers ("1.1    ", "07.141 ")
    # 4. Mixed: any combination
    #
    # The PREFIX is intentionally flexible to handle various source control outputs

    # Prefix pattern matches:
    # - 6 digits (sequence numbers): "000100"
    # - 6-8 spaces: "      " or "       "
    # - Version markers: "1.1    ", "07.141", "01.141", "3.2001"
    # - Panvalet with area indicator: "7.682A", "7.141A" (A=Area A, B=Area B)
    # - No prefix at all (code starts at column 1)
    # Key: version number is SHORT (1-6 chars with dots) followed by optional A/B and REQUIRED space(s)
    # The space after the prefix is mandatory - this distinguishes prefix from code
    PREFIX = r"^(?:[\d.]{1,6}[A-B]?\s+|[\s]{6,8})?"

    # Division pattern: "IDENTIFICATION DIVISION" or "ID DIVISION", etc.
    DIVISION_PATTERN = re.compile(
        PREFIX + r"\s*(IDENTIFICATION|ID|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION",
        re.IGNORECASE | re.MULTILINE,
    )

    # Section pattern: "WORKING-STORAGE SECTION", "INPUT-OUTPUT SECTION", etc.
    SECTION_PATTERN = re.compile(
        PREFIX + r"\s*([A-Z0-9][A-Z0-9-]*)\s+SECTION\s*\.?",
        re.IGNORECASE | re.MULTILINE,
    )

    # Paragraph pattern: paragraph name in Area A followed by period
    # Must be at column 8 (after 6-digit sequence + indicator)
    # Paragraph names start with letter or digit, contain letters, digits, hyphens
    PARAGRAPH_PATTERN = re.compile(
        PREFIX + r"([A-Z0-9][A-Z0-9-]{0,29})\s*\.\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    # COPY statement - can appear anywhere in Area B
    COPY_PATTERN = re.compile(
        PREFIX + r"\s*COPY\s+['\"]?([A-Z][A-Z0-9-]*)['\"]?",
        re.IGNORECASE | re.MULTILINE,
    )

    # Statement patterns for PROCEDURE DIVISION
    # These match the beginning of common COBOL statements
    STATEMENT_PATTERNS = {
        "MOVE": re.compile(PREFIX + r"\s+MOVE\s+", re.IGNORECASE | re.MULTILINE),
        "PERFORM": re.compile(PREFIX + r"\s+PERFORM\s+", re.IGNORECASE | re.MULTILINE),
        "CALL": re.compile(PREFIX + r"\s+CALL\s+", re.IGNORECASE | re.MULTILINE),
        "IF": re.compile(PREFIX + r"\s+IF\s+", re.IGNORECASE | re.MULTILINE),
        "EVALUATE": re.compile(PREFIX + r"\s+EVALUATE\s+", re.IGNORECASE | re.MULTILINE),
        "READ": re.compile(PREFIX + r"\s+READ\s+", re.IGNORECASE | re.MULTILINE),
        "WRITE": re.compile(PREFIX + r"\s+WRITE\s+", re.IGNORECASE | re.MULTILINE),
        "OPEN": re.compile(PREFIX + r"\s+OPEN\s+", re.IGNORECASE | re.MULTILINE),
        "CLOSE": re.compile(PREFIX + r"\s+CLOSE\s+", re.IGNORECASE | re.MULTILINE),
        "DISPLAY": re.compile(PREFIX + r"\s+DISPLAY\s+", re.IGNORECASE | re.MULTILINE),
        "ACCEPT": re.compile(PREFIX + r"\s+ACCEPT\s+", re.IGNORECASE | re.MULTILINE),
        "COMPUTE": re.compile(PREFIX + r"\s+COMPUTE\s+", re.IGNORECASE | re.MULTILINE),
        "ADD": re.compile(PREFIX + r"\s+ADD\s+", re.IGNORECASE | re.MULTILINE),
        "SUBTRACT": re.compile(PREFIX + r"\s+SUBTRACT\s+", re.IGNORECASE | re.MULTILINE),
        "MULTIPLY": re.compile(PREFIX + r"\s+MULTIPLY\s+", re.IGNORECASE | re.MULTILINE),
        "DIVIDE": re.compile(PREFIX + r"\s+DIVIDE\s+", re.IGNORECASE | re.MULTILINE),
        "STRING": re.compile(PREFIX + r"\s+STRING\s+", re.IGNORECASE | re.MULTILINE),
        "UNSTRING": re.compile(PREFIX + r"\s+UNSTRING\s+", re.IGNORECASE | re.MULTILINE),
        "INSPECT": re.compile(PREFIX + r"\s+INSPECT\s+", re.IGNORECASE | re.MULTILINE),
        "INITIALIZE": re.compile(PREFIX + r"\s+INITIALIZE\s+", re.IGNORECASE | re.MULTILINE),
        "SET": re.compile(PREFIX + r"\s+SET\s+", re.IGNORECASE | re.MULTILINE),
        "STOP": re.compile(PREFIX + r"\s+STOP\s+", re.IGNORECASE | re.MULTILINE),
        "GO": re.compile(PREFIX + r"\s+GO\s+TO\s+", re.IGNORECASE | re.MULTILINE),
        "EXIT": re.compile(PREFIX + r"\s+EXIT\s*\.?", re.IGNORECASE | re.MULTILINE),
        "CONTINUE": re.compile(PREFIX + r"\s+CONTINUE\s*\.?", re.IGNORECASE | re.MULTILINE),
        "RETURN": re.compile(PREFIX + r"\s+RETURN\s+", re.IGNORECASE | re.MULTILINE),
        "SEARCH": re.compile(PREFIX + r"\s+SEARCH\s+", re.IGNORECASE | re.MULTILINE),
        "SORT": re.compile(PREFIX + r"\s+SORT\s+", re.IGNORECASE | re.MULTILINE),
        "MERGE": re.compile(PREFIX + r"\s+MERGE\s+", re.IGNORECASE | re.MULTILINE),
        "START": re.compile(PREFIX + r"\s+START\s+", re.IGNORECASE | re.MULTILINE),
        "DELETE": re.compile(PREFIX + r"\s+DELETE\s+", re.IGNORECASE | re.MULTILINE),
        "REWRITE": re.compile(PREFIX + r"\s+REWRITE\s+", re.IGNORECASE | re.MULTILINE),
    }

    # Level 01 data items
    LEVEL_01_PATTERN = re.compile(
        PREFIX + r"\s*01\s+([A-Z][A-Z0-9-]*)",
        re.IGNORECASE | re.MULTILINE,
    )

    # All data item levels (01-49, 66, 77, 88)
    DATA_ITEM_PATTERN = re.compile(
        PREFIX + r"\s*(0[1-9]|[1-4][0-9]|66|77|88)\s+([A-Z][A-Z0-9-]*|FILLER)",
        re.IGNORECASE | re.MULTILINE,
    )

    # IDENTIFICATION DIVISION content
    PROGRAM_ID_PATTERN = re.compile(
        PREFIX + r"\s*PROGRAM-ID\s*[.\s]+([A-Z][A-Z0-9-]*)",
        re.IGNORECASE | re.MULTILINE,
    )
    AUTHOR_PATTERN = re.compile(
        PREFIX + r"\s*AUTHOR\s*[.\s]+",
        re.IGNORECASE | re.MULTILINE,
    )
    DATE_WRITTEN_PATTERN = re.compile(
        PREFIX + r"\s*DATE-WRITTEN\s*[.\s]+",
        re.IGNORECASE | re.MULTILINE,
    )
    DATE_COMPILED_PATTERN = re.compile(
        PREFIX + r"\s*DATE-COMPILED\s*[.\s]+",
        re.IGNORECASE | re.MULTILINE,
    )

    # FILE-CONTROL patterns
    FILE_CONTROL_PATTERN = re.compile(
        PREFIX + r"\s*FILE-CONTROL\s*\.?",
        re.IGNORECASE | re.MULTILINE,
    )
    SELECT_PATTERN = re.compile(
        PREFIX + r"\s*SELECT\s+([A-Z][A-Z0-9-]*)",
        re.IGNORECASE | re.MULTILINE,
    )
    FD_PATTERN = re.compile(
        PREFIX + r"\s*FD\s+([A-Z][A-Z0-9-]*)",
        re.IGNORECASE | re.MULTILINE,
    )
    SD_PATTERN = re.compile(
        PREFIX + r"\s*SD\s+([A-Z][A-Z0-9-]*)",
        re.IGNORECASE | re.MULTILINE,
    )

    # SELECT clause continuations
    SELECT_CLAUSE_PATTERNS = {
        "ORGANIZATION": re.compile(PREFIX + r"\s+ORGANIZATION\s+", re.IGNORECASE | re.MULTILINE),
        "ACCESS": re.compile(PREFIX + r"\s+ACCESS\s+MODE\s+", re.IGNORECASE | re.MULTILINE),
        "RECORD-KEY": re.compile(PREFIX + r"\s+RECORD\s+KEY\s+", re.IGNORECASE | re.MULTILINE),
        "ALTERNATE-KEY": re.compile(PREFIX + r"\s+ALTERNATE\s+RECORD\s+KEY\s+", re.IGNORECASE | re.MULTILINE),
        "FILE-STATUS": re.compile(PREFIX + r"\s+FILE\s+STATUS\s+", re.IGNORECASE | re.MULTILINE),
        "ASSIGN": re.compile(PREFIX + r"\s+ASSIGN\s+", re.IGNORECASE | re.MULTILINE),
        "RELATIVE-KEY": re.compile(PREFIX + r"\s+RELATIVE\s+KEY\s+", re.IGNORECASE | re.MULTILINE),
    }

    # Statement terminators and continuations
    END_STATEMENT_PATTERNS = {
        "END-IF": re.compile(PREFIX + r"\s+END-IF\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-READ": re.compile(PREFIX + r"\s+END-READ\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-WRITE": re.compile(PREFIX + r"\s+END-WRITE\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-PERFORM": re.compile(PREFIX + r"\s+END-PERFORM\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-EVALUATE": re.compile(PREFIX + r"\s+END-EVALUATE\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-CALL": re.compile(PREFIX + r"\s+END-CALL\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-SEARCH": re.compile(PREFIX + r"\s+END-SEARCH\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-STRING": re.compile(PREFIX + r"\s+END-STRING\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-UNSTRING": re.compile(PREFIX + r"\s+END-UNSTRING\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-COMPUTE": re.compile(PREFIX + r"\s+END-COMPUTE\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-ADD": re.compile(PREFIX + r"\s+END-ADD\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-SUBTRACT": re.compile(PREFIX + r"\s+END-SUBTRACT\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-MULTIPLY": re.compile(PREFIX + r"\s+END-MULTIPLY\s*\.?", re.IGNORECASE | re.MULTILINE),
        "END-DIVIDE": re.compile(PREFIX + r"\s+END-DIVIDE\s*\.?", re.IGNORECASE | re.MULTILINE),
        "AT-END": re.compile(PREFIX + r"\s+AT\s+END\s+", re.IGNORECASE | re.MULTILINE),
        "NOT-AT-END": re.compile(PREFIX + r"\s+NOT\s+AT\s+END\s+", re.IGNORECASE | re.MULTILINE),
        "INVALID-KEY": re.compile(PREFIX + r"\s+INVALID\s+KEY\s+", re.IGNORECASE | re.MULTILINE),
        "NOT-INVALID-KEY": re.compile(PREFIX + r"\s+NOT\s+INVALID\s+KEY\s+", re.IGNORECASE | re.MULTILINE),
        "WHEN": re.compile(PREFIX + r"\s+WHEN\s+", re.IGNORECASE | re.MULTILINE),
        "ELSE": re.compile(PREFIX + r"\s+ELSE\s*$", re.IGNORECASE | re.MULTILINE),
        "THEN": re.compile(PREFIX + r"\s+THEN\s*$", re.IGNORECASE | re.MULTILINE),
    }

    # EXEC SQL/CICS blocks (multi-line)
    EXEC_PATTERN = re.compile(
        r"^\d{0,6}\s+(EXEC\s+(?:SQL|CICS).*?END-EXEC)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    def index(self, source: str) -> StructuralIndex:
        """
        Create structural index from COBOL source.

        Args:
            source: COBOL source code as string

        Returns:
            StructuralIndex with divisions, sections, paragraphs, etc.
        """
        # Normalize line endings (Windows CRLF -> LF)
        if "\r" in source:
            source = source.replace("\r\n", "\n").replace("\r", "\n")

        index = StructuralIndex()

        # Build line offset index for O(1) line number lookup
        # This is the key optimization - build once, use many times
        line_offsets = [0]
        pos = 0
        while True:
            pos = source.find("\n", pos)
            if pos == -1:
                break
            pos += 1
            line_offsets.append(pos)
        index.total_lines = len(line_offsets)

        def get_line_num(char_pos: int) -> int:
            """Binary search for line number - O(log n) instead of O(n)."""
            return bisect.bisect_right(line_offsets, char_pos)

        def get_line_num_skip_newline(char_pos: int) -> int:
            """Get line number, skipping past any leading newline character."""
            # If position is at a newline, move to next character
            if char_pos < len(source) and source[char_pos] == '\n':
                char_pos += 1
            return bisect.bisect_right(line_offsets, char_pos)

        # Index divisions (typically only 4, fast)
        for match in self.DIVISION_PATTERN.finditer(source):
            # Use capture group position for accurate line number
            line_num = get_line_num(match.start(1))
            div_name = match.group(1).upper()
            index.divisions.append(IndexEntry(
                name=f"{div_name} DIVISION",
                type="division",
                line_start=line_num,
            ))

        # Index sections
        for match in self.SECTION_PATTERN.finditer(source):
            # Use capture group position for accurate line number
            line_num = get_line_num(match.start(1))
            section_name = match.group(1).upper()
            index.sections.append(IndexEntry(
                name=f"{section_name} SECTION",
                type="section",
                line_start=line_num,
            ))

        # Index paragraphs (only in PROCEDURE DIVISION)
        proc_div_start = 0
        proc_div_offset = 0
        for div in index.divisions:
            if "PROCEDURE" in div.name:
                proc_div_start = div.line_start
                # Find character offset for PROCEDURE DIVISION
                if proc_div_start > 0 and proc_div_start <= len(line_offsets):
                    proc_div_offset = line_offsets[proc_div_start - 1]
                break

        if proc_div_start > 0:
            # Search only in PROCEDURE DIVISION portion
            proc_source = source[proc_div_offset:]
            for match in self.PARAGRAPH_PATTERN.finditer(proc_source):
                para_name = match.group(1).upper()

                # Skip if it looks like a section
                if "SECTION" in para_name:
                    continue

                # Skip common false positives
                if para_name in ("DIVISION", "SECTION", "END", "EXIT"):
                    continue

                # Calculate actual line number using capture group position
                line_num = get_line_num(proc_div_offset + match.start(1))
                index.paragraphs.append(IndexEntry(
                    name=para_name,
                    type="paragraph",
                    line_start=line_num,
                ))

        # Index COPY statements
        for match in self.COPY_PATTERN.finditer(source):
            # Use capture group position
            line_num = get_line_num(match.start(1))
            copybook_name = match.group(1).upper()
            index.copybooks.append(IndexEntry(
                name=copybook_name,
                type="copybook",
                line_start=line_num,
            ))

        # Index level-01 data items
        for match in self.LEVEL_01_PATTERN.finditer(source):
            # Use capture group position
            line_num = get_line_num(match.start(1))
            item_name = match.group(1).upper()
            index.data_items_01.append(IndexEntry(
                name=item_name,
                type="data_item",
                line_start=line_num,
            ))

        # Index ALL data items (all levels: 01-49, 66, 77, 88)
        for match in self.DATA_ITEM_PATTERN.finditer(source):
            # Use capture group position
            line_num = get_line_num(match.start(1))
            level = match.group(1)
            item_name = match.group(2).upper()
            index.data_items_all.append(IndexEntry(
                name=f"{level} {item_name}",
                type="data_item",
                line_start=line_num,
            ))

        # Index IDENTIFICATION DIVISION entries
        for pattern, entry_type in [
            (self.PROGRAM_ID_PATTERN, "PROGRAM-ID"),
            (self.AUTHOR_PATTERN, "AUTHOR"),
            (self.DATE_WRITTEN_PATTERN, "DATE-WRITTEN"),
            (self.DATE_COMPILED_PATTERN, "DATE-COMPILED"),
        ]:
            for match in pattern.finditer(source):
                # Use skip_newline to handle MULTILINE ^ edge cases
                line_num = get_line_num_skip_newline(match.start())
                index.id_division_entries.append(IndexEntry(
                    name=entry_type,
                    type="id_entry",
                    line_start=line_num,
                ))

        # Index FILE-CONTROL paragraph
        for match in self.FILE_CONTROL_PATTERN.finditer(source):
            line_num = get_line_num_skip_newline(match.start())
            index.file_entries.append(IndexEntry(
                name="FILE-CONTROL",
                type="file_entry",
                line_start=line_num,
            ))

        # Index FILE-CONTROL entries (SELECT, FD, SD)
        for pattern, entry_type in [
            (self.SELECT_PATTERN, "SELECT"),
            (self.FD_PATTERN, "FD"),
            (self.SD_PATTERN, "SD"),
        ]:
            for match in pattern.finditer(source):
                # Use skip_newline to handle MULTILINE ^ edge cases
                line_num = get_line_num_skip_newline(match.start())
                name = match.group(1).upper() if match.lastindex else entry_type
                index.file_entries.append(IndexEntry(
                    name=f"{entry_type} {name}",
                    type="file_entry",
                    line_start=line_num,
                ))

        # Index SELECT clause continuations (ORGANIZATION, ACCESS MODE, etc.)
        for clause_type, pattern in self.SELECT_CLAUSE_PATTERNS.items():
            for match in pattern.finditer(source):
                line_num = get_line_num_skip_newline(match.start())
                index.file_entries.append(IndexEntry(
                    name=clause_type,
                    type="file_clause",
                    line_start=line_num,
                ))

        # Post-process: calculate line_end for each entry
        self._calculate_line_ends(index)

        # Index statements (only in PROCEDURE DIVISION)
        if proc_div_start > 0:
            proc_source = source[proc_div_offset:]
            # Build sorted list of paragraph starts for containment lookup
            para_starts = sorted(
                [(p.line_start, p.name) for p in index.paragraphs],
                key=lambda x: x[0]
            )

            # Index main statements
            for stmt_type, pattern in self.STATEMENT_PATTERNS.items():
                for match in pattern.finditer(proc_source):
                    line_num = get_line_num_skip_newline(proc_div_offset + match.start())

                    # Find containing paragraph
                    containing_para = ""
                    for para_line, para_name in reversed(para_starts):
                        if para_line <= line_num:
                            containing_para = para_name
                            break

                    index.statements.append(StatementEntry(
                        type=stmt_type,
                        line_start=line_num,
                        line_end=line_num,
                        paragraph=containing_para,
                    ))

            # Index statement terminators and continuations (END-IF, AT END, etc.)
            for stmt_type, pattern in self.END_STATEMENT_PATTERNS.items():
                for match in pattern.finditer(proc_source):
                    line_num = get_line_num_skip_newline(proc_div_offset + match.start())

                    # Find containing paragraph
                    containing_para = ""
                    for para_line, para_name in reversed(para_starts):
                        if para_line <= line_num:
                            containing_para = para_name
                            break

                    index.statements.append(StatementEntry(
                        type=stmt_type,
                        line_start=line_num,
                        line_end=line_num,
                        paragraph=containing_para,
                    ))

            # Sort statements by line number
            index.statements.sort(key=lambda s: s.line_start)

        # Index EXEC SQL/CICS blocks (multi-line) - search entire source
        # These can appear in DATA DIVISION (EXEC SQL INCLUDE) or PROCEDURE DIVISION
        for match in self.EXEC_PATTERN.finditer(source):
            exec_text = match.group(1)
            start_pos = match.start(1)
            end_pos = match.end(1)
            line_start = get_line_num_skip_newline(start_pos)
            line_end = bisect.bisect_right(line_offsets, end_pos - 1)

            # Determine EXEC type (SQL or CICS)
            exec_type = "EXEC-SQL" if "SQL" in exec_text.upper()[:15] else "EXEC-CICS"

            # Find containing paragraph (if in PROCEDURE DIVISION)
            containing_para = ""
            for para in index.paragraphs:
                if para.line_start <= line_start:
                    containing_para = para.name
                else:
                    break

            index.exec_statements.append(StatementEntry(
                type=exec_type,
                line_start=line_start,
                line_end=line_end,
                paragraph=containing_para,
            ))

        # Sort EXEC statements by line number
        index.exec_statements.sort(key=lambda s: s.line_start)

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
