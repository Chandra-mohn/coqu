#!/bin/bash
# Build standalone coqu executable using PyInstaller
# Usage: ./scripts/build-exe.sh
set -e
cd "$(dirname "$0")/.."

# Cross-platform Python detection (python on Windows, python3 on Mac/Linux)
if command -v python &> /dev/null && python --version 2>&1 | grep -q "Python 3"; then
    PYTHON=python
elif command -v python3 &> /dev/null; then
    PYTHON=python3
else
    echo "Error: Python 3 not found"; exit 1
fi

echo "==> Building coqu executable (using $PYTHON)"

# Ensure PyInstaller is installed
if ! $PYTHON -m PyInstaller --version &> /dev/null; then
    echo "==> Installing PyInstaller..."
    $PYTHON -m pip install pyinstaller
fi

# Create entry point
cat > coqu_entry.py << 'EOF'
from coqu.cli import main
import sys
if __name__ == '__main__':
    sys.exit(main())
EOF

# Build with PyInstaller (onedir for faster startup)
# Include all coqu submodules and required dependencies
# Exclude large unnecessary libraries to reduce bundle size
$PYTHON -m PyInstaller coqu_entry.py \
    --onedir \
    --noconfirm \
    --name coqu \
    --distpath dist/bin \
    --workpath build \
    --specpath . \
    --console \
    --paths src \
    --collect-submodules coqu \
    --collect-submodules antlr4 \
    --hidden-import coqu.cli \
    --hidden-import coqu.version \
    --hidden-import coqu.config \
    --hidden-import coqu.workspace \
    --hidden-import coqu.cache \
    --hidden-import coqu.query \
    --hidden-import coqu.repl \
    --hidden-import coqu.parser \
    --hidden-import coqu.parser.generated \
    --hidden-import coqu.utils \
    --hidden-import antlr4 \
    --hidden-import antlr4.error.ErrorListener \
    --hidden-import msgpack \
    --hidden-import prompt_toolkit \
    --hidden-import prompt_toolkit.completion \
    --hidden-import prompt_toolkit.history \
    --hidden-import prompt_toolkit.styles \
    --hidden-import tomli \
    --exclude-module numpy \
    --exclude-module scipy \
    --exclude-module pandas \
    --exclude-module matplotlib \
    --exclude-module PIL \
    --exclude-module tkinter \
    --exclude-module _tkinter \
    --exclude-module tcl \
    --exclude-module tk \
    --exclude-module IPython \
    --exclude-module jupyter \
    --exclude-module notebook \
    --exclude-module pytest \
    --exclude-module setuptools \
    --exclude-module pip \
    --exclude-module duckdb \
    --exclude-module pyarrow \
    --log-level ERROR

# Cleanup
rm -f coqu_entry.py coqu.spec
rm -rf build

echo "==> Done: dist/bin/coqu/"
dist/bin/coqu/coqu --version
