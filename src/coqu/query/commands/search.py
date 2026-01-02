# coqu.query.commands.search - Search and reference commands
"""
Commands for searching code and finding references.
"""
import re
from coqu.query.commands.base import Command, QueryResult


class FindCommand(Command):
    """Search for patterns in source code."""

    name = "find"
    aliases = ["search", "grep"]
    help = "Search for patterns in source code"
    usage = "find <pattern> [program] [--context=N]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        if not args:
            return QueryResult(error="Search pattern required")

        pattern = args[0]
        program_name = args[1] if len(args) > 1 else None
        context = int(options.get("context", 0))

        # Compile pattern
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return QueryResult(error=f"Invalid pattern: {e}")

        # Get target programs
        if program_name:
            prog = workspace.get(program_name)
            if not prog:
                return QueryResult(error=f"Program '{program_name}' not loaded")
            programs = [prog]
        else:
            programs = list(workspace)
            if not programs:
                return QueryResult(error="No programs loaded")

        items = []
        for prog in programs:
            if not prog.program.source_lines:
                continue

            lines = prog.program.source_lines
            for i, line in enumerate(lines):
                if regex.search(line):
                    # Get context lines
                    start = max(0, i - context)
                    end = min(len(lines), i + context + 1)

                    context_lines = []
                    for j in range(start, end):
                        prefix = ">" if j == i else " "
                        context_lines.append(f"{prefix} {j + 1}: {lines[j]}")

                    items.append({
                        "program": prog.name,
                        "line": i + 1,
                        "text": line.strip(),
                        "context": "\n".join(context_lines) if context > 0 else None,
                    })

        return QueryResult(items=items)


class ReferencesCommand(Command):
    """Find references to a variable or paragraph."""

    name = "references"
    aliases = ["refs", "ref"]
    help = "Find all references to a name"
    usage = "references <name> [program]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        if not args:
            return QueryResult(error="Name to search required")

        name = args[0].upper()
        program_name = args[1] if len(args) > 1 else None

        # Create word-boundary pattern
        pattern = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)

        # Get target programs
        if program_name:
            prog = workspace.get(program_name)
            if not prog:
                return QueryResult(error=f"Program '{program_name}' not loaded")
            programs = [prog]
        else:
            programs = list(workspace)
            if not programs:
                return QueryResult(error="No programs loaded")

        items = []
        for prog in programs:
            if not prog.program.source_lines:
                continue

            lines = prog.program.source_lines
            for i, line in enumerate(lines):
                # Skip comments (column 7 is *)
                if len(line) > 6 and line[6] == "*":
                    continue

                matches = list(pattern.finditer(line))
                for match in matches:
                    items.append({
                        "program": prog.name,
                        "line": i + 1,
                        "column": match.start() + 1,
                        "text": line.strip(),
                    })

        return QueryResult(items=items)


class WhereUsedCommand(Command):
    """Find where a paragraph is called from."""

    name = "where-used"
    aliases = ["callers", "who-calls"]
    help = "Find all callers of a paragraph"
    usage = "where-used <paragraph-name> [program]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        if not args:
            return QueryResult(error="Paragraph name required")

        target_name = args[0].upper()
        program_name = args[1] if len(args) > 1 else None

        # Get target programs
        if program_name:
            prog = workspace.get(program_name)
            if not prog:
                return QueryResult(error=f"Program '{program_name}' not loaded")
            programs = [prog]
        else:
            programs = list(workspace)
            if not programs:
                return QueryResult(error="No programs loaded")

        items = []
        for prog in programs:
            for para in prog.get_all_paragraphs():
                # Check if this paragraph PERFORMs the target
                if target_name in [p.upper() for p in para.performs]:
                    items.append({
                        "program": prog.name,
                        "caller": para.name,
                        "type": "PERFORM",
                        "location": str(para.location),
                    })

        if not items:
            return QueryResult(
                message=f"No callers found for '{target_name}'",
                items=[],
            )

        return QueryResult(items=items)
