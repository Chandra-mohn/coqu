# tests/test_parser.py - Parser tests
"""
Tests for the COBOL parser.
"""
import pytest
from pathlib import Path

from coqu.parser import CobolParser, StructuralIndexer
from coqu.parser.ast import CobolProgram


# Fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_CBL = FIXTURES_DIR / "sample.cbl"
CALLER_CBL = FIXTURES_DIR / "caller.cbl"
MAINFRAME_CBL = FIXTURES_DIR / "mainframe.cbl"


class TestStructuralIndexer:
    """Tests for the fast structural indexer."""

    def test_index_divisions(self):
        """Test that indexer finds all divisions."""
        source = SAMPLE_CBL.read_text()
        indexer = StructuralIndexer()
        index = indexer.index(source)

        division_names = index.get_division_names()
        assert "IDENTIFICATION DIVISION" in division_names
        assert "ENVIRONMENT DIVISION" in division_names
        assert "DATA DIVISION" in division_names
        assert "PROCEDURE DIVISION" in division_names

    def test_index_sections(self):
        """Test that indexer finds sections."""
        source = SAMPLE_CBL.read_text()
        indexer = StructuralIndexer()
        index = indexer.index(source)

        section_names = index.get_section_names()
        assert any("FILE" in s for s in section_names)
        assert any("WORKING-STORAGE" in s for s in section_names)

    def test_index_paragraphs(self):
        """Test that indexer finds paragraphs."""
        source = SAMPLE_CBL.read_text()
        indexer = StructuralIndexer()
        index = indexer.index(source)

        para_names = index.get_paragraph_names()
        assert "0000-MAIN-PARA" in para_names
        assert "1000-INIT-PARA" in para_names
        assert "2100-VALIDATE" in para_names

    def test_index_copybooks(self):
        """Test that indexer finds COPY statements."""
        source = SAMPLE_CBL.read_text()
        indexer = StructuralIndexer()
        index = indexer.index(source)

        copybook_names = [c.name for c in index.copybooks]
        assert "DATEUTIL" in copybook_names

    def test_index_data_items(self):
        """Test that indexer finds level-01 items."""
        source = SAMPLE_CBL.read_text()
        indexer = StructuralIndexer()
        index = indexer.index(source)

        item_names = [i.name for i in index.data_items_01]
        assert "WS-VARIABLES" in item_names
        assert "WS-CONSTANTS" in item_names


class TestMainframeFormat:
    """Tests for mainframe-format COBOL with sequence numbers."""

    def test_index_mainframe_divisions(self):
        """Test indexer finds divisions in mainframe format."""
        source = MAINFRAME_CBL.read_text()
        indexer = StructuralIndexer()
        index = indexer.index(source)

        division_names = index.get_division_names()
        assert "IDENTIFICATION DIVISION" in division_names
        assert "ENVIRONMENT DIVISION" in division_names
        assert "DATA DIVISION" in division_names
        assert "PROCEDURE DIVISION" in division_names

    def test_index_mainframe_paragraphs(self):
        """Test indexer finds paragraphs in mainframe format."""
        source = MAINFRAME_CBL.read_text()
        indexer = StructuralIndexer()
        index = indexer.index(source)

        para_names = index.get_paragraph_names()
        assert "0000-MAIN" in para_names
        assert "1000-INITIALIZE" in para_names
        assert "2100-VALIDATE" in para_names
        assert "2200-UPDATE-DB" in para_names
        assert "9000-TERMINATE" in para_names

    def test_index_mainframe_sections(self):
        """Test indexer finds sections in mainframe format."""
        source = MAINFRAME_CBL.read_text()
        indexer = StructuralIndexer()
        index = indexer.index(source)

        section_names = index.get_section_names()
        assert any("WORKING-STORAGE" in s for s in section_names)
        assert any("LINKAGE" in s for s in section_names)

    def test_index_mainframe_copybooks(self):
        """Test indexer finds COPY statements in mainframe format."""
        source = MAINFRAME_CBL.read_text()
        indexer = StructuralIndexer()
        index = indexer.index(source)

        copybook_names = [c.name for c in index.copybooks]
        assert "COMAREA" in copybook_names

    def test_parse_mainframe_file(self):
        """Test full parsing of mainframe format file."""
        parser = CobolParser(use_indexer_only=True)
        program = parser.parse_file(MAINFRAME_CBL)

        assert program.program_id == "MAINFRAME"
        assert len(program.divisions) == 4
        assert len(program.get_all_paragraphs()) >= 5


