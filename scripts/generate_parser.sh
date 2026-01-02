#!/bin/bash
# Generate Python parser from ANTLR grammar files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
GRAMMAR_DIR="$PROJECT_DIR/grammars"
OUTPUT_DIR="$PROJECT_DIR/src/coqu/parser/generated"

echo "Generating ANTLR Python parser..."
echo "Grammar dir: $GRAMMAR_DIR"
echo "Output dir: $OUTPUT_DIR"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Generate parser for main grammar
echo "Generating Cobol85 parser..."
antlr4 -Dlanguage=Python3 -visitor -o "$OUTPUT_DIR" "$GRAMMAR_DIR/Cobol85.g4"

# Generate parser for preprocessor grammar
echo "Generating Cobol85Preprocessor parser..."
antlr4 -Dlanguage=Python3 -visitor -o "$OUTPUT_DIR" "$GRAMMAR_DIR/Cobol85Preprocessor.g4"

# Create __init__.py for the generated package
cat > "$OUTPUT_DIR/__init__.py" << 'EOF'
# Auto-generated ANTLR parser code
from .Cobol85Lexer import Cobol85Lexer
from .Cobol85Parser import Cobol85Parser
from .Cobol85Listener import Cobol85Listener
from .Cobol85Visitor import Cobol85Visitor
from .Cobol85PreprocessorLexer import Cobol85PreprocessorLexer
from .Cobol85PreprocessorParser import Cobol85PreprocessorParser
from .Cobol85PreprocessorListener import Cobol85PreprocessorListener
from .Cobol85PreprocessorVisitor import Cobol85PreprocessorVisitor

__all__ = [
    "Cobol85Lexer",
    "Cobol85Parser",
    "Cobol85Listener",
    "Cobol85Visitor",
    "Cobol85PreprocessorLexer",
    "Cobol85PreprocessorParser",
    "Cobol85PreprocessorListener",
    "Cobol85PreprocessorVisitor",
]
EOF

echo "Parser generation complete!"
echo "Generated files:"
ls -la "$OUTPUT_DIR"
