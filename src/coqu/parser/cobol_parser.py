# coqu.parser.cobol_parser - Main COBOL parser
"""
Main COBOL parser using ANTLR4 generated code.
Provides high-level parsing API and AST extraction.
"""
import hashlib
from pathlib import Path
from typing import Optional

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from coqu.parser.generated import (
    Cobol85Lexer,
    Cobol85Parser,
    Cobol85Visitor,
)
from coqu.parser.ast import (
    CobolProgram,
    Division,
    Section,
    Paragraph,
    DataItem,
    Statement,
    Comment,
    CopybookRef,
    SourceLocation,
)
from coqu.parser.preprocessor import Preprocessor
from coqu.parser.indexer import StructuralIndexer, StructuralIndex


class ParseError(Exception):
    """Exception raised for parse errors."""
    def __init__(self, message: str, line: int = 0, column: int = 0):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Line {line}:{column} - {message}")


class CoquErrorListener(ErrorListener):
    """Custom error listener for ANTLR parser."""

    def __init__(self):
        super().__init__()
        self.errors: list[ParseError] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(ParseError(msg, line, column))


class CobolASTVisitor(Cobol85Visitor):
    """Visitor to extract AST from ANTLR parse tree."""

    def __init__(self, source_lines: list[str]):
        self.source_lines = source_lines
        self.divisions: list[Division] = []
        self.comments: list[Comment] = []
        self.current_division: Optional[Division] = None
        self.current_section: Optional[Section] = None

    def _get_location(self, ctx) -> SourceLocation:
        """Get source location from parser context."""
        start = ctx.start
        stop = ctx.stop or start
        return SourceLocation(
            line_start=start.line,
            line_end=stop.line,
            col_start=start.column,
            col_end=stop.column + len(stop.text) if stop.text else stop.column,
        )

    def _get_text(self, ctx) -> str:
        """Get original text from context."""
        if ctx is None:
            return ""
        start = ctx.start.line - 1
        stop = (ctx.stop.line if ctx.stop else ctx.start.line)
        return "\n".join(self.source_lines[start:stop])

    def visitIdentificationDivision(self, ctx):
        """Visit IDENTIFICATION DIVISION."""
        location = self._get_location(ctx)
        div = Division(
            name="IDENTIFICATION DIVISION",
            location=location,
        )
        self.divisions.append(div)
        self.current_division = div
        return self.visitChildren(ctx)

    def visitEnvironmentDivision(self, ctx):
        """Visit ENVIRONMENT DIVISION."""
        location = self._get_location(ctx)
        div = Division(
            name="ENVIRONMENT DIVISION",
            location=location,
        )
        self.divisions.append(div)
        self.current_division = div
        return self.visitChildren(ctx)

    def visitDataDivision(self, ctx):
        """Visit DATA DIVISION."""
        location = self._get_location(ctx)
        div = Division(
            name="DATA DIVISION",
            location=location,
        )
        self.divisions.append(div)
        self.current_division = div
        return self.visitChildren(ctx)

    def visitProcedureDivision(self, ctx):
        """Visit PROCEDURE DIVISION."""
        location = self._get_location(ctx)
        div = Division(
            name="PROCEDURE DIVISION",
            location=location,
        )
        self.divisions.append(div)
        self.current_division = div
        return self.visitChildren(ctx)

    def visitWorkingStorageSection(self, ctx):
        """Visit WORKING-STORAGE SECTION."""
        if self.current_division:
            location = self._get_location(ctx)
            section = Section(
                name="WORKING-STORAGE SECTION",
                location=location,
            )
            self.current_division.sections.append(section)
            self.current_section = section
        return self.visitChildren(ctx)

    def visitFileSection(self, ctx):
        """Visit FILE SECTION."""
        if self.current_division:
            location = self._get_location(ctx)
            section = Section(
                name="FILE SECTION",
                location=location,
            )
            self.current_division.sections.append(section)
            self.current_section = section
        return self.visitChildren(ctx)

    def visitLinkageSection(self, ctx):
        """Visit LINKAGE SECTION."""
        if self.current_division:
            location = self._get_location(ctx)
            section = Section(
                name="LINKAGE SECTION",
                location=location,
            )
            self.current_division.sections.append(section)
            self.current_section = section
        return self.visitChildren(ctx)

    def visitLocalStorageSection(self, ctx):
        """Visit LOCAL-STORAGE SECTION."""
        if self.current_division:
            location = self._get_location(ctx)
            section = Section(
                name="LOCAL-STORAGE SECTION",
                location=location,
            )
            self.current_division.sections.append(section)
            self.current_section = section
        return self.visitChildren(ctx)

    def visitProcedureSection(self, ctx):
        """Visit PROCEDURE section."""
        if self.current_division:
            location = self._get_location(ctx)
            # Get section name from header
            header = ctx.procedureSectionHeader()
            name = header.sectionName().getText().upper() if header else "UNKNOWN SECTION"
            section = Section(
                name=f"{name} SECTION",
                location=location,
            )
            self.current_division.sections.append(section)
            self.current_section = section
        return self.visitChildren(ctx)

    def visitParagraph(self, ctx):
        """Visit paragraph in PROCEDURE DIVISION."""
        location = self._get_location(ctx)

        # Get paragraph name
        name_ctx = ctx.paragraphName()
        name = name_ctx.getText().upper() if name_ctx else "UNKNOWN"

        para = Paragraph(
            name=name,
            location=location,
        )

        # Extract PERFORM and CALL targets
        para.performs = self._extract_performs(ctx)
        para.calls = self._extract_calls(ctx)

        # Add to current section or division
        if self.current_section and self.current_division and "PROCEDURE" in self.current_division.name:
            self.current_section.paragraphs.append(para)
        elif self.current_division and "PROCEDURE" in self.current_division.name:
            self.current_division.paragraphs.append(para)

        return self.visitChildren(ctx)

    def visitDataDescriptionEntry(self, ctx):
        """Visit data description entry."""
        if not self.current_section:
            return self.visitChildren(ctx)

        location = self._get_location(ctx)

        # Try to get level number and name
        level = 0
        name = "FILLER"

        # Get the text and parse it
        text = ctx.getText()

        # Extract level number (first thing in the entry)
        import re
        level_match = re.match(r"(\d+)", text)
        if level_match:
            level = int(level_match.group(1))

        # Extract name (after level, before PIC or next keyword)
        name_match = re.search(r"\d+\s+([A-Z][A-Z0-9-]*)", text, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).upper()

        # Extract PIC clause
        pic = None
        pic_match = re.search(r"PIC(?:TURE)?\s+IS\s+(\S+)|PIC(?:TURE)?\s+(\S+)", text, re.IGNORECASE)
        if pic_match:
            pic = pic_match.group(1) or pic_match.group(2)

        item = DataItem(
            name=name,
            level=level,
            location=location,
            pic=pic,
        )

        self.current_section.data_items.append(item)
        return self.visitChildren(ctx)

    def _extract_performs(self, ctx) -> list[str]:
        """Extract PERFORM targets from paragraph."""
        performs = []
        text = ctx.getText().upper()

        import re
        # Pattern for PERFORM paragraph-name
        for match in re.finditer(r"PERFORM\s+([A-Z][A-Z0-9-]*)", text):
            target = match.group(1)
            if target not in ("UNTIL", "VARYING", "TIMES", "WITH", "TEST"):
                performs.append(target)

        return performs

    def _extract_calls(self, ctx) -> list[str]:
        """Extract CALL targets from paragraph."""
        calls = []
        text = ctx.getText().upper()

        import re
        # Pattern for CALL 'program-name' or CALL identifier
        for match in re.finditer(r"CALL\s+['\"]?([A-Z][A-Z0-9-]*)['\"]?", text):
            calls.append(match.group(1))

        return calls


