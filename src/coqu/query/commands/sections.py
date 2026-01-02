# coqu.query.commands.sections - Section query commands
"""
Commands for querying COBOL sections.
"""
from typing import Optional

from coqu.query.commands.base import Command, QueryResult


class SectionsCommand(Command):
    """List all sections in a program."""

    name = "sections"
    aliases = ["sec", "secs"]
    help = "List all sections in the program"
    usage = "sections [program] [--division=name]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        """Execute sections query."""
        # Get program
        program = None
        if args:
            loaded = workspace.get(args[0])
            if loaded:
                program = loaded.program
        else:
            # Use first loaded program
            programs = list(workspace)
            if programs:
                program = programs[0].program

        if not program:
            return QueryResult(error="No program loaded")

        # Filter by division if specified
        division_filter = options.get("division", "").upper()

        sections = []
        for div in program.divisions:
            if division_filter and division_filter not in div.name.upper():
                continue
            for section in div.sections:
                sections.append({
                    "name": section.name,
                    "division": div.name,
                    "line_start": section.location.line_start,
                    "line_end": section.location.line_end,
                })

        return QueryResult(items=sections)


class SectionCommand(Command):
    """Show details of a specific section."""

    name = "section"
    aliases = ["s"]
    help = "Show details of a specific section"
    usage = "section <name> [program] [--body]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        """Execute section query."""
        if not args:
            return QueryResult(error="Section name required")

        section_name = args[0].upper()

        # Get program
        program = None
        if len(args) > 1:
            loaded = workspace.get(args[1])
            if loaded:
                program = loaded.program
        else:
            programs = list(workspace)
            if programs:
                program = programs[0].program

        if not program:
            return QueryResult(error="No program loaded")

        # Find section
        target_section = None
        parent_division = None
        for div in program.divisions:
            for section in div.sections:
                if section.name.upper() == section_name or section_name in section.name.upper():
                    target_section = section
                    parent_division = div
                    break
            if target_section:
                break

        if not target_section:
            return QueryResult(error=f"Section not found: {section_name}")

        # Build result
        result = {
            "name": target_section.name,
            "division": parent_division.name,
            "line_start": target_section.location.line_start,
            "line_end": target_section.location.line_end,
            "paragraphs": [p.name for p in target_section.paragraphs],
            "data_items": [d.name for d in target_section.data_items],
        }

        # Include body if requested
        include_body = options.get("body", False)
        if include_body and program.source_lines:
            result["body"] = program.get_body(target_section.location)

        return QueryResult(items=[result])


class ProcedureSectionsCommand(Command):
    """List sections in PROCEDURE DIVISION only."""

    name = "procedure-sections"
    aliases = ["proc-sec", "psec"]
    help = "List sections in PROCEDURE DIVISION"
    usage = "procedure-sections [program]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        """Execute procedure sections query."""
        # Get program
        program = None
        if args:
            loaded = workspace.get(args[0])
            if loaded:
                program = loaded.program
        else:
            programs = list(workspace)
            if programs:
                program = programs[0].program

        if not program:
            return QueryResult(error="No program loaded")

        sections = program.get_procedure_sections()

        items = []
        for section in sections:
            items.append({
                "name": section.name,
                "line_start": section.location.line_start,
                "line_end": section.location.line_end,
                "paragraph_count": len(section.paragraphs),
            })

        return QueryResult(items=items)
