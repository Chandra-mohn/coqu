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


class TestFormatNormalization:
    """Tests for source format detection and normalization."""

    def test_detect_panvalet_format(self):
        """Test detection of Panvalet format."""
        from coqu.parser.preprocessor import Preprocessor

        preprocessor = Preprocessor()

        panvalet_source = """1.1    IDENTIFICATION DIVISION.
1.2    PROGRAM-ID. TEST.
1.3    PROCEDURE DIVISION.
1.4    MAIN-PARA.
1.5        STOP RUN.
"""
        assert preprocessor.detect_format(panvalet_source) == "panvalet"

    def test_detect_standard_format(self):
        """Test detection of standard format."""
        from coqu.parser.preprocessor import Preprocessor

        preprocessor = Preprocessor()

        standard_source = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        assert preprocessor.detect_format(standard_source) == "standard"

    def test_detect_sequence_format(self):
        """Test detection of sequence number format."""
        from coqu.parser.preprocessor import Preprocessor

        preprocessor = Preprocessor()

        sequence_source = """000100 IDENTIFICATION DIVISION.
000200 PROGRAM-ID. TEST.
000300 PROCEDURE DIVISION.
000400 MAIN-PARA.
000500     STOP RUN.
"""
        assert preprocessor.detect_format(sequence_source) == "sequence"

    def test_normalize_panvalet(self):
        """Test normalization of Panvalet format."""
        from coqu.parser.preprocessor import Preprocessor

        preprocessor = Preprocessor()

        panvalet_source = """1.1    IDENTIFICATION DIVISION.
1.2    PROGRAM-ID. TEST.
"""
        normalized = preprocessor.normalize_format(panvalet_source, "panvalet")

        # Should have 6 spaces prefix instead of version markers
        lines = normalized.split('\n')
        assert lines[0].startswith('      ')
        assert 'IDENTIFICATION DIVISION' in lines[0]

    def test_preprocess_normalizes_panvalet(self):
        """Test that preprocessing auto-normalizes Panvalet format."""
        from coqu.parser.preprocessor import Preprocessor

        preprocessor = Preprocessor()

        panvalet_source = """1.1    IDENTIFICATION DIVISION.
1.2    PROGRAM-ID. TESTPROG.
1.3    PROCEDURE DIVISION.
1.4    MAIN-PARA.
1.5        STOP RUN.
"""
        result = preprocessor.preprocess(panvalet_source)

        assert result.format_detected == "panvalet"
        assert result.was_normalized is True
        assert result.source.startswith('      ')

    def test_parse_panvalet_format(self):
        """Test full parsing of Panvalet format file."""
        panvalet_source = """1.1    IDENTIFICATION DIVISION.
1.2    PROGRAM-ID. TESTPROG.
1.3    DATA DIVISION.
1.4    WORKING-STORAGE SECTION.
1.5    01 WS-VAR PIC X(10).
1.6    PROCEDURE DIVISION.
1.7    MAIN-PARA.
1.8        DISPLAY 'HELLO'.
1.9        STOP RUN.
"""
        parser = CobolParser()
        program = parser.parse(panvalet_source)

        assert program.program_id == "TESTPROG"
        assert len(program.divisions) >= 3


class TestChunkAnalyzer:
    """Tests for chunk-based semantic analysis."""

    def test_extract_performs(self):
        """Test PERFORM extraction from chunk."""
        from coqu.parser.chunk_analyzer import ChunkAnalyzer

        analyzer = ChunkAnalyzer()

        chunk = """
       MAIN-PARA.
           PERFORM INIT-PARA.
           PERFORM PROCESS-PARA THRU PROCESS-EXIT.
           PERFORM VALIDATE UNTIL WS-DONE = 'Y'.
           STOP RUN.
"""
        result = analyzer.analyze(chunk)

        assert "INIT-PARA" in result.performs
        assert "PROCESS-PARA" in result.performs
        assert "PROCESS-EXIT" in result.performs
        assert "VALIDATE" in result.performs
        # Keywords should not be included
        assert "UNTIL" not in result.performs
        assert "THRU" not in result.performs

    def test_extract_calls(self):
        """Test CALL extraction from chunk."""
        from coqu.parser.chunk_analyzer import ChunkAnalyzer

        analyzer = ChunkAnalyzer()

        chunk = """
       CALL-PARA.
           CALL 'SUBPROG1' USING WS-DATA.
           CALL "SUBPROG2".
           CALL WS-PROGRAM-NAME USING BY REFERENCE WS-AREA.
"""
        result = analyzer.analyze(chunk)

        assert "SUBPROG1" in result.calls
        assert "SUBPROG2" in result.calls
        assert "WS-PROGRAM-NAME" in result.calls

    def test_extract_moves(self):
        """Test MOVE extraction from chunk."""
        from coqu.parser.chunk_analyzer import ChunkAnalyzer

        analyzer = ChunkAnalyzer()

        chunk = """
       INIT-PARA.
           MOVE SPACES TO WS-OUTPUT.
           MOVE 'Y' TO WS-FLAG.
           MOVE CORRESPONDING WS-INPUT TO WS-OUTPUT.
"""
        result = analyzer.analyze(chunk)

        assert ("SPACES", "WS-OUTPUT") in result.moves
        assert ("'Y'", "WS-FLAG") in result.moves

    def test_extract_gotos(self):
        """Test GO TO extraction from chunk."""
        from coqu.parser.chunk_analyzer import ChunkAnalyzer

        analyzer = ChunkAnalyzer()

        chunk = """
       ERROR-PARA.
           IF WS-ERROR = 'Y'
               GO TO ERROR-EXIT
           END-IF.
"""
        result = analyzer.analyze(chunk)

        # GO TO targets should be in performs list
        assert "ERROR-EXIT" in result.performs

    def test_program_analyze_paragraph(self):
        """Test analyze_paragraph method on CobolProgram."""
        parser = CobolParser(use_indexer_only=True)
        program = parser.parse_file(SAMPLE_CBL)

        # Analyze a paragraph
        result = program.analyze_paragraph("0000-MAIN-PARA")

        assert result is not None
        assert result["name"] == "0000-MAIN-PARA"
        assert "performs" in result
        assert "calls" in result

    def test_chunk_analysis_speed(self):
        """Test that chunk analysis is fast."""
        import time
        from coqu.parser.chunk_analyzer import ChunkAnalyzer

        analyzer = ChunkAnalyzer()

        # Simulate a large chunk (100 lines)
        chunk = "\n".join([
            f"       MOVE WS-VAR-{i} TO WS-OUTPUT-{i}."
            for i in range(100)
        ])

        start = time.perf_counter()
        for _ in range(100):  # 100 iterations
            analyzer.analyze(chunk)
        elapsed = time.perf_counter() - start

        # Should complete 100 analyses in under 1 second
        assert elapsed < 1.0, f"Chunk analysis too slow: {elapsed:.3f}s"


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
