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
    """Append one decision to the log file and echo it to the screen.

    If the same decision is already in the log (from an earlier run of the
    same script), it is not written again.
    """
    body = f"{step}:** {decision} *Why:* {reason}"
    line = f"- **{date.today()} · {body}\n"
    existing = DECISION_LOG.read_text(encoding="utf-8") if DECISION_LOG.exists() else ""
    if body not in existing:
        with open(DECISION_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    print("DECISION:", line.strip())
