# coqu.query.engine - Query execution engine
"""
Dispatches queries to command handlers.
"""
from typing import Optional

from coqu.query.parser import QueryParser, ParsedQuery
from coqu.query.commands.base import Command, QueryResult
from coqu.query.commands.divisions import DivisionsCommand, DivisionCommand
from coqu.query.commands.sections import SectionsCommand, SectionCommand, ProcedureSectionsCommand
from coqu.query.commands.paragraphs import ParagraphsCommand, ParagraphCommand
from coqu.query.commands.variables import (
    WorkingStorageCommand,
    VariableCommand,
    FileSectionCommand,
    LinkageCommand,
)
from coqu.query.commands.copybooks import CopybooksCommand, CopybookCommand, CopybookDepsCommand
from coqu.query.commands.statements import (
    CallsCommand,
    PerformsCommand,
    MovesCommand,
    SqlCommand,
    CicsCommand,
)
from coqu.query.commands.search import FindCommand, ReferencesCommand, WhereUsedCommand


class QueryEngine:
    """
    Executes queries against the workspace.

    Manages command registration and dispatch.
    """

    def __init__(self, workspace):
        """
        Initialize query engine.

        Args:
            workspace: The workspace to query
        """
        self.workspace = workspace
        self.parser = QueryParser()
        self.commands: dict[str, Command] = {}

        # Register built-in commands
        self._register_builtin_commands()

    def _register_builtin_commands(self) -> None:
        """Register all built-in commands."""
        commands = [
            # Divisions
            DivisionsCommand(),
            DivisionCommand(),
            # Sections
            SectionsCommand(),
            SectionCommand(),
            ProcedureSectionsCommand(),
            # Paragraphs
            ParagraphsCommand(),
            ParagraphCommand(),
            # Variables
            WorkingStorageCommand(),
            VariableCommand(),
            FileSectionCommand(),
            LinkageCommand(),
            # Copybooks
            CopybooksCommand(),
            CopybookCommand(),
            CopybookDepsCommand(),
            # Statements
            CallsCommand(),
            PerformsCommand(),
            MovesCommand(),
            SqlCommand(),
            CicsCommand(),
            # Search
            FindCommand(),
            ReferencesCommand(),
            WhereUsedCommand(),
        ]

        for cmd in commands:
            self.register(cmd)

    def register(self, command: Command) -> None:
        """
        Register a command.

        Args:
            command: The command to register
        """
        self.commands[command.name] = command
        for alias in command.aliases:
            self.commands[alias] = command

    def execute(self, query: str) -> QueryResult:
        """
        Execute a query string.

        Args:
            query: The query string

        Returns:
            QueryResult
        """
        parsed = self.parser.parse(query)
        if not parsed:
            return QueryResult(error="Empty query")

        return self.execute_parsed(parsed)

    def execute_parsed(self, parsed: ParsedQuery) -> QueryResult:
        """
        Execute a parsed query.

        Args:
            parsed: The parsed query

        Returns:
            QueryResult
        """
        # Get command
        cmd = self.commands.get(parsed.command)
        if not cmd:
            return QueryResult(error=f"Unknown command: {parsed.command}")

        try:
            return cmd.execute(self.workspace, parsed.args, parsed.options)
        except Exception as e:
            return QueryResult(error=f"Command failed: {e}")

    def get_command(self, name: str) -> Optional[Command]:
        """
        Get a command by name.

        Args:
            name: Command name or alias

        Returns:
            Command or None
        """
        return self.commands.get(name)

    def list_commands(self) -> list[str]:
        """Get list of unique command names."""
        seen = set()
        names = []
        for name, cmd in self.commands.items():
            if cmd.name not in seen:
                seen.add(cmd.name)
                names.append(cmd.name)
        return sorted(names)

    def get_help(self, command: Optional[str] = None) -> str:
        """
        Get help text.

        Args:
            command: Optional command name for specific help

        Returns:
            Help text
        """
        if command:
            cmd = self.commands.get(command)
            if cmd:
                return cmd.get_help()
            return f"Unknown command: {command}"

        # List all commands
        lines = ["Available commands:", ""]

        # Group by category
        categories = {
            "Divisions": ["divisions", "division"],
            "Sections": ["sections", "section", "procedure-sections"],
            "Paragraphs": ["paragraphs", "paragraph"],
            "Variables": ["working-storage", "variable", "file-section", "linkage"],
            "Copybooks": ["copybooks", "copybook", "copybook-deps"],
            "Statements": ["calls", "performs", "moves", "sql", "cics"],
            "Search": ["find", "references", "where-used"],
        }

        for category, cmds in categories.items():
            lines.append(f"{category}:")
            for name in cmds:
                cmd = self.commands.get(name)
                if cmd:
                    aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
                    lines.append(f"  {name}{aliases} - {cmd.help}")
            lines.append("")

        lines.append("Use 'help <command>' for detailed help on a command.")

        return "\n".join(lines)

    def get_completions(self, text: str) -> list[str]:
        """
        Get command completions for text.

        Args:
            text: Current input text

        Returns:
            List of possible completions
        """
        if not text:
            return self.list_commands()

        # Filter commands by prefix
        text_lower = text.lower()
        return [name for name in self.list_commands() if name.startswith(text_lower)]
