#!/usr/bin/env python3
"""Quick test for mainframe format parsing."""
from coqu.parser.indexer import StructuralIndexer

# Mainframe-format COBOL source
MAINFRAME_SOURCE = """000100 IDENTIFICATION DIVISION.
000200 PROGRAM-ID. MAINFRAME.
000300 AUTHOR. COQU-TEST.
000400*
000500* Sample mainframe-format COBOL with sequence numbers
000600*
000700 ENVIRONMENT DIVISION.
000800 INPUT-OUTPUT SECTION.
000900 FILE-CONTROL.
001000     SELECT MASTER-FILE ASSIGN TO MASTERIN.
001100
001200 DATA DIVISION.
001300 FILE SECTION.
001400 FD MASTER-FILE.
001500 01 MASTER-RECORD.
001600    05 MR-KEY              PIC X(10).
001700    05 MR-DATA             PIC X(80).
001800
001900 WORKING-STORAGE SECTION.
002000 01 WS-WORK-AREAS.
002100    05 WS-EOF-FLAG         PIC 9 VALUE 0.
002200       88 WS-EOF           VALUE 1.
002300    05 WS-COUNT            PIC 9(7) VALUE 0.
002400
002500 COPY COMAREA.
002600
002700 LINKAGE SECTION.
002800 01 DFHCOMMAREA            PIC X(100).
002900
003000 PROCEDURE DIVISION.
003100
003200 0000-MAIN.
003300     PERFORM 1000-INITIALIZE
003400     PERFORM 2000-PROCESS UNTIL WS-EOF
003500     PERFORM 9000-TERMINATE
003600     GOBACK.
003700
003800 1000-INITIALIZE.
003900     OPEN INPUT MASTER-FILE
004000     PERFORM 1100-READ-FIRST.
004100
004200 1100-READ-FIRST.
004300     READ MASTER-FILE
004400         AT END SET WS-EOF TO TRUE
004500     END-READ.
004600
004700 2000-PROCESS.
004800     ADD 1 TO WS-COUNT
004900     PERFORM 2100-VALIDATE
005000     READ MASTER-FILE
005100         AT END SET WS-EOF TO TRUE
005200     END-READ.
005300
005400 2100-VALIDATE.
005500     IF MR-KEY = SPACES
005600         MOVE 'INVALID' TO MR-DATA
005700     END-IF.
005800
005900 9000-TERMINATE.
006000     CLOSE MASTER-FILE
006100     DISPLAY 'DONE'.
"""

def test_mainframe_format():
    indexer = StructuralIndexer()
    index = indexer.index(MAINFRAME_SOURCE)

    print("=== Mainframe Format Test ===\n")

    # Test divisions
    divisions = index.get_division_names()
    print(f"Divisions found: {len(divisions)}")
    for d in divisions:
        print(f"  - {d}")

    assert len(divisions) == 4, f"Expected 4 divisions, got {len(divisions)}"
    print("  [PASS] All 4 divisions found\n")

    # Test sections
    sections = index.get_section_names()
    print(f"Sections found: {len(sections)}")
    for s in sections:
        print(f"  - {s}")
    print()

    # Test paragraphs
    paragraphs = index.get_paragraph_names()
    print(f"Paragraphs found: {len(paragraphs)}")
    for p in paragraphs:
        print(f"  - {p}")

    expected_paras = ["0000-MAIN", "1000-INITIALIZE", "1100-READ-FIRST",
                      "2000-PROCESS", "2100-VALIDATE", "9000-TERMINATE"]
    for para in expected_paras:
        assert para in paragraphs, f"Missing paragraph: {para}"
    print(f"  [PASS] All {len(expected_paras)} expected paragraphs found\n")

    # Test copybooks
    copybooks = [c.name for c in index.copybooks]
    print(f"Copybooks found: {copybooks}")
    assert "COMAREA" in copybooks, "Missing copybook: COMAREA"
    print("  [PASS] Copybook COMAREA found\n")

    print("=== ALL TESTS PASSED ===")

if __name__ == "__main__":
    test_mainframe_format()
