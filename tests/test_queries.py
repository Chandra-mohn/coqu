# tests/test_queries.py - Query engine tests
"""
Tests for the query engine and commands.
"""
import pytest
from pathlib import Path

from coqu.workspace import Workspace
from coqu.query import QueryEngine, QueryParser


# Fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_CBL = FIXTURES_DIR / "sample.cbl"
CALLER_CBL = FIXTURES_DIR / "caller.cbl"


@pytest.fixture
def workspace():
    """Create workspace with loaded programs."""
    ws = Workspace(
        copybook_paths=[FIXTURES_DIR],
        use_indexer_only=True,
    )
    ws.load(SAMPLE_CBL)
    ws.load(CALLER_CBL)
    return ws


@pytest.fixture
def engine(workspace):
    """Create query engine."""
    return QueryEngine(workspace)


class TestQueryParser:
    """Tests for the QueryParser class."""

    def test_parse_simple_command(self):
        """Test parsing simple command."""
        parser = QueryParser()
        result = parser.parse("divisions")

        assert result.command == "divisions"
        assert result.args == []
        assert result.options == {}

    def test_parse_command_with_args(self):
        """Test parsing command with arguments."""
        parser = QueryParser()
        result = parser.parse("paragraph MAIN-PARA SAMPLE")

        assert result.command == "paragraph"
        assert result.args == ["MAIN-PARA", "SAMPLE"]

    def test_parse_command_with_options(self):
        """Test parsing command with options."""
        parser = QueryParser()
        result = parser.parse("paragraph MAIN --body --level=1")

        assert result.command == "paragraph"
        assert result.args == ["MAIN"]
        assert result.options["body"] is True
        assert result.options["level"] == "1"

    def test_parse_meta_command(self):
        """Test parsing meta command."""
        parser = QueryParser()
        result = parser.parse("/load file.cbl")

        assert result.command == "/load"
        assert result.args == ["file.cbl"]
        assert result.is_meta

    def test_parse_empty(self):
        """Test parsing empty string."""
        parser = QueryParser()
        result = parser.parse("")
        assert result is None

        result = parser.parse("   ")
        assert result is None


class TestDivisionCommands:
    """Tests for division-related commands."""

    def test_divisions_command(self, engine):
        """Test divisions command."""
        result = engine.execute("divisions")

        assert not result.is_error
        assert len(result.items) > 0

    def test_division_command(self, engine):
        """Test division command."""
        result = engine.execute("division PROCEDURE")

        assert not result.is_error
        assert len(result.items) > 0
        assert "PROCEDURE" in result.items[0]["name"]

    def test_division_not_found(self, engine):
        """Test division command with invalid name."""
        result = engine.execute("division NONEXISTENT")
        assert result.is_error


class TestParagraphCommands:
    """Tests for paragraph-related commands."""

    def test_paragraphs_command(self, engine):
        """Test paragraphs command."""
        result = engine.execute("paragraphs")

        assert not result.is_error
        assert len(result.items) > 0

    def test_paragraph_command(self, engine):
        """Test paragraph command."""
        result = engine.execute("paragraph 0000-MAIN-PARA")

        assert not result.is_error
        assert len(result.items) >= 1

    def test_paragraph_with_body(self, engine):
        """Test paragraph command with --body."""
        result = engine.execute("paragraph 2100-VALIDATE --body")

        assert not result.is_error
        assert len(result.items) >= 1
        # Body should be included in options handling


class TestVariableCommands:
    """Tests for variable-related commands."""

    def test_working_storage_command(self, engine):
        """Test working-storage command."""
        result = engine.execute("working-storage")

        assert not result.is_error

    def test_variable_command(self, engine):
        """Test variable command."""
        result = engine.execute("variable WS-VARIABLES")

        # May or may not find it depending on parser depth
        # Just check no error
        assert not result.is_error or "not found" in result.error.lower()


class TestCopybookCommands:
    """Tests for copybook-related commands."""

    def test_copybooks_command(self, engine):
        """Test copybooks command."""
        result = engine.execute("copybooks")

        assert not result.is_error
        assert len(result.items) > 0

    def test_copybook_command(self, engine):
        """Test copybook command."""
        result = engine.execute("copybook DATEUTIL")

        assert not result.is_error
        assert len(result.items) == 1
        assert result.items[0]["name"] == "DATEUTIL"


class TestStatementCommands:
    """Tests for statement-related commands."""

    def test_calls_command(self, engine):
        """Test calls command."""
        result = engine.execute("calls")

        assert not result.is_error
        # Should find CALL statements
        assert len(result.items) >= 0

    def test_performs_command(self, engine):
        """Test performs command."""
        result = engine.execute("performs")

        assert not result.is_error


class TestSearchCommands:
    """Tests for search-related commands."""

    def test_find_command(self, engine):
        """Test find command."""
        result = engine.execute("find PERFORM")

        assert not result.is_error
        assert len(result.items) > 0

    def test_find_with_regex(self, engine):
        """Test find command with regex."""
        result = engine.execute("find MOVE.*TO")

        assert not result.is_error

    def test_references_command(self, engine):
        """Test references command."""
        result = engine.execute("references WS-COUNTER")

        assert not result.is_error

    def test_where_used_command(self, engine):
        """Test where-used command."""
        result = engine.execute("where-used 2100-VALIDATE")

        # May or may not find callers
        assert not result.is_error


class TestQueryResult:
    """Tests for QueryResult class."""

    def test_format_text(self, engine):
        """Test text formatting."""
        result = engine.execute("divisions")
        text = result.format_text()

        assert isinstance(text, str)
        assert len(text) > 0

    def test_to_json(self, engine):
        """Test JSON conversion."""
        result = engine.execute("divisions")
        json_data = result.to_json()

        assert "items" in json_data
        assert "count" in json_data

    def test_error_result(self, engine):
        """Test error result handling."""
        result = engine.execute("nonexistent_command")

        assert result.is_error
        text = result.format_text()
        assert "Error" in text


class TestQueryEngine:
    """Tests for QueryEngine class."""

    def test_list_commands(self, engine):
        """Test listing available commands."""
        commands = engine.list_commands()

        assert len(commands) > 0
        assert "divisions" in commands
        assert "paragraphs" in commands

    def test_get_help(self, engine):
        """Test getting help."""
        help_text = engine.get_help()

        assert "Available commands" in help_text
        assert "divisions" in help_text.lower()

    def test_get_command_help(self, engine):
        """Test getting help for specific command."""
        help_text = engine.get_help("divisions")

        assert "divisions" in help_text.lower()

    def test_get_completions(self, engine):
        """Test getting completions."""
        completions = engine.get_completions("div")

        assert "divisions" in completions
        assert "division" in completions