class TestCobolParser:
    """Tests for the main COBOL parser."""

    def test_parse_file(self):
        """Test parsing a file."""
        parser = CobolParser(use_indexer_only=True)
        program = parser.parse_file(SAMPLE_CBL)

        assert program.program_id == "SAMPLE"
        assert program.lines > 0
        assert len(program.divisions) == 4

    def test_parse_with_copybook_path(self):
        """Test parsing with copybook resolution."""
        parser = CobolParser(
            copybook_paths=[FIXTURES_DIR],
            use_indexer_only=True,
        )
        program = parser.parse_file(SAMPLE_CBL)

        # Check copybook was found
        assert len(program.copybook_refs) > 0
        dateutil_ref = next(
            (r for r in program.copybook_refs if r.name == "DATEUTIL"),
            None,
        )
        assert dateutil_ref is not None
        assert dateutil_ref.status == "resolved"

    def test_extract_program_id(self):
        """Test PROGRAM-ID extraction."""
        parser = CobolParser(use_indexer_only=True)

        # Test with sample
        program = parser.parse_file(SAMPLE_CBL)
        assert program.program_id == "SAMPLE"

        # Test with caller
        program = parser.parse_file(CALLER_CBL)
        assert program.program_id == "CALLER"

    def test_get_division(self):
        """Test getting divisions by name."""
        parser = CobolParser(use_indexer_only=True)
        program = parser.parse_file(SAMPLE_CBL)

        proc_div = program.get_division("PROCEDURE")
        assert proc_div is not None
        assert "PROCEDURE" in proc_div.name

        data_div = program.get_division("DATA")
        assert data_div is not None
        assert "DATA" in data_div.name

    def test_get_all_paragraphs(self):
        """Test getting all paragraphs."""
        parser = CobolParser(use_indexer_only=True)
        program = parser.parse_file(SAMPLE_CBL)

        paragraphs = program.get_all_paragraphs()
        assert len(paragraphs) > 0

        para_names = [p.name for p in paragraphs]
        assert "0000-MAIN-PARA" in para_names
        assert "2100-VALIDATE" in para_names

    def test_get_paragraph(self):
        """Test getting specific paragraph."""
        parser = CobolParser(use_indexer_only=True)
        program = parser.parse_file(SAMPLE_CBL)

        para = program.get_paragraph("2100-VALIDATE")
        assert para is not None
        assert para.name == "2100-VALIDATE"

    def test_get_working_storage_items(self):
        """Test getting WORKING-STORAGE items."""
        parser = CobolParser(use_indexer_only=True)
        program = parser.parse_file(SAMPLE_CBL)

        items = program.get_working_storage_items()
        assert len(items) > 0

    def test_source_hash(self):
        """Test that source hash is computed."""
        parser = CobolParser(use_indexer_only=True)
        program = parser.parse_file(SAMPLE_CBL)

        assert program.source_hash
        assert len(program.source_hash) == 64  # SHA256 hex


class TestPreprocessor:
    """Tests for the preprocessor."""

    def test_find_copy_statements(self):
        """Test finding COPY statements."""
        from coqu.parser.preprocessor import Preprocessor

        preprocessor = Preprocessor()
        source = SAMPLE_CBL.read_text()
        result = preprocessor.preprocess(source, SAMPLE_CBL, resolve_copybooks=False)

        assert len(result.copybook_refs) > 0
        assert any(r.name == "DATEUTIL" for r in result.copybook_refs)

    def test_resolve_copybooks(self):
        """Test resolving copybooks."""
        from coqu.parser.preprocessor import Preprocessor

        preprocessor = Preprocessor([FIXTURES_DIR])
        source = SAMPLE_CBL.read_text()
        result = preprocessor.preprocess(source, SAMPLE_CBL)

        dateutil_ref = next(
            (r for r in result.copybook_refs if r.name == "DATEUTIL"),
            None,
        )
        assert dateutil_ref is not None
        assert dateutil_ref.status == "resolved"
        assert dateutil_ref.resolved_path is not None


class TestASTSerialization:
    """Tests for AST serialization."""

    def test_to_dict_from_dict(self):
        """Test round-trip serialization."""
        parser = CobolParser(use_indexer_only=True)
        program = parser.parse_file(SAMPLE_CBL)

        # Convert to dict and back
        data = program.to_dict()
        restored = CobolProgram.from_dict(data)

        assert restored.program_id == program.program_id
        assert restored.lines == program.lines
        assert len(restored.divisions) == len(program.divisions)
