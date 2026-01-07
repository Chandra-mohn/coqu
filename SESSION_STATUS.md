# coqu Project Status - January 2, 2026

## Current State: MVP Complete + Optimizations

**All 82 tests passing**

## Recent Session Work

### 1. Progress Bar Simplification (Completed)
- Replaced complex percentage-based progress bar with simpler feedback
- Created `Spinner` class: ASCII spinner (`| / - \`) for single file loading
- Created `ProgressCounter` class: File count progress for batch operations
- Removed `progress_callback` from entire parser/indexer chain
- Updated REPL commands to use new spinner/progress utilities

### 2. Chunk-Based Hybrid Parsing (Completed)
- Pass 1: Regex structural indexer (always runs, fast)
- Pass 2: On-demand chunk analysis for specific paragraphs/sections
- `ChunkAnalyzer` extracts PERFORM, CALL, MOVE, GO TO targets
- Added `--analyze` flag to paragraph/performs/calls/moves commands

### 3. Panvalet Format Support (Completed)
- `detect_format()` identifies panvalet, sequence, or standard format
- `normalize_format()` strips version markers for ANTLR compatibility
- Auto-normalization during preprocessing

## Performance Metrics (User's 250K Line File)
- **Pass 1 (structural index)**: 54 seconds
- **Cache hit**: Instantaneous
- **Memory usage**: Few hundred MB (acceptable)
- **Throughput**: ~4,600 lines/sec

## Open Investigation: Paragraph Detection
User's 250K line file shows:
- **618 sections detected** (correct)
- **0 paragraphs detected** <- Needs investigation

Possible causes:
1. Code uses section-based organization (no paragraphs)
2. Paragraph regex not matching specific format (sequence numbers, spacing)
3. Paragraphs may be inside sections with different naming patterns

**Next steps when resuming:**
- Get sample snippet of section structure to verify paragraph format
- May need to adjust `PARAGRAPH_PATTERN` regex in `indexer.py`
- Consider enhancing section-level analysis to match paragraph features
- Add `section <name> --body --analyze` similar to paragraph command

## Key Files Modified This Session
- `src/coqu/utils/spinner.py` (NEW)
- `src/coqu/parser/indexer.py` (simplified, removed progress callbacks)
- `src/coqu/parser/cobol_parser.py` (removed progress_callback)
- `src/coqu/workspace/workspace.py` (uses Spinner/ProgressCounter)
- `src/coqu/repl/commands.py` (updated load/loaddir/reload)
- `src/coqu/parser/chunk_analyzer.py` (NEW - chunk-based semantic analysis)
- `src/coqu/utils/__init__.py` (fixed missing module reference)

## Architecture Summary
```
Pass 1 (Always): Regex Indexer -> Divisions, Sections, Paragraphs, Copybooks
Pass 2 (On-Demand): ChunkAnalyzer -> PERFORM/CALL/MOVE targets for specific chunk
Cache: MessagePack serialization of CobolProgram AST
```

## Test Coverage
- 82 tests covering parser, workspace, queries, chunk analysis
- Format detection/normalization tests for Panvalet format
- Chunk analyzer speed test (100 analyses < 1 second)
