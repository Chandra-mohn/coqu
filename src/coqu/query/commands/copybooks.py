# coqu.query.commands.copybooks - Copybook-related commands
"""
Commands for querying COBOL copybooks.
"""
from coqu.query.commands.base import Command, QueryResult


class CopybooksCommand(Command):
    """List all copybook references."""

    name = "copybooks"
    aliases = ["copies", "copy"]
    help = "List all COPY statements in loaded programs"
    usage = "copybooks [program]"

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
            for ref in prog.copybook_refs:
                items.append({
                    "program": prog.name,
                    "name": ref.name,
                    "line": ref.line,
                    "status": ref.status,
                    "resolved_path": str(ref.resolved_path) if ref.resolved_path else None,
                    "replacing": ref.replacing,
                })

        return QueryResult(items=items)


class CopybookCommand(Command):
    """Show details of a specific copybook."""

    name = "copybook"
    aliases = ["cb"]
    help = "Show details of a specific copybook"
    usage = "copybook <name> [--body]"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        if not args:
            return QueryResult(error="Copybook name required")

        cb_name = args[0].upper()
        include_body = options.get("body", False)

        # Get copybook info from resolver
        info = workspace.copybook_resolver.get_info(cb_name)

        if not info:
            return QueryResult(error=f"Copybook '{cb_name}' not found")

        item = {
            "name": info.name,
            "path": str(info.path),
            "size": info.size,
            "lines": info.lines,
            "nested_refs": info.nested_refs,
        }

        if include_body:
            try:
                item["body"] = info.path.read_text()
            except Exception:
                item["body"] = "(unable to read)"

        return QueryResult(items=[item])


class CopybookDepsCommand(Command):
    """Show copybook dependency tree."""

    name = "copybook-deps"
    aliases = ["deps", "cb-deps"]
    help = "Show copybook dependency tree"
    usage = "copybook-deps <name>"

    def execute(self, workspace, args: list[str], options: dict) -> QueryResult:
        args, opts = self.parse_options(args)
        options.update(opts)

        if not args:
            return QueryResult(error="Copybook name required")

        cb_name = args[0].upper()

        # Get dependency tree
        tree = workspace.copybook_resolver.get_dependency_tree(cb_name)

        if not tree.get("resolved"):
            return QueryResult(error=f"Copybook '{cb_name}' not found")

        # Format tree for display
        lines = self._format_tree(tree, 0)

        return QueryResult(
            items=[tree],
            message="\n".join(lines),
        )

    def _format_tree(self, node: dict, indent: int) -> list[str]:
        """Format dependency tree for display."""
        prefix = "  " * indent
        lines = []

        name = node["name"]
        if node.get("circular"):
            lines.append(f"{prefix}{name} (circular reference)")
        elif not node.get("resolved"):
            lines.append(f"{prefix}{name} (not found)")
        else:
            lines.append(f"{prefix}{name} ({node.get('lines', 0)} lines)")
            for nested in node.get("nested", []):
                lines.extend(self._format_tree(nested, indent + 1))

        return lines
