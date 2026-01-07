# coqu.cli - Command line interface
"""
CLI entry point for coqu.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from coqu.version import __version__
from coqu.config import load_config
from coqu.workspace import Workspace
from coqu.cache import CacheManager
from coqu.query import QueryEngine
from coqu.repl import Repl


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="coqu",
        description="COBOL Query - Interactive COBOL source analyzer",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"coqu {__version__}",
    )

    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Coverage subcommand
    coverage_parser = subparsers.add_parser(
        "coverage",
        help="Analyze parser coverage of a COBOL file",
    )
    coverage_parser.add_argument(
        "file",
        type=Path,
        help="COBOL file to analyze",
    )
    coverage_parser.add_argument(
        "--mode",
        choices=["antlr", "indexer", "both"],
        default="both",
        help="Parser mode to analyze (default: both)",
    )
    coverage_parser.add_argument(
        "--show-uncovered",
        action="store_true",
        help="Show list of uncovered line numbers",
    )
    coverage_parser.add_argument(
        "--show-source",
        action="store_true",
        help="Show uncovered source lines",
    )

    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="COBOL files or directories to load",
    )

    parser.add_argument(
        "-c", "--command",
        help="Execute a single query and exit",
    )

    parser.add_argument(
        "-s", "--script",
        type=Path,
        help="Execute a .coqu script file",
    )

    parser.add_argument(
        "-o", "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--copybook-path",
        type=Path,
        action="append",
        dest="copybook_paths",
        help="Add copybook search path (can be repeated)",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable AST caching",
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Cache directory (default: ~/.cache/coqu)",
    )

    parser.add_argument(
        "--indexer-only",
        action="store_true",
        help="Use fast regex indexer instead of full ANTLR parser",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config file",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle coverage command
    if args.command == "coverage":
        return run_coverage(args)

    # Load config
    config = load_config(args.config)

    # Merge CLI args with config
    copybook_paths = list(config.copybook_paths)
    if args.copybook_paths:
        copybook_paths.extend(args.copybook_paths)

    cache_enabled = config.cache_enabled and not args.no_cache
    cache_dir = args.cache_dir or config.cache_dir
    use_indexer_only = args.indexer_only or config.use_indexer_only

    # Single command mode
    if args.command:
        return run_command(
            args.command,
            args.files,
            copybook_paths,
            cache_enabled,
            cache_dir,
            use_indexer_only,
            args.output,
            args.debug,
        )

    # Script mode
    if args.script:
        return run_script(
            args.script,
            args.files,
            copybook_paths,
            cache_enabled,
            cache_dir,
            use_indexer_only,
            args.debug,
        )

    # Interactive REPL mode
    return run_repl(
        args.files,
        copybook_paths,
        cache_enabled,
        cache_dir,
        use_indexer_only,
        config.history_file,
    )


def run_coverage(args) -> int:
    """Run coverage analysis."""
    from coqu.parser.coverage import CoverageAnalyzer

    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    analyzer = CoverageAnalyzer()
    results = analyzer.analyze_file(args.file, args.mode)

    # Read source for --show-source option
    source_lines = []
    if args.show_source:
        source_lines = args.file.read_text().split("\n")

    for mode_name, result in results.items():
        print(f"\n{'='*60}")
        print(f"Coverage Analysis: {args.file.name} ({mode_name.upper()} parser)")
        print('='*60)
        print(result.summary())

        if args.show_uncovered:
            print()
            print(result.uncovered_list())

        if args.show_source and result.uncovered_lines:
            print()
            print("Uncovered source lines:")
            print("-" * 40)
            for line_num in sorted(result.uncovered_lines):
                if line_num <= len(source_lines):
                    print(f"{line_num:4d}: {source_lines[line_num - 1]}")

    # Return success if coverage is above threshold (e.g., any coverage)
    return 0


def run_command(
    command: str,
    files: list[Path],
    copybook_paths: list[Path],
    cache_enabled: bool,
    cache_dir: Optional[Path],
    use_indexer_only: bool,
    output_format: str,
    debug: bool,
) -> int:
    """Run a single command and exit."""
    # Setup
    cache_manager = CacheManager(cache_dir) if cache_enabled else None

    workspace = Workspace(
        copybook_paths=copybook_paths,
        cache_manager=cache_manager,
        use_indexer_only=use_indexer_only,
    )

    # Load files
    for path in files:
        if path.is_file():
            try:
                workspace.load(path)
            except Exception as e:
                if debug:
                    print(f"Warning: Failed to load {path}: {e}", file=sys.stderr)
        elif path.is_dir():
            workspace.load_directory(path)

    if not workspace.programs:
        print("No programs loaded", file=sys.stderr)
        return 1

    # Execute query
    engine = QueryEngine(workspace)
    result = engine.execute(command)

    # Output
    if output_format == "json":
        print(json.dumps(result.to_json(), indent=2))
    else:
        include_body = "--body" in command
        print(result.format_text(include_body=include_body))

    return 0 if not result.is_error else 1


def run_script(
    script_path: Path,
    files: list[Path],
    copybook_paths: list[Path],
    cache_enabled: bool,
    cache_dir: Optional[Path],
    use_indexer_only: bool,
    debug: bool,
) -> int:
    """Run a script file."""
    repl = Repl(
        cache_dir=cache_dir if cache_enabled else False,
        copybook_paths=copybook_paths,
        use_indexer_only=use_indexer_only,
    )

    # Load initial files
    repl.load_initial_files(files)

    # Execute script
    errors = repl.execute_script(script_path)

    return errors


def run_repl(
    files: list[Path],
    copybook_paths: list[Path],
    cache_enabled: bool,
    cache_dir: Optional[Path],
    use_indexer_only: bool,
    history_file: Optional[Path],
) -> int:
    """Run interactive REPL."""
    repl = Repl(
        cache_dir=cache_dir if cache_enabled else False,
        copybook_paths=copybook_paths,
        use_indexer_only=use_indexer_only,
        history_file=history_file,
    )

    # Load initial files
    if files:
        repl.load_initial_files(files)

    # Run REPL
    repl.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
