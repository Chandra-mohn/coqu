# coqu.query.commands.variables - Data item commands
"""
Commands for querying COBOL data items (variables).
"""
from coqu.query.commands.base import Command, QueryResult


class WorkingStorageCommand(Command):
    """List WORKING-STORAGE data items."""

    name = "working-storage"
    aliases = ["ws", "working"]
    help = "List WORKING-STORAGE SECTION data items"
    usage = "working-storage [program] [--level=N]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        program_name = args[0] if args else None
        level_filter = options.get("level")

        if level_filter:
            try:
                level_filter = int(level_filter)
            except ValueError:
                return QueryResult(error=f"Invalid level: {level_filter}")

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
            ws_items = prog.get_working_storage_items(level_filter)
            for item in ws_items:
                items.append({
                    "program": prog.name,
                    "name": item.name,
                    "level": item.level,
                    "pic": item.pic,
                    "location": str(item.location),
                })

        return QueryResult(items=items)


class VariableCommand(Command):
    """Show details of a specific variable."""

    name = "variable"
    aliases = ["var", "v"]
    help = "Show details of a specific variable"
    usage = "variable <name> [program] [--body]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        if not args:
            return QueryResult(error="Variable name required")

        var_name = args[0].upper()
        program_name = args[1] if len(args) > 1 else None
        include_body = options.get("body", False)

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
            # Search in DATA DIVISION
            data_div = prog.get_division("DATA")
            if not data_div:
                continue

            for section in data_div.sections:
                for item in section.data_items:
                    if item.name.upper() == var_name:
                        result = {
                            "program": prog.name,
                            "name": item.name,
                            "level": item.level,
                            "section": section.name,
                            "pic": item.pic,
                            "usage": item.usage,
                            "value": item.value,
                            "occurs": item.occurs,
                            "redefines": item.redefines,
                            "location": str(item.location),
                        }

                        if include_body:
                            result["body"] = prog.get_body(item.location)

                        items.append(result)

        if not items:
            return QueryResult(error=f"Variable '{var_name}' not found")

        return QueryResult(items=items)


class FileSectionCommand(Command):
    """List FILE SECTION data items."""

    name = "file-section"
    aliases = ["files", "fd"]
    help = "List FILE SECTION data items"
    usage = "file-section [program]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        program_name = args[0] if args else None

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
            data_div = prog.get_division("DATA")
            if not data_div:
                continue

            for section in data_div.sections:
                if "FILE" in section.name.upper():
                    for item in section.data_items:
                        items.append({
                            "program": prog.name,
                            "name": item.name,
                            "level": item.level,
                            "pic": item.pic,
                            "location": str(item.location),
                        })

        return QueryResult(items=items)


class LinkageCommand(Command):
    """List LINKAGE SECTION data items."""

    name = "linkage"
    aliases = ["link"]
    help = "List LINKAGE SECTION data items"
    usage = "linkage [program]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        program_name = args[0] if args else None

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
            data_div = prog.get_division("DATA")
            if not data_div:
                continue

            for section in data_div.sections:
                if "LINKAGE" in section.name.upper():
                    for item in section.data_items:
                        items.append({
                            "program": prog.name,
                            "name": item.name,
                            "level": item.level,
                            "pic": item.pic,
                            "location": str(item.location),
                        })

        return QueryResult(items=items)
