# W0-14 Component Mini-Spec

Title: Authority-matrix lint + consumer tests

Matrix-driven consumer tests: for every spec 1.2 row, consumers branch only on validated authority state and fail closed with the named result on stale/missing/invalid mirror; undeclared-authority lint for security-fact reads with no declared row.

Acceptance criteria:
- DF-9 complete row coverage
- lint catches a fixture module reading a mirror directly

Spec source: spec-final.md v9.1 (sha 5d981350); execution-plan.md task W0-14.
Implementation status: greenfield — no authority-matrix suite exists
