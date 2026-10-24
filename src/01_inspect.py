"""Step 1: inspect every raw data file before building anything.

For each file in data/raw this prints columns, dtypes, row counts and, where
the columns exist, the spread of years, offices, parties, incumbency codes,
seat counts, write-in flags and example names. It writes nothing except a
text report to output/01_inspect_report.txt.

Run:  .venv/bin/python src/01_inspect.py
"""

import io
import sys
import zipfile
from contextlib import redirect_stdout

import pandas as pd

from common import OUTPUT, RAW
from readers import MIT_MEMBER, read_mit_house

READABLE = {".csv", ".tab", ".tsv", ".txt", ".dta", ".parquet", ".xlsx", ".xls", ".rds"}

# Substrings that hint a column holds something we care about. Column names
# for the HKS and MIT files are NOT verified yet, so we search loosely.
HINTS = {
    "year": ["year", "date"],
    "office": ["office", "position", "seat", "contest", "race"],
    "party": ["party"],
    "incumbent": ["incumb"],
    "seats": ["seat", "vote_for", "magnitude", "num_win", "nwin"],
    "writein": ["writein", "write_in", "write-in"],
    "special": ["special"],
    "stage": ["stage", "runoff", "primary", "general", "type"],
    "name": ["name", "candidate"],
    "nonpartisan": ["nonpartisan", "partisan"],
}


def read_any(path, name=None):
    """Read one file into a DataFrame based on its extension."""
    if name == MIT_MEMBER:
        # Our copy of the MIT House file has non-standard quoting; see readers.py.
        return read_mit_house()
    suffix = (name or path.name).lower().rsplit(".", 1)[-1]
    if suffix in ("csv", "txt", "tab", "tsv"):
        # Don't trust the extension: Dataverse's ".tab" downloads can be
        # comma-separated. Pick whichever delimiter the header line uses more.
        if isinstance(path, io.BytesIO):
            header = path.getvalue().split(b"\n", 1)[0].decode("utf-8", "replace")
        else:
            with open(path, encoding="utf-8", errors="replace") as f:
                header = f.readline()
        sep = "\t" if header.count("\t") > header.count(",") else ","
        return pd.read_csv(path, sep=sep, low_memory=False, encoding_errors="replace")
    if suffix == "dta":
        return pd.read_stata(path, convert_categoricals=False)
    if suffix == "parquet":
        return pd.read_parquet(path)
    if suffix in ("xlsx", "xls"):
        return pd.read_excel(path)
    raise ValueError(f"don't know how to read .{suffix}")


def describe(df: pd.DataFrame, label: str) -> None:
    """Print a compact profile of one table."""
    print("=" * 80)
    print(f"{label}: {len(df):,} rows x {df.shape[1]} columns")
    print("-" * 80)
    print(df.dtypes.to_string())
    print("\nFirst 3 rows:")
    print(df.head(3).T.to_string())

    lower = {c: c.lower() for c in df.columns}
    for topic, keys in HINTS.items():
        cols = [c for c, l in lower.items() if any(k in l for k in keys)]
        for c in cols:
            vc = df[c].value_counts(dropna=False)
            print(f"\n[{topic}] column '{c}': {df[c].nunique(dropna=False):,} distinct values")
            print(vc.head(15).to_string())


def main() -> None:
    files = sorted(p for p in RAW.rglob("*") if p.is_file())
    if not files:
        sys.exit(f"No files in {RAW}. Put the raw data there first.")
    for path in files:
        if path.suffix.lower() == ".zip":
            # Read zip members in memory; never extract into data/raw.
            with zipfile.ZipFile(path) as z:
                for member in z.namelist():
                    if "." + member.lower().rsplit(".", 1)[-1] in READABLE:
                        with z.open(member) as f:
                            try:
                                describe(read_any(io.BytesIO(f.read()), member), f"{path.name}::{member}")
                            except Exception as e:
                                print(f"{path.name}::{member}: could not read ({e})")
        elif path.suffix.lower() in READABLE:
            try:
                describe(read_any(path), path.name)
            except Exception as e:
                print(f"{path.name}: could not read ({e})")
        else:
            print(f"{path.name}: skipped (not a data file)")


if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)
    report = OUTPUT / "01_inspect_report.txt"
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    report.write_text(buf.getvalue(), encoding="utf-8")
    print(buf.getvalue())
    print(f"\nSaved to {report}")
