# coqu.query.commands.paragraphs - Paragraph-related commands
"""
Commands for querying COBOL paragraphs.
"""
from coqu.query.commands.base import Command, QueryResult


class ParagraphsCommand(Command):
    """List all paragraphs in a program."""

    name = "paragraphs"
    aliases = ["paras", "para"]
    help = "List all paragraphs in PROCEDURE DIVISION"
    usage = "paragraphs [program] [--section=name]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        program_name = args[0] if args else None
        section_filter = options.get("section", "").upper()

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
            # Get PROCEDURE DIVISION
            proc_div = prog.get_division("PROCEDURE")
            if not proc_div:
                continue

            # Paragraphs directly in division
            for para in proc_div.paragraphs:
                items.append({
                    "program": prog.name,
                    "name": para.name,
                    "section": None,
                    "location": str(para.location),
                    "performs": len(para.performs),
                    "calls": len(para.calls),
                })

            # Paragraphs in sections
            for section in proc_div.sections:
                if section_filter and section_filter not in section.name.upper():
                    continue

                for para in section.paragraphs:
                    items.append({
                        "program": prog.name,
                        "name": para.name,
                        "section": section.name,
                        "location": str(para.location),
                        "performs": len(para.performs),
                        "calls": len(para.calls),
                    })

        return QueryResult(items=items)


class ParagraphCommand(Command):
    """Show details of a specific paragraph."""

    name = "paragraph"
    aliases = ["p"]
    help = "Show details of a specific paragraph"
    usage = "paragraph <name> [program] [--body]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        if not args:
            return QueryResult(error="Paragraph name required")

        para_name = args[0].upper()
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
            para = prog.get_paragraph(para_name)
            if para:
                item = {
                    "program": prog.name,
                    "name": para.name,
                    "location": str(para.location),
                    "performs": para.performs,
                    "calls": para.calls,
                }

                if include_body:
                    item["body"] = prog.get_body(para.location)

                items.append(item)

        if not items:
            return QueryResult(error=f"Paragraph '{para_name}' not found")

        return QueryResult(items=items)
