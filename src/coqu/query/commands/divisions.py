# coqu.query.commands.divisions - Division-related commands
"""
Commands for querying COBOL divisions.
"""
from coqu.query.commands.base import Command, QueryResult


class DivisionsCommand(Command):
    """List all divisions in a program."""

    name = "divisions"
    aliases = ["div", "divs"]
    help = "List all divisions in the current program"
    usage = "divisions [program]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        # Get target program
        program_name = args[0] if args else None

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
            for div in prog.divisions:
                items.append({
                    "program": prog.name,
                    "name": div.name,
                    "location": str(div.location),
                    "sections": len(div.sections),
                    "paragraphs": len(div.paragraphs),
                })

        return QueryResult(items=items)


class DivisionCommand(Command):
    """Show details of a specific division."""

    name = "division"
    aliases = []
    help = "Show details of a specific division"
    usage = "division <name> [program] [--body]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        if not args:
            return QueryResult(error="Division name required")

        div_name = args[0].upper()
        program_name = args[1] if len(args) > 1 else None

        # Get target program
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
        include_body = options.get("body", False)

        for prog in programs:
            for div in prog.divisions:
                if div_name in div.name.upper():
                    item = {
                        "program": prog.name,
                        "name": div.name,
                        "location": str(div.location),
                        "sections": [s.name for s in div.sections],
                        "paragraphs": [p.name for p in div.paragraphs],
                    }

                    if include_body:
                        item["body"] = prog.get_body(div.location)

                    items.append(item)

        if not items:
            return QueryResult(error=f"Division '{div_name}' not found")

        return QueryResult(items=items)
