"""Loaders for the raw data files. They read from data/raw and never write there."""

import csv
import io
import zipfile

import pandas as pd

from common import RAW

MIT_ZIP = RAW / "mit_house_dataverse_files.zip"
MIT_MEMBER = "1976-2024-house.tab"


def _unwrap_mit_line(line: str) -> str:
    """Undo the non-standard quoting in our copy of the MIT House file.

    Every data row is wrapped in one extra pair of double quotes, and quotes
    inside a field are backslash-escaped:
        "1976,...,\"WILLIAM L \\"\"BILL\\"\" DICKINSON\",REPUBLICAN,..."
    We strip the outer quotes and turn the escapes back into standard CSV:
        1976,...,"WILLIAM L ""BILL"" DICKINSON",REPUBLICAN,...
    """
    if len(line) >= 2 and line[0] == '"' and line[-1] == '"':
        line = line[1:-1]
    return line.replace('\\\\"\\"', '""').replace('\\"', '"')


def read_mit_house() -> pd.DataFrame:
    """Read the MIT Election Lab U.S. House file (1976-2024) into a DataFrame.

    Raises an error if any row does not have the same number of fields as the
    header, so a parsing problem can never pass silently.
    """
    with zipfile.ZipFile(MIT_ZIP) as z:
        text = z.read(MIT_MEMBER).decode("utf-8")
    lines = [_unwrap_mit_line(l) for l in text.splitlines() if l.strip()]
    rows = list(csv.reader(lines))
    header, body = rows[0], rows[1:]
    bad = [i for i, r in enumerate(body) if len(r) != len(header)]
    if bad:
        raise ValueError(f"{len(bad)} MIT rows have the wrong number of fields, e.g. line {bad[0] + 2}: {lines[bad[0] + 1]}")
    df = pd.DataFrame(body, columns=header)
    # Turn text into proper types. "NA" is the file's missing-value code.
    df = df.replace({"NA": pd.NA, "": pd.NA})
    for col in ["year", "district", "candidatevotes", "totalvotes", "state_fips"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ["runoff", "special", "writein", "unofficial", "fusion_ticket"]:
        df[col] = df[col].map({"TRUE": True, "FALSE": False}).astype("boolean")
    return df


def read_mit_senate() -> pd.DataFrame:
    """Read the MIT Election Lab U.S. Senate file (1976-2024).

    It is a real tab-separated file; quotes inside names are written as \\"
    so we tell pandas that backslash is the escape character.
    """
    with zipfile.ZipFile(RAW / "mit_senate_dataverse_files.zip") as z:
        return pd.read_csv(z.open("1976-2024-senate-state.tab"), sep="\t", escapechar="\\")


def read_hks() -> pd.DataFrame:
    """Read the HKS American Local Government Elections Database (candidate level).

    fips is read as text so leading zeros survive ("06037", not 6037).
    """
    return pd.read_csv(RAW / "hks" / "ledb_candidatelevel.csv", dtype={"fips": str}, low_memory=False)


def read_state_president() -> pd.DataFrame:
    """MIT state-level presidential returns, 1976-2024."""
    return pd.read_csv(RAW / "mit_president" / "1976-2024-president.csv")


def read_county_president() -> pd.DataFrame:
    """MIT county-level presidential returns, 2000-2024. county_fips read as text."""
    with zipfile.ZipFile(RAW / "mit_countypres_dataverse_files.zip") as z:
        return pd.read_csv(z.open("countypres_2000-2024.tab"), sep="\t", dtype={"county_fips": str})
