# coqu.workspace - Workspace management module
from coqu.workspace.workspace import Workspace
from coqu.workspace.program import LoadedProgram
from coqu.workspace.copybook import CopybookResolver

__all__ = [
    "Workspace",
    "LoadedProgram",
    "CopybookResolver",
]
