# Statistics workspace

Latest: [descriptive-only Phase 5](phase_reports/PHASE_5_REPORT.md), authorized in
[PHASE_5_APPROVAL.md](phase_reports/PHASE_5_APPROVAL.md). Fourteen cases and four
windows are implemented; 118 tests pass. Inference remains disabled, Strict is
default, Standard 95% is experimental. Stop for user review before Phase 6.
This supersedes historical Phase 5 holds below; it does not release inference.

Latest: [Sen-centered Berger--Boos checkpoint](phase_reports/PHASE_4_BERGER_BOOS_REPORT.md).
The focused confidence-set candidate failed practical calibration/power targets.
110 software tests pass; source data, policies and previous results are preserved.
Recommend descriptive-only use of existing Sen results and stop method searching
at this checkpoint. Inference remains disabled; no Phase 5 work has started.

Previous: [estimand-aligned Sen uncertainty](phase_reports/PHASE_4_SEN_REPORT.md).
Sen-centered nuisance-aware Monte Carlo is recommended for further research;
the tested grid envelope is too conservative and other candidates fail calibration.
103 tests pass. No method is released and Phase 5 has not started.

Latest checkpoint: [double-bootstrap diagnosis](phase_reports/PHASE_4_DOUBLE_DIAGNOSIS_REPORT.md).
Repeated cache/grid/misspecification experiments confirm remaining failures;
regression inference and Sen descriptions have distinct estimands. 99 tests pass,
but inference remains disabled. NASA data and all prior artifacts are preserved.

Newest research: [short-record dependence uncertainty](phase_reports/PHASE_4_UNCERTAINTY_REPORT.md).
REML and refitted/double parametric bootstrap substantially improve calibration,
but no candidate passes all required scenarios. 94 tests pass; inference remains
disabled. NASA data, default policies and validated descriptive slopes are preserved.

Latest: [Phase 4 follow-up](phase_reports/PHASE_4_FOLLOWUP_REPORT.md) compares
adjusted Mann-Kendall and AR(1) regression on fresh holdout simulations. Both
fail calibration; 90 software tests pass. Inference remains disabled, all
previous artifacts are preserved, and Phase 5 has not started.

New to weather data? Start with [Stage 2 explained](STAGE_2_EXPLAINED.md),
the plain-language guide to variables, units, preparation, output fields,
coverage percentages, figures and actual examples.

