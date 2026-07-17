from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from otto.engine.scanner import Finding

DEDUCTIONS = {"critical": 25, "high": 10, "medium": 4, "low": 1}
CRITICAL_CAP = 59


def _score(findings: List[Finding]) -> int:
    score = max(0, 100 - sum(DEDUCTIONS[f.severity] for f in findings))
    if any(f.severity == "critical" for f in findings):
        score = min(score, CRITICAL_CAP)
    return score


@dataclass
class ScoreResult:
    score: int
    per_file: Dict[str, int]
    counts: Dict[str, int]


def compute_score(findings: List[Finding]) -> ScoreResult:
    files = sorted({f.file_path for f in findings})
    per_file = {
        fp: _score([f for f in findings if f.file_path == fp]) for fp in files
    }
    counts = {sev: sum(1 for f in findings if f.severity == sev) for sev in DEDUCTIONS}
    return ScoreResult(score=_score(findings), per_file=per_file, counts=counts)
