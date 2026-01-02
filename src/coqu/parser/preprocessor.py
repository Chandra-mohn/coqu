# coqu.parser.preprocessor - COBOL preprocessor for COPY/REPLACE
"""
Preprocessor for COBOL source code.
Handles COPY statement resolution and REPLACE directives.
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from coqu.parser.ast import CopybookRef


@dataclass
class PreprocessorResult:
    """Result of preprocessing COBOL source."""
    source: str  # Preprocessed source
    original_source: str  # Original source before preprocessing
    copybook_refs: list[CopybookRef]
    warnings: list[str]
    errors: list[str]


class Preprocessor:
    """
    COBOL preprocessor for COPY and REPLACE statements.

    Handles:
    - COPY statement resolution (inline expansion)
    - COPY ... REPLACING clause
    - Nested copybooks
    - REPLACE directive (text substitution)
    """

    # Pattern for COPY statement
    COPY_PATTERN = re.compile(
        r"COPY\s+([A-Z][A-Z0-9-]*)"
        r"(?:\s+(?:OF|IN)\s+([A-Z][A-Z0-9-]*))?"  # Optional library
        r"(?:\s+REPLACING\s+(.+?))?"  # Optional REPLACING clause
        r"\s*\.",
        re.IGNORECASE | re.DOTALL,
    )

    # Pattern for REPLACE statement
    REPLACE_PATTERN = re.compile(
        r"REPLACE\s+(.+?)\s*\.",
        re.IGNORECASE | re.DOTALL,
    )

    # Pattern for REPLACE OFF
    REPLACE_OFF_PATTERN = re.compile(
        r"REPLACE\s+OFF\s*\.",
        re.IGNORECASE,
    )

    # Common copybook extensions
    COPYBOOK_EXTENSIONS = [".cpy", ".copy", ".cbl", ".cob", ""]

    def __init__(self, copybook_paths: Optional[list[Path]] = None):
        """
        Initialize preprocessor.

        Args:
            copybook_paths: List of directories to search for copybooks
        """
        self.copybook_paths = copybook_paths or []
        self._copybook_cache: dict[str, str] = {}
        self._processed_copybooks: set[str] = set()  # For circular reference detection

    def add_copybook_path(self, path: Path) -> None:
        """Add a copybook search path."""
        if path not in self.copybook_paths:
            self.copybook_paths.append(path)

    def preprocess(
        self,
        source: str,
        source_path: Optional[Path] = None,
        resolve_copybooks: bool = True,
    ) -> PreprocessorResult:
        """
        Preprocess COBOL source code.

        Args:
            source: COBOL source code
            source_path: Path to source file (for relative copybook resolution)
            resolve_copybooks: Whether to inline copybook contents

        Returns:
            PreprocessorResult with preprocessed source and metadata
        """
        result = PreprocessorResult(
            source=source,
            original_source=source,
            copybook_refs=[],
            warnings=[],
            errors=[],
        )

        # Reset processed copybooks for this run
        self._processed_copybooks.clear()

        # Find all COPY statements
        copybook_refs = self._find_copy_statements(source)
        result.copybook_refs = copybook_refs

        if resolve_copybooks:
            # Resolve each copybook
            for ref in copybook_refs:
                resolved_path = self._resolve_copybook(ref.name, source_path)
                if resolved_path:
                    ref.resolved_path = resolved_path
                    ref.status = "resolved"
                else:
                    ref.status = "unresolved"
                    result.warnings.append(
                        f"Copybook '{ref.name}' not found in search paths "
                        f"(referenced at line {ref.line})"
                    )

            # Inline copybook contents
            result.source = self._inline_copybooks(
                source, copybook_refs, source_path, result.warnings
            )

        return result

    def _find_copy_statements(self, source: str) -> list[CopybookRef]:
        """Find all COPY statements in source."""
        refs = []
        for match in self.COPY_PATTERN.finditer(source):
            line_num = source[:match.start()].count("\n") + 1
            copybook_name = match.group(1).upper()
            library = match.group(2).upper() if match.group(2) else None
            replacing = match.group(3).strip() if match.group(3) else None

            refs.append(CopybookRef(
                name=copybook_name,
                line=line_num,
                replacing=replacing,
            ))
        return refs

    def _resolve_copybook(
        self,
        name: str,
        source_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Resolve copybook name to file path.

        Search order:
        1. Same directory as source file
        2. Configured copybook paths
        """
        # Normalize name
        name_lower = name.lower()

        # Search paths to check
        search_paths: list[Path] = []

        # Add source directory first
        if source_path:
            search_paths.append(source_path.parent)

        # Add configured paths
        search_paths.extend(self.copybook_paths)

        # Try each path with each extension
        for search_path in search_paths:
            for ext in self.COPYBOOK_EXTENSIONS:
                candidate = search_path / f"{name_lower}{ext}"
                if candidate.exists():
                    return candidate

                # Try uppercase too
                candidate = search_path / f"{name.upper()}{ext}"
                if candidate.exists():
                    return candidate

        return None

    def _inline_copybooks(
        self,
        source: str,
        refs: list[CopybookRef],
        source_path: Optional[Path],
        warnings: list[str],
    ) -> str:
        """Inline copybook contents into source."""
        result = source

        # Process in reverse order to preserve line positions
        for ref in sorted(refs, key=lambda r: r.line, reverse=True):
            if ref.status != "resolved" or not ref.resolved_path:
                continue

            # Check for circular references
            ref_key = str(ref.resolved_path.resolve())
            if ref_key in self._processed_copybooks:
                warnings.append(
                    f"Circular copybook reference detected: {ref.name}"
                )
                continue

            self._processed_copybooks.add(ref_key)

            try:
                # Read copybook content
                if ref_key in self._copybook_cache:
                    copybook_content = self._copybook_cache[ref_key]
                else:
                    copybook_content = ref.resolved_path.read_text()
                    self._copybook_cache[ref_key] = copybook_content

                # Apply REPLACING if specified
                if ref.replacing:
                    copybook_content = self._apply_replacing(
                        copybook_content, ref.replacing
                    )

                # Find and replace COPY statement
                copy_pattern = re.compile(
                    rf"COPY\s+{re.escape(ref.name)}"
                    r"(?:\s+(?:OF|IN)\s+[A-Z][A-Z0-9-]*)?"
                    r"(?:\s+REPLACING\s+.+?)?"
                    r"\s*\.",
                    re.IGNORECASE | re.DOTALL,
                )

                # Add comment markers around inlined content
                replacement = (
                    f"      * COPY {ref.name} - BEGIN (from {ref.resolved_path.name})\n"
                    f"{copybook_content}\n"
                    f"      * COPY {ref.name} - END"
                )

                result = copy_pattern.sub(replacement, result, count=1)

            except Exception as e:
                warnings.append(
                    f"Error reading copybook '{ref.name}': {e}"
                )

        return result

    def _apply_replacing(self, content: str, replacing_clause: str) -> str:
        """Apply REPLACING clause to copybook content."""
        # Parse REPLACING clause: pattern BY replacement
        # Format: ==old-text== BY ==new-text==
        # Or: old-word BY new-word

        result = content

        # Pattern for pseudo-text replacement: ==text== BY ==text==
        pseudo_pattern = re.compile(
            r"==(.+?)==\s+BY\s+==(.+?)==",
            re.IGNORECASE | re.DOTALL,
        )

        for match in pseudo_pattern.finditer(replacing_clause):
            old_text = match.group(1).strip()
            new_text = match.group(2).strip()
            result = result.replace(old_text, new_text)

        # Pattern for word replacement: word BY word
        word_pattern = re.compile(
            r"([A-Z][A-Z0-9-]*)\s+BY\s+([A-Z][A-Z0-9-]*)",
            re.IGNORECASE,
        )

        for match in word_pattern.finditer(replacing_clause):
            old_word = match.group(1)
            new_word = match.group(2)
            # Replace whole words only
            result = re.sub(
                rf"\b{re.escape(old_word)}\b",
                new_word,
                result,
                flags=re.IGNORECASE,
            )

        return result