Public work: [PR #1 on AdhamAl-Rifaie's fork](https://github.com/AdhamAl-Rifaie/nasa_planet/pull/1),
branch `codex/ml-statistics`, originally based on upstream main at
`ecf39088744c7ea01ae7d30d92e5ce6b91d24f6d`.

**Latest checkpoint: [Phase 4 inference research](phase_reports/PHASE_4_REPORT.md).
The tested bootstrap candidate FAILED calibration and is rejected for release.**
85 software tests pass, but that does not establish scientific error control.
Descriptive Phase 3 outputs remain available; no inference or significance maps
are released. Phase 5 has not started.

Read the revised `ML_STATISTICS_AGENT.md`, [PLAN.md](PLAN.md), this directory's
`PROGRESS.md`, and its latest phase report at the start of a statistics session.
The repository-root `AGENT_BRIEF.md` and `PROGRESS.md` belong to Role 04 (RAG).
The statistics brief and plan were revised under the user's 15 November request
to use the actual data. The original brief/report remain in Git history.

Phases 1-3 passed their implementation checks. Stage 2 prepares all twelve
variable-region pairs, with approval to advance recorded separately from its
unchanged policy bytes. Phase 3 implements validated descriptive regional/cell
slopes; its approval to begin Phase 4 is also recorded. Standard 95% remains
experimental and retains missing/incomplete records. Backend schema sign-off
and legacy inference review are separate later gates.

Install the input/exploration dependencies in a repository-local environment:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r packages/science/requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s packages/science/tests -v
.\.venv\Scripts\python.exe tools/audit_science_inputs.py --output data/derived/input-audit.json
.\.venv\Scripts\python.exe tools/run_science_exploration.py
.\.venv\Scripts\python.exe tools/probe_existing_statistics.py --output data/derived/existing-method-probes.json
```

The current suite has **85 tests**, including the earlier 72 preparation/trend
checks and 13 inference-mechanics/reference checks. The current input audit passes all twelve field/unit
contracts. The inherited-method probe intentionally still exits **1**
for the two uncorrected regression cases in its pinned historical commit. It
does not test a repaired engine. Neither audit/probe edits source measurements.

Explore [notebooks/01_exploration.ipynb](notebooks/01_exploration.ipynb). It writes
a map/cell-series image to `data/derived/science/phase_1/` and a provenance
summary to `phase_reports/PHASE_1_INPUT_METADATA.json`. This is descriptive input
exploration, with GPM ancillary fields retained and no additional quality-index
cutoff; regional aggregation, product QA policy and inference are later gates.

See [the plan-alignment report](phase_reports/PHASE_0_REPLAN_REPORT.md) and
[Phase 1 report](phase_reports/PHASE_1_REPORT.md) for evidence and remaining work.
The [original Phase 0 report](phase_reports/PHASE_0_REPORT.md) remains historical.

## Stage 2 reproduction

These preparation commands are for a fresh workspace. In an existing reviewed
workspace, read the saved artifacts and use the later review/validation commands
below, preserving the original files and their checkpoint hashes.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s packages/science/tests -v
.\.venv\Scripts\python.exe tools/prepare_science_inputs.py
.\.venv\Scripts\python.exe tools/prepare_science_inputs.py --variable-id vegetation_greenness --modis-mode standard --output-dir data/derived/science/phase_2_standard --coverage-report packages/science/phase_reports/PHASE_2_QA_SENSITIVITY.json
.\.venv\Scripts\python.exe tools/validate_prepared_inputs.py
.\.venv\Scripts\python.exe tools/run_science_preprocessing.py
```

[The policy](config/preparation_policy.json) defaults to strict MODIS QA and
fixed complete-reference support. Centre-selected full native cells receive
spherical area weights; this is not exact polygon intersection. The source
cubes and readiness flags remain unchanged. Annual summaries require all twelve
months. Cell masks, coverage, source rates/QA, monthly/annual series and
fixed-reference anomalies are preserved in ignored `data/derived/science/phase_2/`.
Downstream estimators must select `cell_monthly` or `regional_monthly`
explicitly. `qa_monthly` is a diagnostic before fixed-support exclusion;
ancillary QA/error fields are not interchangeable with the analysis series.

Open [02_preprocessing.ipynb](notebooks/02_preprocessing.ipynb),
[the coverage report](phase_reports/PHASE_2_COVERAGE.json),
[QA sensitivity results](phase_reports/PHASE_2_QA_SENSITIVITY.json), and
[the Stage 2 report](phase_reports/PHASE_2_REPORT.md).
Strict complete-period support retains only 14.69% of selected native-cell area
for Sahel NDVI; the standard comparison retains 82.59% but admits marginal data.
Stage 2 approval is recorded in [PHASE_2_APPROVAL.md](phase_reports/PHASE_2_APPROVAL.md).
Preparation itself produces no slopes or inferential claims.

Output metadata revision `1.1` corrects inherited unit labels on masks,
fractions and normalized weights. These are dimensionless `1`; only the native
cell solid angle uses `sr`. Annual/anomaly descriptions are explicit. All
numeric/coordinate arrays in the twelve default and three comparison files
were verified unchanged by this label correction. The preparation policy and
strict preparation default remain unchanged.

## Phase 3 descriptive slopes

[Checkpoint](phase_reports/PHASE_3_REPORT.md) and
[executed notebook](notebooks/03_trend_validation.ipynb): exact Theil-Sen regional
and cell slopes, explicit monthly/annual elapsed-year axes, known-trend and
missing/short-series checks, 210 independent slope-only reference comparisons.
Strict 100%, Standard 100% and experimental Standard 95% remain separate.
The commands below rebuild the Phase 3 checkpoint in a fresh workspace. For
the existing reviewed outputs, open the saved notebook/reports; rebuilding
creates new provenance records that must become a new review baseline.

```powershell
.\.venv\Scripts\python.exe tools/run_science_trends.py
.\.venv\Scripts\python.exe tools/run_science_trend_notebook.py
```

The historical Phase 3 test manifest records its 72-test checkpoint. Current
tests are run with the full discovery command above; the Phase 4 validator also
checks preservation of the historical artifacts without overwriting them.

## Phase 4 research and non-release decision

[Checkpoint](phase_reports/PHASE_4_REPORT.md),
[study evidence](phase_reports/PHASE_4_STUDY.json),
[validation](phase_reports/PHASE_4_VALIDATION.json),
[executed notebook](notebooks/04_inference_validation.ipynb).

```powershell
.\.venv\Scripts\python.exe tools/run_science_inference_study.py
.\.venv\Scripts\python.exe tools/validate_inference_study.py
.\.venv\Scripts\python.exe tools/run_science_inference_notebook.py
```

The study takes about six minutes locally. It evaluates correlated nulls,
known positive/negative slopes, seasonal annualization, block sensitivity,
interval coverage, and BH/BY against SciPy on valid synthetic p-values.
The 24,000 scenario-record evaluations reuse records across block comparisons;
they are not 24,000 independent datasets or additional NASA observations.

The four-year candidate's false-positive rates of 18.6-34.0% and interval
coverage of 65.8-82.4% at 24 years fail its gates. BH/BY reference agreement
does not repair invalid individual p-values. NASA candidate calculations are
quarantined research diagnostics, never application evidence. Real multiplicity,
real-cell inference and significance classifications remain withheld.

Sources, default preparation and Phase 3 descriptive results remain unchanged.
Continue Phase 4 method research before authorizing Phase 5.
