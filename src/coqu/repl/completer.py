# coqu.repl.completer - Tab completion for REPL
"""
Provides tab completion for queries and meta commands.
"""
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from typing import Iterable, Optional


class CoquCompleter(Completer):
    """
    Tab completer for coqu REPL.

    Provides completions for:
    - Query commands
    - Meta commands (/ prefixed)
    - Program names
    - Paragraph names
    - Variable names
    """

    def __init__(self, query_engine, meta_handler, workspace):
        """
        Initialize completer.

        Args:
            query_engine: Query engine for command completions
            meta_handler: Meta command handler
            workspace: Workspace for program/name completions
        """
        self.query_engine = query_engine
        self.meta_handler = meta_handler
        self.workspace = workspace

    def get_completions(
        self,
        document: Document,
        complete_event,
    ) -> Iterable[Completion]:
        """
        Get completions for current input.

        Args:
            document: Current document
            complete_event: Completion event

        Yields:
            Completion objects
        """
        text = document.text_before_cursor
        word = document.get_word_before_cursor()

        # Meta command completion
        if text.startswith("/"):
            yield from self._complete_meta(text, word)
            return

        # First word is command
        tokens = text.split()
        if len(tokens) <= 1:
            yield from self._complete_command(word)
            return

        # Subsequent words depend on command
        command = tokens[0].lower()
        yield from self._complete_args(command, word, tokens[1:])

    def _complete_meta(self, text: str, word: str) -> Iterable[Completion]:
        """Complete meta commands."""
        # Remove leading /
        prefix = text[1:].lower() if len(text) > 1 else ""

        for cmd in self.meta_handler.list_commands():
            if cmd.startswith(prefix):
                yield Completion(
                    "/" + cmd,
                    start_position=-len(text),
                    display_meta=self.meta_handler.get_help_short(cmd),
                )

    def _complete_command(self, word: str) -> Iterable[Completion]:
        """Complete query commands."""
        word_lower = word.lower()
        for name in self.query_engine.list_commands():
            if name.startswith(word_lower):
                cmd = self.query_engine.get_command(name)
                yield Completion(
                    name,
                    start_position=-len(word),
                    display_meta=cmd.help if cmd else "",
                )

    def _complete_args(
        self,
        command: str,
        word: str,
        existing_args: list[str],
    ) -> Iterable[Completion]:
        """Complete command arguments."""
        word_upper = word.upper()

        # Commands that take program names
        if command in ["divisions", "division", "paragraphs", "paragraph",
                       "working-storage", "variable", "copybooks", "calls",
                       "performs", "sql", "cics", "find", "references"]:
            # If first arg not given, suggest programs
            if not existing_args or word:
                yield from self._complete_programs(word_upper)

        # Commands that take paragraph names
        if command in ["paragraph", "where-used", "moves"]:
            if len(existing_args) == 0 or (len(existing_args) == 1 and word):
                yield from self._complete_paragraphs(word_upper)

        # Commands that take variable names
        if command in ["variable", "references"]:
            if len(existing_args) == 0 or (len(existing_args) == 1 and word):
                yield from self._complete_variables(word_upper)

        # Commands that take copybook names
        if command in ["copybook", "copybook-deps"]:
            if len(existing_args) == 0 or (len(existing_args) == 1 and word):
                yield from self._complete_copybooks(word_upper)

        # Option completions
        if word.startswith("--"):
            yield from self._complete_options(command, word)

    def _complete_programs(self, prefix: str) -> Iterable[Completion]:
        """Complete program names."""
        for name in self.workspace.list_programs():
            if name.startswith(prefix):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                )

    def _complete_paragraphs(self, prefix: str) -> Iterable[Completion]:
        """Complete paragraph names."""
        seen = set()
        for prog in self.workspace:
            for para in prog.get_all_paragraphs():
                name = para.name.upper()
                if name.startswith(prefix) and name not in seen:
                    seen.add(name)
                    yield Completion(
                        name,
                        start_position=-len(prefix),
                    )

    def _complete_variables(self, prefix: str) -> Iterable[Completion]:
        """Complete variable names."""
        seen = set()
        for prog in self.workspace:
            for item in prog.get_working_storage_items():
                name = item.name.upper()
                if name.startswith(prefix) and name not in seen:
                    seen.add(name)
                    yield Completion(
                        name,
                        start_position=-len(prefix),
                    )

    def _complete_copybooks(self, prefix: str) -> Iterable[Completion]:
        """Complete copybook names."""
        seen = set()
        for prog in self.workspace:
            for ref in prog.copybook_refs:
                name = ref.name.upper()
                if name.startswith(prefix) and name not in seen:
                    seen.add(name)
                    yield Completion(
                        name,
                        start_position=-len(prefix),
                    )

    def _complete_options(self, command: str, word: str) -> Iterable[Completion]:
        """Complete command options."""
        options = {
            "body": "Include source code body",
            "level": "Filter by level number",
            "section": "Filter by section name",
            "target": "Filter by target name",
            "context": "Lines of context",
        }

        prefix = word[2:]  # Remove --
        for opt, desc in options.items():
            if opt.startswith(prefix):
                yield Completion(
                    "--" + opt,
                    start_position=-len(word),
                    display_meta=desc,
                )
