# coqu - COBOL Query Tool

## Specification Document

**Version**: 1.0.0
**Status**: Final Draft
**Date**: 2025-12-31

---

## 1. Executive Summary

**coqu** (COBOL Query) is a Python-based COBOL source code analysis tool that leverages ANTLR4 parsing to provide an interactive query interface for understanding undocumented COBOL codebases.

### Primary Use Case

Enable developers, modernization teams, auditors, and maintainers to quickly understand and navigate complex, undocumented COBOL applications through an intuitive REPL interface.

### Key Features

- **Interactive REPL** with `/` command prefix pattern and scriptable execution
- **Multi-file workspaces** supporting simultaneous analysis of programs and copybooks
- **Granular extraction** of code blocks (names and full source bodies)
- **Full copybook resolution** with dependency tracking and REPLACING support
- **Extreme scale support** for files up to 2+ million lines
- **AST caching** for fast subsequent access

---

## 2. Technical Foundation

### 2.1 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Parser Generator | ANTLR4 | 4.13+ |
| Grammar Source | [antlr/grammars-v4/cobol85](https://github.com/antlr/grammars-v4/tree/master/cobol85) | Latest |
| Runtime Language | Python | 3.10+ |
| ANTLR Runtime | antlr4-python3-runtime | 4.13+ |
| AST Serialization | MessagePack | msgpack |
| Analytics (Future) | DuckDB + Parquet | v2+ |

### 2.2 Supported COBOL Dialects

| Dialect | Support Level | Notes |
|---------|--------------|-------|
| COBOL-85 (ANSI) | Full | Primary target, NIST compliant grammar |
| IBM Enterprise COBOL | Full | EXEC SQL, EXEC CICS support |
| COBOL-2002 | Partial | Core features only |

### 2.3 Grammar Architecture

The COBOL85 grammar uses a two-phase parsing approach:

```
+----------------------------------------------------------+
|                   Source COBOL Files                      |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|         Phase 1: Preprocessor (Cobol85Preprocessor.g4)   |
|  - COPY statement resolution                              |
|  - REPLACE directive processing                           |
|  - EXEC SQL/CICS block handling                           |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|         Phase 2: Main Parser (Cobol85.g4)                |
|  - Full syntactic parsing                                 |
|  - AST generation with position tracking                  |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|                   Query-Ready AST                         |
+----------------------------------------------------------+
```

---

## 3. Performance Architecture

### 3.1 The 2M Line Challenge

Target: Handle single COBOL files with 2+ million lines on machines with 32GB RAM.

### 3.2 Hybrid Parsing Strategy

```
+----------------------------------------------------------+
|              HYBRID PARSING STRATEGY                      |
+----------------------------------------------------------+
|                                                           |
|  PHASE 1: STRUCTURAL INDEX                                |
|  -------------------------                                |
|  - Regex-based scan for DIVISION, SECTION, paragraphs     |
|  - Fast: ~5-10 seconds for 2M lines                       |
|  - Memory: ~10MB for 2M lines                             |
|  - Used for: Listing, navigation, line-range lookup       |
|                                                           |
|  PHASE 2: FULL ANTLR PARSE                                |
|  -------------------------                                |
|  - Complete syntactic analysis                            |
|  - Options:                                               |
|    A) Parse specific segment (paragraph/section)          |
|    B) Full file parse (--full-parse flag)                 |
|  - Used for: Statement analysis, semantic queries         |
|                                                           |
|  ACCURACY GUARANTEE                                       |
|  ------------------                                       |
|  - Index answers: "what exists?" (names, locations)       |
|  - ANTLR answers: "what does it do?" (semantics)          |
|  - Regex NEVER used for semantic questions                |
|                                                           |
+----------------------------------------------------------+
```

### 3.3 Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Index 2M line file | < 10 seconds | Structural scan only |
| Load cached AST | < 2 seconds | MessagePack deserialize |
| Query response | < 500ms | Indexed queries |
| Memory ceiling | 32GB | Full parse of large files |
| Cache overhead | ~2x source size | MessagePack AST |

### 3.4 CLI Performance Flags

```bash
coqu --full-parse          # Force complete ANTLR parse upfront
coqu --index-only          # Lightweight mode, parse on demand
coqu                       # Auto-detect based on file size
coqu --memory-limit 16G    # Set memory ceiling
```

---

## 4. Storage Architecture

### 4.1 Directory Structure

```
~/.coqu/
+-- config.toml              # User configuration
+-- history                  # Command history (text)
+-- cache/                   # V1: Per-file AST cache
|   +-- <sha256>.ast         # MessagePack serialized AST
|   +-- ...
+-- index/                   # V2+: Multi-program analytics
    +-- programs.parquet     # Program metadata
    +-- symbols.parquet      # All symbols across programs
    +-- references.parquet   # Cross-references
    +-- copybooks.parquet    # Copybook usage
```

### 4.2 AST Cache (V1)

| Aspect | Decision |
|--------|----------|
| Format | MessagePack |
| Key | SHA256 hash of source file |
| Location | `~/.coqu/cache/<hash>.ast` |
| Invalidation | Hash mismatch with source |
| Contents | `{meta: {...}, ast: {...}}` |

**Cache metadata:**
```python
{
    "meta": {
        "source_path": "/path/to/program.cbl",
        "source_hash": "abc123...",
        "lines": 45000,
        "cached_at": "2025-12-31T10:30:00Z",
        "coqu_version": "1.0.0"
    },
    "ast": { ... }  # Serialized AST
}
```

### 4.3 Multi-Program Index (V2+)

For cross-program analytics, Parquet + DuckDB:

```sql
-- programs.parquet
program_id | file_path | file_hash | lines | indexed_at

-- symbols.parquet
symbol_id | program_id | name | type | division | line_start | line_end

-- references.parquet
program_id | symbol_name | ref_type | line | context

-- copybooks.parquet
program_id | copybook_name | resolved_path | line | replacing
```

**Example queries (future):**
```sql
-- Which programs use CUSTFILE copybook?
SELECT DISTINCT file_path FROM programs p
JOIN copybooks c ON p.program_id = c.program_id
WHERE c.copybook_name = 'CUSTFILE';

-- Find all EXEC CICS across codebase
SELECT file_path, line, context FROM references r
JOIN programs p ON r.program_id = p.program_id
WHERE r.ref_type = 'cics';
```

---

## 5. Configuration

### 5.1 Config File: `~/.coqu/config.toml`

```toml
[general]
# Default parsing mode: "auto", "full", "index-only"
parse_mode = "auto"

# Memory limit for full parsing
memory_limit = "32G"

# Enable debug output (full ANTLR diagnostics)
debug = false

[copybooks]
# Copybook search paths (searched in order)
paths = [
    "/opt/cobol/copybooks",
    "/opt/cobol/includes",
    "./copybooks"
]

[cache]
# Cache directory (default: ~/.coqu/cache)
directory = "~/.coqu/cache"

# Maximum cache size (0 = unlimited)
max_size = "10G"

[repl]
# Enable syntax highlighting
highlight = true

# History file location
history_file = "~/.coqu/history"

# Maximum history entries
history_size = 1000
```

---

## 6. CLI Interface

### 6.1 Invocation Modes

```bash
coqu                          # Interactive REPL
coqu --script analysis.coqu   # Run script file, then exit
coqu --json                   # Machine mode (future: VS Code)
coqu paragraphs program.cbl   # One-shot command
```

### 6.2 Command Structure

Commands are divided into two categories:

| Prefix | Type | Purpose |
|--------|------|---------|
| `/` | Meta commands | Workspace, settings, system |
| (none) | Query commands | Data extraction, search |

### 6.3 Meta Commands (/ prefix)

#### Workspace Management

```
/load <file|glob>           Load COBOL source file(s)
/load *.cbl                 Load all .cbl files in current directory
/load /path/to/prog.cbl     Load specific file

/unload <file>              Remove file from workspace
/unload all                 Clear entire workspace

/reload                     Reload all files, invalidate cache
/reload <file>              Reload specific file

/workspace                  Show all loaded files with stats
/workspace --verbose        Show detailed file information
```

#### Copybook Configuration

```
/copylib <path>             Add copybook search path
/copylib --list             Show current copybook paths
/copylib --clear            Clear all copybook paths
```

#### Cache Management

```
/cache status               Show cache usage statistics
/cache clear                Delete all cached ASTs
/cache clear <file>         Delete cache for specific file
/cache rebuild              Re-parse and re-cache all loaded files
```

#### Settings

```
/set debug on|off           Toggle debug mode (full ANTLR errors)
/set parse-mode <mode>      Set: auto, full, index-only
/set                        Show all current settings
```

#### Session

```
/help                       Show all commands
/help <command>             Show help for specific command
/history                    Show command history
/quit                       Exit coqu (also: /exit, /q)
```

### 6.4 Query Commands (no prefix)

#### Structure Queries

```
divisions                   List all divisions present
division <name>             Show division metadata
division <name> --body      Show full division source code

sections                    List all sections
sections --division <name>  List sections in specific division
section <name>              Show section metadata
section <name> --body       Show full section source code

paragraphs                  List all paragraph names
paragraphs --section <name> List paragraphs in specific section
paragraph <name>            Show paragraph metadata (lines, size)
paragraph <name> --body     Show full paragraph source code
paragraph <name> --calls    Show paragraphs called from this one
paragraph <name> --called-by Show paragraphs that call this one
```

#### Data Structure Queries

```
working-storage             List all WORKING-STORAGE items
working-storage --level 01  Only level-01 items
working-storage --level 88  Condition names (88-level)

variable <name>             Show variable definition details
variable <name> --body      Show full data description entry
variable <name> --references Show all PROCEDURE DIVISION uses

file-section                List FD entries and record layouts
linkage                     List LINKAGE SECTION items
```

#### Copybook Queries

```
copybooks                   List all COPY statements found
copybook <name>             Show copybook usage details
copybook <name> --contents  Show resolved copybook source
copybook <name> --used-by   Show programs using this copybook
copybook-deps               Show copybook dependency graph
copybook-deps --format dot  Export as GraphViz DOT format
```

#### Statement Queries

```
calls                       List all CALL statements
calls --external            External program calls only
calls --program <name>      Calls to specific program

performs                    List all PERFORM statements
performs --thru             PERFORM...THRU statements only
performs --paragraph <name> PERFORMs of specific paragraph

moves                       List MOVE statements
moves --to <variable>       MOVEs targeting specific variable
moves --from <variable>     MOVEs from specific variable

sql                         List EXEC SQL blocks
sql --body                  Show SQL block contents
cics                        List EXEC CICS blocks
cics --body                 Show CICS block contents
```

#### Comment Queries

```
comments                    List all comments in source
comments --orphan           Comments not associated with code
comments --for <element>    Comments for specific element
comments --header           Program header comments only
```

#### Search Queries

```
find <pattern>              Regex search across loaded sources
find <pattern> --in <scope> Scoped search (PROCEDURE, DATA, etc.)
find "MOVE.*CUSTOMER"       Example: find MOVE statements

references <name>           Find all references to identifier
references <name> --writes  Only assignments to variable
references <name> --reads   Only reads of variable

where-used <copybook>       Programs using specific copybook
```

### 6.5 Output Modifiers

All query commands support these modifiers:

```
--body                      Include source code (not just names)
--line-numbers              Show line numbers in output
--count                     Show count only, not details
> filename                  Redirect output to file
>> filename                 Append output to file
```

---

## 7. Script Files

### 7.1 Script Format

Script files use `.coqu` extension:

```coqu
# analysis.coqu - Batch analysis script
# Comments start with #

# Configuration
/copylib /opt/cobol/copybooks
/copylib /opt/cobol/includes

# Load sources
/load /opt/cobol/programs/*.cbl

# Generate reports
/workspace > workspace_inventory.txt
copybook-deps --format dot > copybook_dependencies.dot

# Extract key paragraphs
paragraph 0000-MAIN-LOGIC --body > main_logic.txt
paragraph 9000-ERROR-HANDLER --body > error_handling.txt

# Find potential issues
find "GO TO" > goto_usage.txt
find "ALTER" > alter_usage.txt

# Cross-reference analysis
references WS-RETURN-CODE > return_code_refs.txt
```

### 7.2 Script Execution

```bash
coqu --script analysis.coqu           # Run script and exit
coqu --script analysis.coqu --dry-run # Validate without executing
```

Within REPL:
```
coqu> /run analysis.coqu
coqu> @analysis.coqu                   # Shorthand
```

---

## 8. Error Handling

### 8.1 Error Modes

| Mode | Trigger | Output |
|------|---------|--------|
| Normal | Default | Summary: "Line 45: syntax error near 'MOVE'" |
| Debug | `/set debug on` | Full ANTLR diagnostic with stack trace |

### 8.2 Copybook Resolution

When a copybook cannot be resolved:

```
WARNING: Copybook 'CUSTFILE' not found in search paths
         Referenced at line 47 in CUSTMAINT.cbl
         Continuing with unresolved reference.
```

The parse continues with a placeholder. Queries that depend on the copybook contents will note the unresolved status.

### 8.3 Parse Errors

```
ERROR: Parse failed for CUSTMAINT.cbl
       Line 1245: mismatched input 'MOEV' expecting {'MOVE', 'ADD', ...}

Hint: Use '/set debug on' for full diagnostic output
```

---

## 9. Module Structure

```
coqu/
+-- __init__.py
+-- __main__.py                 # Entry point
+-- cli.py                      # CLI argument parsing
+-- version.py                  # Version info
|
+-- parser/
|   +-- __init__.py
|   +-- generated/              # ANTLR generated code
|   |   +-- Cobol85Lexer.py
|   |   +-- Cobol85Parser.py
|   |   +-- Cobol85Listener.py
|   |   +-- Cobol85Visitor.py
|   |   +-- Cobol85PreprocessorLexer.py
|   |   +-- Cobol85PreprocessorParser.py
|   +-- preprocessor.py         # COPY/REPLACE handling
|   +-- parser.py               # Main parser wrapper
|   +-- indexer.py              # Lightweight structural indexer
|   +-- ast.py                  # AST node definitions
|
+-- workspace/
|   +-- __init__.py
|   +-- workspace.py            # Workspace manager
|   +-- program.py              # Program representation
|   +-- copybook.py             # Copybook handling
|
+-- cache/
|   +-- __init__.py
|   +-- manager.py              # Cache operations
|   +-- serializer.py           # MessagePack serialization
|
+-- query/
|   +-- __init__.py
|   +-- engine.py               # Query execution
|   +-- parser.py               # Query command parser
|   +-- commands/               # Individual query handlers
|   |   +-- __init__.py
|   |   +-- divisions.py
|   |   +-- sections.py
|   |   +-- paragraphs.py
|   |   +-- variables.py
|   |   +-- copybooks.py
|   |   +-- statements.py
|   |   +-- comments.py
|   |   +-- search.py
|   +-- results.py              # Result formatting
|
+-- repl/
|   +-- __init__.py
|   +-- repl.py                 # Main REPL loop
|   +-- completer.py            # Tab completion
|   +-- history.py              # Command history
|   +-- script.py               # Script execution
|
+-- config/
|   +-- __init__.py
|   +-- config.py               # Configuration management
|
+-- utils/
    +-- __init__.py
    +-- source.py               # Source file handling
    +-- encoding.py             # Character encoding detection
```

---

## 10. Dependencies

### 10.1 Runtime Dependencies

```
antlr4-python3-runtime>=4.13.0   # ANTLR parser runtime
msgpack>=1.0.0                   # AST serialization
prompt-toolkit>=3.0.0            # REPL interface
tomli>=2.0.0                     # Config file parsing (Python <3.11)
```

### 10.2 Development Dependencies

```
antlr4-tools>=0.2                # Grammar compilation
pytest>=7.0.0                    # Testing
pytest-cov>=4.0.0                # Coverage
black>=23.0.0                    # Code formatting
mypy>=1.0.0                      # Type checking
ruff>=0.1.0                      # Linting
```

### 10.3 Future Dependencies (V2+)

```
duckdb>=0.9.0                    # Multi-program analytics
pyarrow>=14.0.0                  # Parquet file support
```

---

## 11. Implementation Roadmap

### 11.1 Version 1.0 (MVP)

**Scope**: Core parsing + REPL + Essential queries

```
Phase 1: Parser Foundation (Week 1-2)
+-- Generate Python parser from ANTLR grammars
+-- Implement preprocessor (COPY resolution)
+-- Create AST wrapper classes
+-- Implement structural indexer
+-- Unit tests for parser

Phase 2: Workspace & Cache (Week 3)
+-- Workspace management (load/unload)
+-- MessagePack cache implementation
+-- Copybook path management
+-- Multi-file handling

Phase 3: Query Engine (Week 4-5)
+-- Query command parser
+-- Division/section/paragraph queries
+-- Working-storage queries
+-- --body extraction for all
+-- Basic search (find, references)
+-- Statement queries (calls, performs)

Phase 4: REPL & Polish (Week 6)
+-- Interactive REPL with prompt-toolkit
+-- Tab completion
+-- Command history
+-- Script execution
+-- Error handling modes
+-- Documentation
```

### 11.2 Version 1.1

- Enhanced copybook handling (nested, REPLACING)
- Comment queries
- Copybook dependency graphs (DOT export)
- Performance optimization for large files

### 11.3 Version 1.2

- Windows compatibility
- Character encoding detection (EBCDIC)
- Additional output formats if needed
- Cache size management

### 11.4 Version 2.0 (Multi-Program)

- Parquet index generation
- DuckDB integration
- Cross-program queries
- Impact analysis
- Dead code detection

### 11.5 Version 3.0 (VS Code)

- JSON/MessagePack machine protocol
- VS Code extension
- Outline view integration
- Hover information
- Go-to-definition

---

## 12. Advanced Features Roadmap

### Phase 2: Semantic Analysis

| Feature | Description |
|---------|-------------|
| Type Resolution | Resolve PIC clauses to actual types |
| Scope Analysis | Variable scope and visibility |
| Cross-Reference | Full cross-reference generation |
| Unused Detection | Find unused variables/paragraphs |

### Phase 3: Data Flow Analysis

| Feature | Description |
|---------|-------------|
| Variable Tracing | Track data flow through program |
| Impact Analysis | What changes if I modify X? |
| Dead Code | Unreachable paragraph detection |
| Slice Extraction | Extract code affecting variable |

### Phase 4: Control Flow Analysis

| Feature | Description |
|---------|-------------|
| Call Graph | Visualize PERFORM/CALL relationships |
| Execution Paths | Possible paths through program |
| Complexity Metrics | Cyclomatic complexity per paragraph |
| Loop Detection | Identify loop structures |

### Phase 5: Business Rule Extraction

| Feature | Description |
|---------|-------------|
| Condition Mining | Extract conditions from IF statements |
| 88-Level Analysis | Document condition names semantically |
| Rule Templates | Pattern-based rule extraction |
| Natural Language | Generate rule descriptions |

### Phase 6: Modernization Assistance

| Feature | Description |
|---------|-------------|
| Pseudo-Code | Readable algorithm extraction |
| API Identification | Identify service boundaries |
| Data Model Export | ERD from record layouts |
| Migration Stubs | Target language skeletons |

### Phase 7: IDE Integration

| Feature | Description |
|---------|-------------|
| LSP Server | Language Server Protocol |
| VS Code Extension | Full IDE integration |
| JSON API | Programmatic access |
| CI/CD Integration | Static analysis in pipelines |

### Phase 8: Multi-Program Analysis

| Feature | Description |
|---------|-------------|
| Application Mapping | Full application call graph |
| Copybook Impact | Programs affected by changes |
| Data Lineage | Track data across programs |
| Component Detection | Identify reusable components |

---

## 13. Sample Session

```
$ coqu
coqu v1.0.0 - COBOL Query Tool
Type '/help' for available commands.

coqu> /copylib /opt/cobol/copybooks
Added: /opt/cobol/copybooks

coqu> /load /opt/cobol/programs/CUSTMAINT.cbl
Loaded: CUSTMAINT.cbl (2,847 lines, 3 copybooks resolved)

coqu> divisions
IDENTIFICATION DIVISION    (lines 1-15)
ENVIRONMENT DIVISION       (lines 16-45)
DATA DIVISION              (lines 46-890)
PROCEDURE DIVISION         (lines 891-2847)

coqu> paragraphs
0000-MAIN-LOGIC
1000-INITIALIZE
2000-PROCESS-INPUT
2100-VALIDATE-CUSTOMER
2200-UPDATE-RECORD
3000-TERMINATE
9000-ERROR-HANDLER
9100-ABEND-ROUTINE

coqu> paragraph 2100-VALIDATE-CUSTOMER --body
       2100-VALIDATE-CUSTOMER.
           IF CUST-ID = SPACES
               MOVE 'E001' TO ERR-CODE
               MOVE 'Customer ID required' TO ERR-MSG
               PERFORM 9000-ERROR-HANDLER
           END-IF.
           IF CUST-NAME = SPACES
               MOVE 'E002' TO ERR-CODE
               MOVE 'Customer name required' TO ERR-MSG
               PERFORM 9000-ERROR-HANDLER
           END-IF.
           MOVE 'Y' TO VALID-FLAG.

coqu> copybooks
COPY Statement              Copybook         Status
----------------------------------------------------
Line 47:  COPY CUSTFILE.    CUSTFILE.cpy     Resolved
Line 102: COPY ERRORCPY.    ERRORCPY.cpy     Resolved
Line 340: COPY LOGREC.      LOGREC.cpy       Resolved

coqu> find "PERFORM.*ERROR" --in PROCEDURE
Line 856:     PERFORM 9000-ERROR-HANDLER
Line 862:     PERFORM 9000-ERROR-HANDLER
Line 1245:    PERFORM 9100-ABEND-ROUTINE

coqu> working-storage --level 01
01 WS-SWITCHES.
01 WS-COUNTERS.
01 WS-CUSTOMER-RECORD.
01 WS-ERROR-HANDLING.
01 WS-WORK-AREAS.

coqu> variable WS-CUSTOMER-RECORD --body
       01 WS-CUSTOMER-RECORD.
          05 CUST-ID              PIC X(10).
          05 CUST-NAME            PIC X(50).
          05 CUST-ADDRESS.
             10 CUST-STREET       PIC X(30).
             10 CUST-CITY         PIC X(20).
             10 CUST-STATE        PIC XX.
             10 CUST-ZIP          PIC X(10).
          05 CUST-BALANCE         PIC S9(9)V99 COMP-3.

coqu> paragraph 9000-ERROR-HANDLER --called-by
0000-MAIN-LOGIC          (line 903)
2100-VALIDATE-CUSTOMER   (line 856)
2100-VALIDATE-CUSTOMER   (line 862)
2200-UPDATE-RECORD       (line 1102)

coqu> /quit
Goodbye!
```

---

## 14. Appendices

### A. Grammar Files

**Source Repository:**
```
https://github.com/antlr/grammars-v4/tree/master/cobol85
```

**Required Files:**
- `Cobol85.g4` - Main parser grammar
- `Cobol85Preprocessor.g4` - Preprocessor grammar

**Generation Command:**
```bash
antlr4 -Dlanguage=Python3 -visitor Cobol85.g4
antlr4 -Dlanguage=Python3 -visitor Cobol85Preprocessor.g4
```

### B. File Extensions

| Extension | Purpose |
|-----------|---------|
| `.cbl`, `.cob` | COBOL source programs |
| `.cpy`, `.copy` | Copybook files |
| `.coqu` | coqu script files |
| `.ast` | Cached AST (MessagePack) |
| `.parquet` | Multi-program index (V2+) |

### C. Environment Variables

```bash
COQU_HOME          # Override ~/.coqu directory
COQU_CONFIG        # Override config file location
COQU_COPYLIB       # Additional copybook path (colon-separated)
COQU_DEBUG         # Set to "1" for debug mode
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-31 | coqu Team | Initial specification |

---

End of Specification
