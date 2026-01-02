# coqu.query.commands.statements - Statement-related commands
"""
Commands for querying COBOL statements (CALL, PERFORM, etc).
"""
import re
from coqu.query.commands.base import Command, QueryResult


class CallsCommand(Command):
    """List all CALL statements."""

    name = "calls"
    aliases = ["call"]
    help = "List all CALL statements in loaded programs"
    usage = "calls [program] [--target=name]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        program_name = args[0] if args else None
        target_filter = options.get("target", "").upper()

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
                for call in para.calls:
                    if target_filter and target_filter not in call.upper():
                        continue
                    items.append({
                        "program": prog.name,
                        "paragraph": para.name,
                        "target": call,
                        "location": str(para.location),
                    })

        return QueryResult(items=items)


class PerformsCommand(Command):
    """List all PERFORM statements."""

    name = "performs"
    aliases = ["perform"]
    help = "List all PERFORM statements in loaded programs"
    usage = "performs [program] [--target=name]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        program_name = args[0] if args else None
        target_filter = options.get("target", "").upper()

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
                for perform in para.performs:
                    if target_filter and target_filter not in perform.upper():
                        continue
                    items.append({
                        "program": prog.name,
                        "paragraph": para.name,
                        "target": perform,
                        "location": str(para.location),
                    })

        return QueryResult(items=items)


class MovesCommand(Command):
    """List MOVE statements (basic extraction)."""

    name = "moves"
    aliases = ["move"]
    help = "List MOVE statements in a paragraph"
    usage = "moves <paragraph> [program]"

    # Pattern to extract MOVE statements
    MOVE_PATTERN = re.compile(
        r"MOVE\s+(\S+)\s+TO\s+(\S+)",
        re.IGNORECASE,
    )

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        if not args:
            return QueryResult(error="Paragraph name required")

        para_name = args[0].upper()
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
            para = prog.get_paragraph(para_name)
            if not para:
                continue

            # Get paragraph body
            body = prog.get_body(para.location)

            # Find MOVE statements
            for match in self.MOVE_PATTERN.finditer(body):
                items.append({
                    "program": prog.name,
                    "paragraph": para.name,
                    "from": match.group(1),
                    "to": match.group(2),
                })

        if not items:
            return QueryResult(error=f"No MOVE statements found in '{para_name}'")

        return QueryResult(items=items)


class SqlCommand(Command):
    """List EXEC SQL statements (basic extraction)."""

    name = "sql"
    aliases = ["exec-sql"]
    help = "List EXEC SQL statements"
    usage = "sql [program]"

    # Pattern to extract EXEC SQL blocks
    SQL_PATTERN = re.compile(
        r"EXEC\s+SQL\s+(.*?)\s+END-EXEC",
        re.IGNORECASE | re.DOTALL,
    )

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
            if not prog.program.source_lines:
                continue

            source = "\n".join(prog.program.source_lines)
            for match in self.SQL_PATTERN.finditer(source):
                sql_text = match.group(1).strip()
                # Extract first word as operation type
                op_match = re.match(r"(\w+)", sql_text)
                op_type = op_match.group(1).upper() if op_match else "UNKNOWN"

                line_num = source[:match.start()].count("\n") + 1

                items.append({
                    "program": prog.name,
                    "operation": op_type,
                    "line": line_num,
                    "sql": sql_text[:100] + ("..." if len(sql_text) > 100 else ""),
                })

        return QueryResult(items=items)


class CicsCommand(Command):
    """List EXEC CICS statements (basic extraction)."""

    name = "cics"
    aliases = ["exec-cics"]
    help = "List EXEC CICS statements"
    usage = "cics [program]"

    # Pattern to extract EXEC CICS blocks
    CICS_PATTERN = re.compile(
        r"EXEC\s+CICS\s+(.*?)\s+END-EXEC",
        re.IGNORECASE | re.DOTALL,
    )

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
            if not prog.program.source_lines:
                continue

            source = "\n".join(prog.program.source_lines)
            for match in self.CICS_PATTERN.finditer(source):
                cics_text = match.group(1).strip()
                # Extract first word as command type
                cmd_match = re.match(r"(\w+)", cics_text)
                cmd_type = cmd_match.group(1).upper() if cmd_match else "UNKNOWN"

                line_num = source[:match.start()].count("\n") + 1

                items.append({
                    "program": prog.name,
                    "command": cmd_type,
                    "line": line_num,
                    "cics": cics_text[:100] + ("..." if len(cics_text) > 100 else ""),
                })

        return QueryResult(items=items)
