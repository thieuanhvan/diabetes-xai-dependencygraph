@echo off
REM ============================================================================
REM  refresh_outputs.bat   (place in the P7 repo root, run from there)
REM
REM  Syncs the committed audit snapshot  outputs\  with the run that backs the
REM  FAIR manuscript, rebuilds the derived files, and verifies the numbers.
REM
REM  WHY IT EXISTS
REM    The runners write to  %%PIPELINE_REPO%%\outputs_kg .  The committed
REM    outputs\ folder is a snapshot for reviewers who do NOT have the P4
REM    pipeline.  When the two drift, analysis reads the stale snapshot and
REM    prints numbers that disagree with the paper.  This script re-syncs them
REM    and refuses to run on a mismatch.
REM
REM  SAFE BY DEFAULT
REM    It COPIES the existing authoritative dumps; it does NOT regenerate them.
REM    DiCE is stochastic across library versions, so a fresh run would no
REM    longer match the frozen manuscript.  Regeneration commands are recorded
REM    at the bottom (PROVENANCE) for the day the dumps have to be rebuilt.
REM ============================================================================
setlocal EnableDelayedExpansion

set "P7=C:\Projects\uit\diabetes-xai-dependencygraph"
set "PIPELINE_REPO=C:\Projects\uit\diabetes-xai-counterfactual"
set "SRC=%PIPELINE_REPO%\outputs_kg"
set "PY=%P7%\.venv\Scripts\python.exe"
set "DST=%P7%\outputs"

cd /d "%P7%" || (echo [FAIL] cannot cd to %P7% & exit /b 1)

REM ---- gate 0: authoritative dump present, and equal to the manuscript run ----
if not exist "%SRC%\raw_cf_changes.csv" (
  echo [STOP] "%SRC%\raw_cf_changes.csv" not found.
  echo        The run backing the manuscript is not on disk.
  echo        Generate it once with the PROVENANCE commands below, then re-run.
  goto :provenance
)
"%PY%" -c "n=sum(1 for _ in open(r'%SRC%\raw_cf_changes.csv'))-1;print('   outputs_kg change-rows:',n);raise SystemExit(0 if n==1520 else 2)"
if errorlevel 1 (
  echo [STOP] outputs_kg holds a DIFFERENT run than the manuscript ^(expected 1520 change-rows^).
  echo        Do NOT copy - that would desync the paper.  Restore the manuscript run,
  echo        or regenerate AND re-sync every number in the manuscript.  Ask first.
  exit /b 1
)

REM ---- 1: copy authoritative dumps + summaries into the snapshot --------------
copy /Y "%SRC%\raw_cf_changes.csv"         "%DST%\" >nul
copy /Y "%SRC%\raw_cf_index.csv"           "%DST%\" >nul
copy /Y "%SRC%\seed_sweep.csv"             "%DST%\" >nul
copy /Y "%SRC%\enforcement_comparison.csv" "%DST%\" >nul
if exist "%SRC%\route_enforcement.csv"     copy /Y "%SRC%\route_enforcement.csv"     "%DST%\" >nul
if exist "%SRC%\model_reproducibility.csv" copy /Y "%SRC%\model_reproducibility.csv" "%DST%\" >nul

REM ---- 2: rebuild derived files, reading/writing ONLY the snapshot ------------
REM  KG_OUTPUTS wins over every other path, so all reads/writes hit outputs\ .
set "KG_OUTPUTS=%DST%"
"%PY%" analysis\audit_rules.py outputs   || (echo [FAIL] audit_rules & exit /b 1)
"%PY%" analysis\tier_sensitivity.py      || (echo [FAIL] tier_sensitivity & exit /b 1)
"%PY%" analysis\export_edges.py outputs  || (echo [FAIL] export_edges & exit /b 1)

REM ---- 3: verification gate --------------------------------------------------
echo.
echo ================ VERIFY : must match the manuscript ================
"%PY%" analysis\paper_numbers.py
echo ====================================================================
echo Expected: total=1520  indicator=339 22.3pct  no-lever=172  edge=210  fully-unactionable=111 11.1pct
echo If the block above matches, outputs\ is safe to commit.
echo.
echo NOTE: graph_cf_changes.csv / graph_cf_index.csv are vestigial ^(paper_numbers
echo       does not read them^).  Leave or delete; they do not affect any number.
endlocal
exit /b 0

:provenance
echo.
echo -- PROVENANCE: how outputs_kg is generated ^(run from %P7%, in order^) --------
echo      set PIPELINE_REPO=%PIPELINE_REPO%
echo      "%%PY%%" run_audit_dump.py       REM seed-42 CF dump, global pass replayed  (Sec V)
echo      "%%PY%%" run_enforce.py          REM enforcement comparison                 (Sec VI)
echo      "%%PY%%" run_seed_sweep.py       REM 5-seed sweep                           (Sec VI)
echo      "%%PY%%" run_route_enforce.py    REM route-aware variants A/B/C   (journal)
echo      "%%PY%%" run_check_model_repro.py REM artefact/retrain agreement
echo.
echo   run_audit_dump.py replays the discarded global-mode pass, so it yields the
echo   published 1520-change vector.  A per-query-only run yields 1500 and L1=88
echo   against the published per-feature vector; see run_rng_offset_test.py.
echo   Then re-run refresh_outputs.bat.  If the numbers moved, the manuscript
echo   must be re-synced to the new run before committing.
exit /b 1