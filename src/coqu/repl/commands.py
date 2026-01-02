# coqu.repl.commands - Meta command handlers
"""
Handles / prefixed meta commands in the REPL.
"""
from pathlib import Path
from typing import Callable, Optional


class MetaCommandHandler:
    """
    Handles meta commands (/ prefixed) in the REPL.

    Meta commands:
    - /load <file> - Load a COBOL file
    - /loaddir <dir> [pattern] - Load all files in directory
    - /unload <name> - Unload a program
    - /reload [name] - Reload program(s)
    - /list - List loaded programs
    - /copypath <path> - Add copybook search path
    - /info [name] - Show program info
    - /cache - Show cache stats
    - /clear-cache - Clear the cache
    - /help [command] - Show help
    - /quit - Exit REPL
    """

    def __init__(self, workspace, query_engine, cache_manager=None):
        """
        Initialize handler.

        Args:
            workspace: The workspace
            query_engine: Query engine
            cache_manager: Optional cache manager
        """
        self.workspace = workspace
        self.query_engine = query_engine
        self.cache_manager = cache_manager

        # Command registry
        self.commands: dict[str, Callable] = {
            "load": self.cmd_load,
            "loaddir": self.cmd_loaddir,
            "unload": self.cmd_unload,
            "reload": self.cmd_reload,
            "list": self.cmd_list,
            "programs": self.cmd_list,
            "copypath": self.cmd_copypath,
            "info": self.cmd_info,
            "cache": self.cmd_cache,
            "clear-cache": self.cmd_clear_cache,
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
            "q": self.cmd_quit,
        }

        self.help_text: dict[str, str] = {
            "load": "Load a COBOL file: /load <file>",
            "loaddir": "Load all files in directory: /loaddir <dir> [pattern]",
            "unload": "Unload a program: /unload <name>",
            "reload": "Reload program(s): /reload [name]",
            "list": "List loaded programs",
            "copypath": "Add copybook search path: /copypath <path>",
            "info": "Show program info: /info [name]",
            "cache": "Show cache statistics",
            "clear-cache": "Clear the AST cache",
            "help": "Show help: /help [command]",
            "quit": "Exit the REPL",
        }

    def execute(self, command: str, args: list[str]) -> tuple[str, bool]:
        """
        Execute a meta command.

        Args:
            command: Command name (without /)
            args: Command arguments

        Returns:
            Tuple of (output_message, should_exit)
        """
        handler = self.commands.get(command.lower())
        if not handler:
            return f"Unknown command: /{command}", False

        try:
            return handler(args)
        except Exception as e:
            return f"Error: {e}", False

    def list_commands(self) -> list[str]:
        """Get list of unique command names."""
        return list(set(self.help_text.keys()))

    def get_help_short(self, command: str) -> str:
        """Get short help for command."""
        return self.help_text.get(command, "")

    # Command implementations

    def _print_progress(self, stage: str, percent: int) -> None:
        """Print progress indicator inline."""
        import sys
        bar_width = 30
        filled = int(bar_width * percent / 100)
        bar = "=" * filled + "-" * (bar_width - filled)
        # Use carriage return to overwrite line
        sys.stdout.write(f"\r[{bar}] {percent:3d}% {stage:<20}")
        sys.stdout.flush()
        if percent >= 100:
            sys.stdout.write("\r" + " " * 60 + "\r")  # Clear line
            sys.stdout.flush()

    def cmd_load(self, args: list[str]) -> tuple[str, bool]:
        """Load a COBOL file."""
        if not args:
            return "Usage: /load <file>", False

        path = Path(args[0]).expanduser().resolve()
        if not path.exists():
            return f"File not found: {path}", False

        try:
            prog = self.workspace.load(path, progress_callback=self._print_progress)
            cache_str = " (from cache)" if prog.from_cache else f" (parsed in {prog.parse_time_ms:.0f}ms)"
            return f"Loaded {prog.name}: {prog.program_id} ({prog.lines} lines){cache_str}", False
        except Exception as e:
            return f"Failed to load {path}: {e}", False

    def cmd_loaddir(self, args: list[str]) -> tuple[str, bool]:
        """Load all COBOL files in a directory."""
        if not args:
            return "Usage: /loaddir <directory> [pattern]", False

        directory = Path(args[0]).expanduser().resolve()
        pattern = args[1] if len(args) > 1 else "*.cbl"

        if not directory.is_dir():
            return f"Not a directory: {directory}", False

        programs = self.workspace.load_directory(directory, pattern)
        return f"Loaded {len(programs)} programs from {directory}", False

    def cmd_unload(self, args: list[str]) -> tuple[str, bool]:
        """Unload a program."""
        if not args:
            return "Usage: /unload <name>", False

        name = args[0]
        if self.workspace.unload(name):
            return f"Unloaded {name}", False
        return f"Program not loaded: {name}", False

    def cmd_reload(self, args: list[str]) -> tuple[str, bool]:
        """Reload program(s)."""
        if args:
            prog = self.workspace.reload(args[0], progress_callback=self._print_progress)
            if prog:
                return f"Reloaded {prog.name} ({prog.parse_time_ms:.0f}ms)", False
            return f"Program not loaded: {args[0]}", False
        else:
            programs = self.workspace.reload_all(progress_callback=self._print_progress)
            return f"Reloaded {len(programs)} programs", False

    def cmd_list(self, args: list[str]) -> tuple[str, bool]:
        """List loaded programs."""
        programs = list(self.workspace)
        if not programs:
            return "No programs loaded", False

        lines = ["Loaded programs:", ""]
        for prog in programs:
            cache_str = " (cached)" if prog.from_cache else ""
            lines.append(f"  {prog.name}: {prog.program_id} ({prog.lines} lines){cache_str}")

        stats = self.workspace.get_stats()
        lines.append("")
        lines.append(f"Total: {stats['program_count']} programs, {stats['total_lines']} lines")

        return "\n".join(lines), False

    def cmd_copypath(self, args: list[str]) -> tuple[str, bool]:
        """Add copybook search path."""
        if not args:
            # List current paths
            paths = self.workspace.copybook_paths
            if not paths:
                return "No copybook paths configured", False
            lines = ["Copybook paths:"]
            for p in paths:
                lines.append(f"  {p}")
            return "\n".join(lines), False

        path = Path(args[0]).expanduser().resolve()
        if not path.is_dir():
            return f"Not a directory: {path}", False

        self.workspace.add_copybook_path(path)
        return f"Added copybook path: {path}", False

    def cmd_info(self, args: list[str]) -> tuple[str, bool]:
        """Show program info."""
        if args:
            prog = self.workspace.get(args[0])
            if not prog:
                return f"Program not loaded: {args[0]}", False
            programs = [prog]
        else:
            programs = list(self.workspace)
            if not programs:
                return "No programs loaded", False

        lines = []
        for prog in programs:
            lines.append(f"{prog.name}:")
            lines.append(f"  PROGRAM-ID: {prog.program_id}")
            lines.append(f"  Path: {prog.path}")
            lines.append(f"  Lines: {prog.lines}")
            lines.append(f"  Divisions: {len(prog.divisions)}")
            lines.append(f"  Sections: {len(prog.get_all_sections())}")
            lines.append(f"  Paragraphs: {len(prog.get_all_paragraphs())}")
            lines.append(f"  Copybooks: {len(prog.copybook_refs)}")
            lines.append("")

        return "\n".join(lines).rstrip(), False

    def cmd_cache(self, args: list[str]) -> tuple[str, bool]:
        """Show cache statistics."""
        if not self.cache_manager:
            return "Cache not enabled", False

        stats = self.cache_manager.get_stats()
        lines = [
            "Cache Statistics:",
            f"  Hits: {stats['hits']}",
            f"  Misses: {stats['misses']}",
            f"  Hit Rate: {stats['hit_rate']}%",
            f"  Files: {stats['file_count']}",
            f"  Size: {stats['total_size_mb']} MB",
        ]
        return "\n".join(lines), False

    def cmd_clear_cache(self, args: list[str]) -> tuple[str, bool]:
        """Clear the cache."""
        if not self.cache_manager:
            return "Cache not enabled", False

        count = self.cache_manager.clear()
        return f"Cleared {count} cached files", False

    def cmd_help(self, args: list[str]) -> tuple[str, bool]:
        """Show help."""
        if args:
            # Help for specific command
            cmd = args[0].lstrip("/")
            if cmd in self.help_text:
                return self.help_text[cmd], False
            # Try query command
            help_text = self.query_engine.get_help(cmd)
            return help_text, False

        # General help
        lines = [
            "coqu - COBOL Query",
            "",
            "Meta Commands:",
        ]

        for cmd in sorted(self.help_text.keys()):
            lines.append(f"  /{cmd} - {self.help_text[cmd]}")

        lines.append("")
        lines.append("Query Commands:")
        lines.append(self.query_engine.get_help())

        return "\n".join(lines), False

    def cmd_quit(self, args: list[str]) -> tuple[str, bool]:
        """Exit the REPL."""
        return "Goodbye!", True
