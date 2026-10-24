"""Shared paths and the decision logger used by every script.

Every analytic choice (a parsing rule, an exclusion, a coding rule) is written
to docs/decision_log.md via log_decision(), so nothing is decided silently.
"""

from datetime import date
from pathlib import Path

# Project folders. Raw data is read-only: scripts never write to RAW.
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output"
DOCS = ROOT / "docs"
DECISION_LOG = DOCS / "decision_log.md"


def log_decision(step: str, decision: str, reason: str) -> None:
    """Append one decision to the log file and echo it to the screen."""
    line = f"- **{date.today()} · {step}:** {decision} *Why:* {reason}\n"
    with open(DECISION_LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print("DECISION:", line.strip())
