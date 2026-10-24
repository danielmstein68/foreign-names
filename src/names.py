"""Surname parsing and matching to the Census 2010 surname file.

Candidate names arrive in many formats ("SMITH, JOHN A. JR.", "John Smith III",
"Maria de la Cruz", "Smith-Jones, Ann"). This module turns each one into a
first name and a surname, then finds the surname in the Census table.

Census surnames are upper-case letters only: spaces and apostrophes are removed
(DE LA CRUZ -> DELACRUZ, O'BRIEN -> OBRIEN) and there are no hyphenated entries.
So we normalise the same way before matching.
"""

import re
import unicodedata

import pandas as pd

# Tokens that are not part of anyone's surname.
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V", "ESQ", "MD", "PHD", "DDS", "CPA"}
TITLES = {"DR", "MR", "MRS", "MS", "HON", "REV", "SEN", "REP", "JUDGE", "SHERIFF"}

# Lower-case particles that belong to the surname that follows them
# ("Van Buren", "de la Cruz", "St. John").
PARTICLES = {"DE", "DA", "DEL", "DELA", "DELLA", "DI", "DO", "DOS", "DU",
             "LA", "LE", "VAN", "VON", "DER", "DEN", "TEN", "ST", "SAINT", "MAC", "BIN", "AL", "EL"}


def strip_accents(text: str) -> str:
    """GARCÍA -> GARCIA, MUÑOZ -> MUNOZ (the Census file has no accents)."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _tokens(text: str) -> list[str]:
    """Upper-case, drop periods, split on spaces; keep hyphens and apostrophes inside words."""
    text = text.upper().replace(".", " ")
    return [t for t in re.split(r"\s+", text) if t]


def _drop_extras(tokens: list[str]) -> list[str]:
    """Remove suffixes (Jr, III...) and titles (Dr, Hon...)."""
    return [t for t in tokens if t.strip(",") not in SUFFIXES | TITLES]


def parse_name(raw: str) -> tuple[str, str]:
    """Return (first_name, surname) from one raw candidate-name string.

    Rules, in order:
    0. Remove accents: García -> Garcia.
    1. Remove nicknames in quotes or parentheses: John "Jack" Smith -> John Smith,
       James 'Jimmy' Van Bramer -> James Van Bramer (apostrophes inside a
       word, as in O'Brien, are kept).
    2. If there is a comma, the part before the first comma is the surname
       ("LAST, FIRST"), unless that part is the whole name and the comma only
       separates a suffix ("John Smith, Jr.").
    3. Otherwise the surname is the last word plus any particles before it
       ("Maria de la Cruz" -> "DE LA CRUZ").
    Suffixes (Jr, Sr, II, III...) and titles (Dr, Hon...) are dropped.
    """
    if not isinstance(raw, str) or not raw.strip():
        return "", ""
    text = re.sub(r'"[^"]*"|\([^)]*\)|“[^”]*”', " ", raw)
    text = re.sub(r"(?<!\w)'[^']+'(?!\w)", " ", text)
    text = strip_accents(text)

    if "," in text:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        # Drop comma-separated parts that are only suffixes: "John Smith, Jr."
        parts = [p for p in parts if _drop_extras(_tokens(p))]
        if len(parts) >= 2:
            last = _drop_extras(_tokens(parts[0]))
            first = _drop_extras(_tokens(parts[1]))
            return (first[0] if first else ""), " ".join(last)
        text = parts[0] if parts else ""

    tokens = _drop_extras(_tokens(text))
    if not tokens:
        return "", ""
    if len(tokens) == 1:
        return "", tokens[0]

    # Walk left from the last word, absorbing particles into the surname.
    i = len(tokens) - 1
    while i - 1 >= 1 and tokens[i - 1] in PARTICLES:
        i -= 1
    return tokens[0], " ".join(tokens[i:])


def census_key(surname: str) -> str:
    """Normalise a surname the way the Census file does: letters A-Z only."""
    return re.sub(r"[^A-Z]", "", strip_accents(surname).upper())


def match_candidates(surname: str) -> list[tuple[str, str]]:
    """Ordered list of (rule, census_key) to try for one surname.

    1. 'full': the whole surname, letters only (DE LA CRUZ -> DELACRUZ).
    2. 'first_part': for hyphenated or multi-word names, the first part
       (DIAZ-BALART -> DIAZ). This is usually the paternal / original surname.
    3. 'last_part': then the last part (SMITH-JONES -> JONES).
    """
    tries = [("full", census_key(surname))]
    pieces = [census_key(p) for p in re.split(r"[-\s]+", surname) if census_key(p)]
    # Skip particles when taking parts, so "DE LA CRUZ" never matches "DE".
    pieces = [p for p in pieces if p not in PARTICLES]
    if len(pieces) >= 2:
        tries += [("first_part", pieces[0]), ("last_part", pieces[-1])]
    return [(rule, key) for rule, key in tries if key]


def match_to_census(surnames: pd.Series, census: pd.DataFrame) -> pd.DataFrame:
    """Match each surname to the Census table.

    Returns one row per input with the matched key, which rule matched
    ('full', 'first_part', 'last_part' or 'unmatched'), and the Census
    percentage columns (NaN when unmatched).
    """
    table = census.set_index("name")
    known = set(table.index)
    keys, rules = [], []
    for s in surnames.fillna(""):
        hit = next(((r, k) for r, k in match_candidates(s) if k in known), ("unmatched", None))
        rules.append(hit[0])
        keys.append(hit[1])
    out = table.reindex(keys).reset_index(drop=True)
    out.insert(0, "census_key", keys)
    out.insert(1, "census_match_rule", rules)
    out.index = surnames.index
    return out
