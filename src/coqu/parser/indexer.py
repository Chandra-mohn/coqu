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

    # Level 01 data items
    LEVEL_01_PATTERN = re.compile(
        PREFIX + r"\s*01\s+([A-Z][A-Z0-9-]*)",
        re.IGNORECASE | re.MULTILINE,
    )

    def index(
        self,
        source: str,
        progress_callback: Optional[callable] = None,
    ) -> StructuralIndex:
        """
        Create structural index from COBOL source.

        Args:
            source: COBOL source code as string
            progress_callback: Optional callback(stage, percent) for progress updates

        Returns:
            StructuralIndex with divisions, sections, paragraphs, etc.
        """
        # Map internal progress (0-100) to external range (15-90)
        # This integrates with workspace.py which uses 0-15 for reading, 15-90 for parsing, 90-100 for caching
        def report(stage: str, internal_pct: int) -> None:
            if progress_callback:
                # Scale 0-100 internal to 15-90 external
                external_pct = 15 + int(internal_pct * 0.75)
                progress_callback(stage, external_pct)

        report("Normalizing", 0)

        # Normalize line endings (Windows CRLF -> LF)
        if "\r" in source:
            source = source.replace("\r\n", "\n").replace("\r", "\n")

        index = StructuralIndex()

        report("Building line index", 5)

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

        import bisect

        def get_line_num(char_pos: int) -> int:
            """Binary search for line number - O(log n) instead of O(n)."""
            return bisect.bisect_right(line_offsets, char_pos)

        # For large files, we report progress during regex scanning
        # Progress allocation: divisions 10-15, sections 15-35, paragraphs 35-55,
        #                      copybooks 55-75, data items 75-90
        total_chars = len(source)
        total_lines = len(line_offsets)
        is_large_file = total_chars > 500000  # ~10K+ lines

        def scan_chunked_with_progress(
            pattern,
            stage_name: str,
            start_pct: int,
            end_pct: int,
            start_line: int = 1,
        ):
            """
            Scan source in chunks, reporting progress between chunks.

            For large files, this ensures the progress bar updates even when
            matches are sparse (e.g., 618 sections in 254K lines).
            """
            matches = []

            if not is_large_file:
                # Small file - just scan directly
                start_offset = line_offsets[start_line - 1] if start_line > 1 else 0
                for match in pattern.finditer(source, start_offset):
                    matches.append((match, get_line_num(match.start())))
                return matches

            # Large file - scan in chunks of ~10K lines for smooth progress
            chunk_size = 10000  # lines per chunk
            end_line = total_lines

            current_line = start_line
            while current_line < end_line:
                # Calculate chunk boundaries
                chunk_end_line = min(current_line + chunk_size, end_line)
                chunk_start_offset = line_offsets[current_line - 1] if current_line > 1 else 0
                chunk_end_offset = line_offsets[chunk_end_line - 1] if chunk_end_line < total_lines else total_chars

                # Extract chunk and search
                chunk = source[chunk_start_offset:chunk_end_offset]
                for match in pattern.finditer(chunk):
                    actual_pos = chunk_start_offset + match.start()
                    line_num = get_line_num(actual_pos)
                    # Create a simple match-like object with the info we need
                    matches.append((match, line_num))

                # Report progress based on lines processed
                progress_in_stage = (chunk_end_line - start_line) / max(end_line - start_line, 1)
                current_pct = start_pct + int(progress_in_stage * (end_pct - start_pct))
                report(f"{stage_name} (line {chunk_end_line:,})", current_pct)

                current_line = chunk_end_line

            return matches

        report("Finding divisions", 10)

        # Index divisions (typically only 4, fast)
        for match in self.DIVISION_PATTERN.finditer(source):
            line_num = get_line_num(match.start())
            div_name = match.group(1).upper()
            index.divisions.append(IndexEntry(
                name=f"{div_name} DIVISION",
                type="division",
                line_start=line_num,
            ))

        report("Finding sections", 15)

        # Index sections with progress
        section_matches = scan_chunked_with_progress(
            self.SECTION_PATTERN, "Sections", 15, 35
        )
        for match, line_num in section_matches:
            section_name = match.group(1).upper()
            index.sections.append(IndexEntry(
                name=f"{section_name} SECTION",
                type="section",
                line_start=line_num,
            ))

        report("Finding paragraphs", 35)

        # Index paragraphs (only in PROCEDURE DIVISION)
        proc_div_start = 0
        for div in index.divisions:
            if "PROCEDURE" in div.name:
                proc_div_start = div.line_start
                break

        if proc_div_start > 0:
            # Search only in PROCEDURE DIVISION portion with progress
            para_matches = scan_chunked_with_progress(
                self.PARAGRAPH_PATTERN, "Paragraphs", 35, 55, proc_div_start
            )
            for match, line_num in para_matches:
                para_name = match.group(1).upper()

                # Skip if it looks like a section
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

        report("Finding copybooks", 55)

        # Index COPY statements with progress
        copy_matches = scan_chunked_with_progress(
            self.COPY_PATTERN, "Copybooks", 55, 75
        )
        for match, line_num in copy_matches:
            copybook_name = match.group(1).upper()
            index.copybooks.append(IndexEntry(
                name=copybook_name,
                type="copybook",
                line_start=line_num,
            ))

        report("Finding data items", 75)

        # Index level-01 data items with progress
        data_matches = scan_chunked_with_progress(
            self.LEVEL_01_PATTERN, "Data items", 75, 90
        )
        for match, line_num in data_matches:
            item_name = match.group(1).upper()
            index.data_items_01.append(IndexEntry(
                name=item_name,
                type="data_item",
                line_start=line_num,
            ))

        report("Calculating ranges", 90)

        # Post-process: calculate line_end for each entry
        self._calculate_line_ends(index)

        report("Complete", 100)

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
