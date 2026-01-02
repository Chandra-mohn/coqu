# coqu - COBOL Query

An ANTLR4-based COBOL parser with interactive REPL for querying COBOL source code structures.

## Features

- Parse COBOL-85 and IBM Enterprise COBOL programs
- Interactive REPL with tab completion and history
- Query divisions, sections, paragraphs, and data items
- Copybook resolution with REPLACING support
- AST caching with MessagePack for fast reloading
- Script execution for batch operations
- Handles large files (tested with 2M+ line programs)

## Installation

```bash
pip install coqu
```

## Quick Start

### Interactive REPL

```bash
# Start REPL
coqu

# Load files on startup
coqu program.cbl copybooks/

# Add copybook path
coqu --copybook-path /path/to/copybooks program.cbl
```

### Commands in REPL

```
coqu> /load MYPROGRAM.cbl
Loaded MYPROGRAM: MYPROGRAM (5432 lines)

coqu> divisions
IDENTIFICATION DIVISION (lines 1-15)
DATA DIVISION (lines 16-200)
PROCEDURE DIVISION (lines 201-5432)

coqu> paragraphs
0000-MAIN (line 210)
1000-INIT (line 250)
2000-PROCESS (line 380)
...

coqu> paragraph 2000-PROCESS --body
2000-PROCESS:
  Location: lines 380-450
  Performs: 2100-VALIDATE, 2200-UPDATE
  Calls: AUDITLOG
  --- Body ---
  2000-PROCESS.
      PERFORM 2100-VALIDATE
      ...

coqu> find MOVE.*TO
MYPROGRAM:120: MOVE WS-INPUT TO WS-OUTPUT
MYPROGRAM:245: MOVE SPACES TO WS-BUFFER
...

coqu> /quit
```

### Single Query Mode

```bash
# Execute a single query
coqu -c "paragraphs" MYPROGRAM.cbl

# JSON output
coqu -c "divisions" -o json MYPROGRAM.cbl
```

### Script Execution

```bash
# Execute a .coqu script
coqu -s analysis.coqu MYPROGRAM.cbl
```

## Query Commands

| Command | Description |
|---------|-------------|
| divisions | List all divisions |
| division NAME | Show division details |
| paragraphs | List all paragraphs |
| paragraph NAME --body | Show paragraph with source |
| working-storage | List WORKING-STORAGE items |
| variable NAME | Show variable details |
| copybooks | List COPY statements |
| copybook NAME | Show copybook details |
| calls | List CALL statements |
| performs | List PERFORM statements |
| find PATTERN | Search source code |
| references NAME | Find all references |
| where-used NAME | Find callers of paragraph |

## Meta Commands

| Command | Description |
|---------|-------------|
| /load FILE | Load a COBOL file |
| /loaddir DIR | Load all files in directory |
| /unload NAME | Unload a program |
| /reload [NAME] | Reload program(s) |
| /list | List loaded programs |
| /copypath PATH | Add copybook search path |
| /info [NAME] | Show program info |
| /cache | Show cache statistics |
| /help [CMD] | Show help |
| /quit | Exit REPL |

## Configuration

Create `.coqu.toml` in your project or `~/.config/coqu/config.toml`:

```toml
copybook_paths = [
    "/path/to/copybooks",
    "./copybooks"
]

[cache]
enabled = true
max_size_mb = 500

[parser]
use_indexer_only = false
```

## Development

```bash
# Clone repository
git clone https://github.com/your-org/coqu
cd coqu

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Regenerate ANTLR parser
./scripts/generate_parser.sh
```

## License

MIT
