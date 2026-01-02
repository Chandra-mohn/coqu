       IDENTIFICATION DIVISION.
       PROGRAM-ID. CALLER.
       AUTHOR. COQU-TEST.
      *
      * Program that calls other programs
      *
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-AREA.
           05 WS-RESULT        PIC 9(9)V99.
           05 WS-STATUS        PIC X(2).

       PROCEDURE DIVISION.

       MAIN-PARA.
           CALL "SAMPLE" USING WS-AREA
           CALL "UTILITY" USING WS-RESULT
           PERFORM PROCESS-RESULT
           STOP RUN.

       PROCESS-RESULT.
           IF WS-STATUS = "OK"
               DISPLAY "Success"
           ELSE
               DISPLAY "Error: " WS-STATUS
           END-IF.
