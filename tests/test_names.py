"""Unit tests for the surname parser. Run with:  .venv/bin/python -m pytest tests"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from names import match_to_census, parse_name  # noqa: E402


@pytest.mark.parametrize("raw, first, last", [
    ("SMITH, JOHN A.", "JOHN", "SMITH"),
    ("Smith, John A., Jr.", "JOHN", "SMITH"),
    ("John Smith III", "JOHN", "SMITH"),
    ("John Smith, Jr.", "JOHN", "SMITH"),
    ("Maria de la Cruz", "MARIA", "DE LA CRUZ"),
    ("Martin Van Buren", "MARTIN", "VAN BUREN"),
    ("Ann Smith-Jones", "ANN", "SMITH-JONES"),
    ("DIAZ-BALART, LINCOLN", "LINCOLN", "DIAZ-BALART"),
    ('Robert "Bob" O\'Brien', "ROBERT", "O'BRIEN"),
    ("Dr. Jane Q. Public", "JANE", "PUBLIC"),
    ("Madonna", "", "MADONNA"),
    ("rosa garcía", "ROSA", "GARCIA"),
    ("james 'jimmy' van bramer", "JAMES", "VAN BRAMER"),
    ("pat o'brien", "PAT", "O'BRIEN"),
    ("joey acuna, jr.", "JOEY", "ACUNA"),
    ("richard de la paz,", "RICHARD", "DE LA PAZ"),
    ("", "", ""),
])
def test_parse_name(raw, first, last):
    assert parse_name(raw) == (first, last)


def test_match_rules():
    census = pd.DataFrame({"name": ["DELACRUZ", "OBRIEN", "DIAZ", "JONES", "SMITH"],
                           "pctwhite": [5.0, 95.0, 20.0, 60.0, 70.9]})
    s = pd.Series(["DE LA CRUZ", "O'BRIEN", "DIAZ-BALART", "XYZ-JONES", "ZZZZQ"])
    out = match_to_census(s, census)
    assert out["census_match_rule"].tolist() == ["full", "full", "first_part", "last_part", "unmatched"]
    assert out["census_key"].tolist()[:4] == ["DELACRUZ", "OBRIEN", "DIAZ", "JONES"]
    assert pd.isna(out["pctwhite"].iloc[4])
