# coqu.repl.repl - Main REPL implementation
"""
Interactive REPL for COBOL queries.
"""
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style

from coqu.workspace import Workspace
from coqu.cache import CacheManager
from coqu.query import QueryEngine
from coqu.repl.completer import CoquCompleter
from coqu.repl.commands import MetaCommandHandler
from coqu.version import __version__


class Repl:
    """
    Interactive REPL for COBOL queries.

    Features:
    - Tab completion for commands and names
    - Command history
    - Meta commands (/ prefixed)
    - Script execution
    """

    # REPL prompt style
    STYLE = Style.from_dict({
        "prompt": "bold cyan",
        "rprompt": "gray",
    })

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        copybook_paths: Optional[list[Path]] = None,
        use_indexer_only: bool = False,
        history_file: Optional[Path] = None,
    ):
        """
        Initialize REPL.

        Args:
            cache_dir: Cache directory
            copybook_paths: Copybook search paths
            use_indexer_only: Use fast indexer instead of ANTLR
            history_file: History file path
        """
        # Initialize cache
        self.cache_manager = CacheManager(cache_dir) if cache_dir is not False else None

        # Initialize workspace
        self.workspace = Workspace(
            copybook_paths=copybook_paths,
            cache_manager=self.cache_manager,
            use_indexer_only=use_indexer_only,
        )

        # Initialize query engine
        self.query_engine = QueryEngine(self.workspace)

        # Initialize meta command handler
        self.meta_handler = MetaCommandHandler(
            self.workspace,
            self.query_engine,
            self.cache_manager,
        )

        # Initialize completer
        self.completer = CoquCompleter(
            self.query_engine,
            self.meta_handler,
            self.workspace,
        )

        # Setup history
        if history_file is None:
            history_file = Path.home() / ".coqu_history"
        self.history = FileHistory(str(history_file))

        # Create prompt session
        self.session: Optional[PromptSession] = None

    def _create_session(self) -> PromptSession:
        """Create prompt session."""
        return PromptSession(
            history=self.history,
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.completer,
            style=self.STYLE,
            complete_while_typing=False,
        )

    def run(self) -> None:
        """Run the REPL."""
        self.session = self._create_session()

        # Print banner
        print(self._get_banner())

        # Main loop
        while True:
            try:
                # Get input
                line = self.session.prompt(
                    [("class:prompt", "coqu> ")],
                    rprompt=self._get_rprompt(),
                )

                # Skip empty lines
                if not line or not line.strip():
                    continue

                # Execute
                should_exit = self.execute_line(line.strip())
                if should_exit:
                    break

            except KeyboardInterrupt:
                print("\nUse /quit to exit")
                continue

            except EOFError:
                print("\nGoodbye!")
                break

    def execute_line(self, line: str) -> bool:
        """
        Execute a line of input.

        Args:
            line: Input line

        Returns:
            True if REPL should exit
        """
        if line.startswith("/"):
            # Meta command
            return self._execute_meta(line)

        # Handle common commands without / prefix
        first_word = line.split()[0].lower() if line.split() else ""
        if first_word in ("help", "quit", "exit", "q"):
            return self._execute_meta("/" + line)

        # Query
        self._execute_query(line)
        return False

    def _execute_meta(self, line: str) -> bool:
        """Execute meta command."""
        # Parse command and args
        parts = line[1:].split(None, 1)
        command = parts[0] if parts else ""
        args = parts[1].split() if len(parts) > 1 else []

        output, should_exit = self.meta_handler.execute(command, args)
        if output:
            print(output)

        return should_exit

    def _execute_query(self, line: str) -> None:
        """Execute query."""
        result = self.query_engine.execute(line)

        # Check for --body option
        include_body = "--body" in line

        output = result.format_text(include_body=include_body)
        print(output)

    def execute_script(self, script_path: Path) -> int:
        """
        Execute a script file.

        Args:
            script_path: Path to .coqu script

        Returns:
            Number of errors
        """
        if not script_path.exists():
            print(f"Script not found: {script_path}")
            return 1

        errors = 0
        for line_num, line in enumerate(script_path.read_text().splitlines(), 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            try:
                if self.execute_line(line):
                    break
            except Exception as e:
                print(f"Error at line {line_num}: {e}")
                errors += 1

        return errors

    def _get_banner(self) -> str:
        """Get welcome banner."""
        return f"""
coqu v{__version__} - COBOL Query
Type /help for commands, /quit to exit
"""

    def _get_rprompt(self) -> str:
        """Get right prompt (program count)."""
        count = len(self.workspace)
        if count == 0:
            return ""
        return f"[{count} program{'s' if count != 1 else ''}]"

    def load_initial_files(self, paths: list[Path]) -> None:
        """
        Load initial files.

        Args:
            paths: List of paths to load
        """
        for path in paths:
            if path.is_file():
                try:
                    prog = self.workspace.load(path)
                    print(f"Loaded: {prog.name}")
                except Exception as e:
                    print(f"Failed to load {path}: {e}")
            elif path.is_dir():
                programs = self.workspace.load_directory(path)
                print(f"Loaded {len(programs)} programs from {path}")
