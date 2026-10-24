# Surname penalty in vote share

Do candidates with non-white-coded or foreign-sounding surnames get lower vote shares than their opponents in the same race? This project estimates within-race associations, not causal effects.

## Layout
- `data/raw/`: original downloads. These files are read-only and never modified.
- `data/processed/`: intermediate tables that the scripts write.
- `src/`: scripts, numbered in the order they run.
- `tests/`: unit tests (for example, the surname parser).
- `docs/decision_log.md`: every analytic decision.
- `docs/foreign_coding_rule.md`: which origins count as "foreign". This was fixed before any results were seen.
- `output/`: reports, tables and figures.

## Steps
1. `src/01_inspect.py`: profile the raw files.
2. `src/02_build.py`: build one candidate table with a common schema. *(next)*
3. `src/03_score_names.py`: parse surnames, add Census and ethnicolr scores. *(next)*
4. **Checkpoint:** report match rates and the whiteness × foreignness cell counts. Wait for approval before step 5.
5. Main regressions.
6. Robustness checks and write-up.

## Setup
```
uv venv -p 3.11 .venv
uv pip install -p .venv/bin/python -r requirements.txt
.venv/bin/python -m pytest tests
```
