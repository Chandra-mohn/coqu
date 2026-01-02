# coqu.query.parser - Query command parser
"""
Parses query strings into command and arguments.
"""
import shlex
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedQuery:
    """Parsed query with command, args, and options."""
    command: str
    args: list[str]
    options: dict[str, str | bool]
    raw: str

    @property
    def is_meta(self) -> bool:
        """Check if this is a meta command (starts with /)."""
        return self.command.startswith("/")


class QueryParser:
    """
    Parses query strings.

    Query format:
    - Regular query: command arg1 arg2 --option --key=value
    - Meta command: /command arg1 arg2

    Examples:
    - "divisions" -> command="divisions", args=[], options={}
    - "paragraph MAIN --body" -> command="paragraph", args=["MAIN"], options={"body": True}
    - "/load file.cbl" -> command="/load", args=["file.cbl"], options={}
    """

    def parse(self, query: str) -> Optional[ParsedQuery]:
        """
        Parse a query string.

        Args:
            query: The query string

        Returns:
            ParsedQuery or None if empty/invalid
        """
        query = query.strip()
        if not query:
            return None

        try:
            # Use shlex for proper quote handling
            tokens = shlex.split(query)
        except ValueError:
            # Handle unclosed quotes
            tokens = query.split()

        if not tokens:
            return None

        command = tokens[0].lower()
        args = []
        options = {}

        for token in tokens[1:]:
            if token.startswith("--"):
                # Option
                if "=" in token:
                    key, value = token[2:].split("=", 1)
                    options[key] = value
                else:
                    options[token[2:]] = True
            else:
                args.append(token)

        return ParsedQuery(
            command=command,
            args=args,
            options=options,
            raw=query,
        )

    def tokenize(self, query: str) -> list[str]:
        """
        Tokenize a query string for completion.

        Args:
            query: The query string

        Returns:
            List of tokens
        """
        try:
            return shlex.split(query)
        except ValueError:
            return query.split()

    def get_current_token(self, query: str, cursor: int) -> tuple[str, int]:
        """
        Get the token at cursor position.

        Args:
            query: The query string
            cursor: Cursor position

        Returns:
            Tuple of (current_token, token_start_position)
        """
        if cursor == 0:
            return "", 0

        # Find word boundaries
        start = cursor
        while start > 0 and query[start - 1] not in " \t":
            start -= 1

        end = cursor
        while end < len(query) and query[end] not in " \t":
            end += 1

        return query[start:end], start
