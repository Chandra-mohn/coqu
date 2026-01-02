# coqu.query.commands.base - Base command class and result
"""
Base classes for query commands.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class QueryResult:
    """
    Result of a query command execution.

    Provides multiple output formats for different contexts.
    """
    items: list[Any] = field(default_factory=list)
    message: str = ""
    error: Optional[str] = None
    count: int = 0

    def __post_init__(self):
        if not self.count:
            self.count = len(self.items)

    @property
    def is_error(self) -> bool:
        """Check if result is an error."""
        return self.error is not None

    @property
    def is_empty(self) -> bool:
        """Check if result has no items."""
        return len(self.items) == 0

    def format_text(self, include_body: bool = False) -> str:
        """
        Format result as text for terminal display.

        Args:
            include_body: Include source code body in output

        Returns:
            Formatted text string
        """
        if self.error:
            return f"Error: {self.error}"

        if self.message:
            lines = [self.message]
        else:
            lines = []

        if not self.items:
            if not self.message:
                lines.append("No results found.")
            return "\n".join(lines)

        for item in self.items:
            if hasattr(item, "format_text"):
                lines.append(item.format_text(include_body))
            elif isinstance(item, dict):
                lines.append(self._format_dict(item, include_body))
            elif isinstance(item, str):
                lines.append(item)
            else:
                lines.append(str(item))

        if self.count > 0:
            lines.append(f"\n({self.count} result{'s' if self.count != 1 else ''})")

        return "\n".join(lines)

    def _format_dict(self, data: dict, include_body: bool = False) -> str:
        """Format a dictionary item."""
        lines = []

        name = data.get("name", "")
        if name:
            lines.append(f"  {name}")

        location = data.get("location") or data.get("line")
        if location:
            lines.append(f"    Location: {location}")

        for key, value in data.items():
            if key in ("name", "location", "line", "body"):
                continue
            if value is not None:
                lines.append(f"    {key}: {value}")

        if include_body and data.get("body"):
            lines.append("    --- Body ---")
            for line in data["body"].split("\n"):
                lines.append(f"    {line}")
            lines.append("    --- End ---")

        return "\n".join(lines)

    def to_json(self) -> dict:
        """
        Convert result to JSON-serializable dict.

        Returns:
            Dictionary for JSON encoding
        """
        result = {
            "count": self.count,
            "items": [],
        }

        if self.error:
            result["error"] = self.error

        if self.message:
            result["message"] = self.message

        for item in self.items:
            if hasattr(item, "to_dict"):
                result["items"].append(item.to_dict())
            elif isinstance(item, dict):
                result["items"].append(item)
            else:
                result["items"].append(str(item))

        return result


class Command(ABC):
    """
    Base class for query commands.

    Subclasses implement specific query logic.
    """

    # Command name (e.g., "divisions", "paragraphs")
    name: str = ""

    # Command aliases
    aliases: list[str] = []

    # Help text
    help: str = ""

    # Usage example
    usage: str = ""

    @abstractmethod
    def execute(
        self,
        workspace,
        args: list[str],
        options: dict,
    ) -> QueryResult:
        """
        Execute the command.

        Args:
            workspace: The workspace to query
            args: Command arguments
            options: Command options (--body, --level, etc.)

        Returns:
            QueryResult with matching items
        """
        pass

    def get_help(self) -> str:
        """Get help text for the command."""
        lines = [f"{self.name}"]

        if self.aliases:
            lines[0] += f" (aliases: {', '.join(self.aliases)})"

        if self.help:
            lines.append(f"  {self.help}")

        if self.usage:
            lines.append(f"  Usage: {self.usage}")

        return "\n".join(lines)

    def parse_options(self, args: list[str]) -> tuple[list[str], dict]:
        """
        Parse options from arguments.

        Extracts --option and --option=value from args.

        Args:
            args: Raw arguments

        Returns:
            Tuple of (remaining_args, options_dict)
        """
        remaining = []
        options = {}

        for arg in args:
            if arg.startswith("--"):
                if "=" in arg:
                    key, value = arg[2:].split("=", 1)
                    options[key] = value
                else:
                    options[arg[2:]] = True
            else:
                remaining.append(arg)

        return remaining, options
