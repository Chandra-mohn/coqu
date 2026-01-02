       IDENTIFICATION DIVISION.
       PROGRAM-ID. SAMPLE.
       AUTHOR. COQU-TEST.
      *
      * Sample COBOL program for testing coqu parser
      *
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT EMPLOYEE-FILE ASSIGN TO "EMPLOYEE.DAT"
               ORGANIZATION IS INDEXED
               ACCESS MODE IS DYNAMIC
               RECORD KEY IS EMP-ID.

       DATA DIVISION.
       FILE SECTION.
       FD EMPLOYEE-FILE.
       01 EMPLOYEE-RECORD.
           05 EMP-ID            PIC 9(6).
           05 EMP-NAME          PIC X(30).
           05 EMP-DEPT          PIC X(10).
           05 EMP-SALARY        PIC 9(7)V99.

       WORKING-STORAGE SECTION.
       01 WS-VARIABLES.
           05 WS-COUNTER        PIC 9(4) VALUE 0.
           05 WS-TOTAL          PIC 9(9)V99 VALUE 0.
           05 WS-FLAG           PIC 9 VALUE 0.
               88 WS-END-OF-FILE VALUE 1.
           05 WS-DATE.
               10 WS-YEAR       PIC 9(4).
               10 WS-MONTH      PIC 9(2).
               10 WS-DAY        PIC 9(2).

       01 WS-CONSTANTS.
           05 WS-MAX-RECORDS    PIC 9(4) VALUE 9999.
           05 WS-COMPANY-NAME   PIC X(20) VALUE "ACME CORP".

       COPY DATEUTIL.

       LINKAGE SECTION.
       01 LS-PARM.
           05 LS-PARM-LENGTH    PIC S9(4) COMP.
           05 LS-PARM-DATA      PIC X(100).

       PROCEDURE DIVISION USING LS-PARM.

       0000-MAIN SECTION.
       0000-MAIN-PARA.
           PERFORM 1000-INIT
           PERFORM 2000-PROCESS UNTIL WS-END-OF-FILE
           PERFORM 3000-CLEANUP
           STOP RUN.

       1000-INIT SECTION.
       1000-INIT-PARA.
           INITIALIZE WS-VARIABLES
           OPEN INPUT EMPLOYEE-FILE
           PERFORM 1100-READ-FIRST.

       1100-READ-FIRST.
           READ EMPLOYEE-FILE
               AT END SET WS-END-OF-FILE TO TRUE
           END-READ.

       2000-PROCESS SECTION.
       2000-PROCESS-PARA.
           ADD 1 TO WS-COUNTER
           ADD EMP-SALARY TO WS-TOTAL
           PERFORM 2100-VALIDATE
           PERFORM 2200-UPDATE
           READ EMPLOYEE-FILE
               AT END SET WS-END-OF-FILE TO TRUE
           END-READ.

       2100-VALIDATE.
           IF EMP-SALARY > 100000
               CALL "AUDITLOG" USING EMP-ID EMP-NAME EMP-SALARY
           END-IF.

       2200-UPDATE.
           MOVE FUNCTION CURRENT-DATE TO WS-DATE
           DISPLAY "Processing: " EMP-NAME.

       3000-CLEANUP SECTION.
       3000-CLEANUP-PARA.
           CLOSE EMPLOYEE-FILE
           DISPLAY "Total records: " WS-COUNTER
           DISPLAY "Total salary: " WS-TOTAL.