class CobolParser:
    """
    Main COBOL parser.

    Provides:
    - Full ANTLR parsing for accurate AST
    - Fast structural indexing for large files
    - Copybook preprocessing
    """

    def __init__(
        self,
        copybook_paths: Optional[list[Path]] = None,
        use_indexer_only: bool = False,
    ):
        """
        Initialize parser.

        Args:
            copybook_paths: Paths to search for copybooks
            use_indexer_only: Only use fast indexer, skip full ANTLR parse
        """
        self.preprocessor = Preprocessor(copybook_paths)
        self.indexer = StructuralIndexer()
        self.use_indexer_only = use_indexer_only
        self.debug = False

    def add_copybook_path(self, path: Path) -> None:
        """Add copybook search path."""
        self.preprocessor.add_copybook_path(path)

    def parse_file(self, path: Path) -> CobolProgram:
        """
        Parse COBOL file.

        Args:
            path: Path to COBOL source file

        Returns:
            CobolProgram AST
        """
        source = path.read_text()
        return self.parse(source, path)

    def parse(
        self,
        source: str,
        path: Optional[Path] = None,
        preprocess: bool = True,
    ) -> CobolProgram:
        """
        Parse COBOL source code.

        Args:
            source: COBOL source code
            path: Optional path for copybook resolution
            preprocess: Whether to preprocess (resolve copybooks)

        Returns:
            CobolProgram AST
        """
        # Compute source hash
        source_hash = hashlib.sha256(source.encode()).hexdigest()

        # Preprocess
        copybook_refs: list[CopybookRef] = []
        if preprocess:
            result = self.preprocessor.preprocess(source, path)
            source = result.source
            copybook_refs = result.copybook_refs

        # Split into lines for body extraction
        source_lines = source.split("\n")
        total_lines = len(source_lines)

        # Extract program ID from source
        program_id = self._extract_program_id(source)

        if self.use_indexer_only:
            # Fast path: use structural indexer only
            return self._parse_with_indexer(
                source, source_lines, path, source_hash, program_id, copybook_refs
            )

        # Full ANTLR parse
        return self._parse_with_antlr(
            source, source_lines, path, source_hash, program_id, copybook_refs
        )

    def _parse_with_antlr(
        self,
        source: str,
        source_lines: list[str],
        path: Optional[Path],
        source_hash: str,
        program_id: str,
        copybook_refs: list[CopybookRef],
    ) -> CobolProgram:
        """Parse using full ANTLR parser."""
        # Create ANTLR input stream
        input_stream = InputStream(source)

        # Create lexer
        lexer = Cobol85Lexer(input_stream)
        lexer.removeErrorListeners()
        error_listener = CoquErrorListener()
        lexer.addErrorListener(error_listener)

        # Create token stream
        stream = CommonTokenStream(lexer)

        # Create parser
        parser = Cobol85Parser(stream)
        parser.removeErrorListeners()
        parser.addErrorListener(error_listener)

        # Parse
        tree = parser.startRule()

        # Check for errors
        if error_listener.errors:
            if self.debug:
                for err in error_listener.errors:
                    print(f"Parse error: {err}")
            # Fall back to indexer on parse error
            return self._parse_with_indexer(
                source, source_lines, path, source_hash, program_id, copybook_refs
            )

        # Extract AST using visitor
        visitor = CobolASTVisitor(source_lines)
        visitor.visit(tree)

        # Build program
        program = CobolProgram(
            program_id=program_id,
            source_path=path,
            source_hash=source_hash,
            lines=len(source_lines),
            divisions=visitor.divisions,
            copybook_refs=copybook_refs,
            comments=visitor.comments,
            source_lines=source_lines,
        )

        return program

    def _parse_with_indexer(
        self,
        source: str,
        source_lines: list[str],
        path: Optional[Path],
        source_hash: str,
        program_id: str,
        copybook_refs: list[CopybookRef],
    ) -> CobolProgram:
        """Parse using fast structural indexer."""
        index = self.indexer.index(source)

        # Convert index to AST
        divisions: list[Division] = []

        for div_entry in index.divisions:
            div = Division(
                name=div_entry.name,
                location=SourceLocation(
                    line_start=div_entry.line_start,
                    line_end=div_entry.line_end,
                ),
            )
            divisions.append(div)

        # Add sections to divisions
        for sec_entry in index.sections:
            # Find containing division
            for div in divisions:
                if div.location.line_start <= sec_entry.line_start <= div.location.line_end:
                    section = Section(
                        name=sec_entry.name,
                        location=SourceLocation(
                            line_start=sec_entry.line_start,
                            line_end=sec_entry.line_end,
                        ),
                    )
                    div.sections.append(section)
                    break

        # Add paragraphs to PROCEDURE DIVISION
        proc_div = None
        for div in divisions:
            if "PROCEDURE" in div.name:
                proc_div = div
                break

        if proc_div:
            for para_entry in index.paragraphs:
                para = Paragraph(
                    name=para_entry.name,
                    location=SourceLocation(
                        line_start=para_entry.line_start,
                        line_end=para_entry.line_end,
                    ),
                )
                # Find containing section
                added_to_section = False
                for section in proc_div.sections:
                    if section.location.line_start <= para_entry.line_start <= section.location.line_end:
                        section.paragraphs.append(para)
                        added_to_section = True
                        break

                if not added_to_section:
                    proc_div.paragraphs.append(para)

        # Add data items from index
        data_div = None
        for div in divisions:
            if "DATA" in div.name:
                data_div = div
                break

        if data_div:
            # Create WORKING-STORAGE section if we have level-01 items
            if index.data_items_01:
                ws_section = None
                for section in data_div.sections:
                    if "WORKING-STORAGE" in section.name:
                        ws_section = section
                        break

                if not ws_section:
                    ws_section = Section(
                        name="WORKING-STORAGE SECTION",
                        location=SourceLocation(line_start=0, line_end=0),
                    )
                    data_div.sections.append(ws_section)

                for item_entry in index.data_items_01:
                    item = DataItem(
                        name=item_entry.name,
                        level=1,
                        location=SourceLocation(
                            line_start=item_entry.line_start,
                            line_end=item_entry.line_end,
                        ),
                    )
                    ws_section.data_items.append(item)

        program = CobolProgram(
            program_id=program_id,
            source_path=path,
            source_hash=source_hash,
            lines=len(source_lines),
            divisions=divisions,
            copybook_refs=copybook_refs,
            comments=[],
            source_lines=source_lines,
        )

        return program

    def _extract_program_id(self, source: str) -> str:
        """Extract PROGRAM-ID from source."""
        import re
        match = re.search(
            r"PROGRAM-ID\s*[.\s]+([A-Z][A-Z0-9-]*)",
            source,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).upper()
        return "UNKNOWN"

    def index_only(self, source: str) -> StructuralIndex:
        """Get structural index only (fast)."""
        return self.indexer.index(source)
