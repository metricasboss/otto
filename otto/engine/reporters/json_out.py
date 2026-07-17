from __future__ import annotations

import json
from dataclasses import asdict
from typing import List

from otto.engine.scanner import Finding
from otto.engine.scorer import ScoreResult


def render(findings: List[Finding], score: ScoreResult, regulation: str) -> str:
    return json.dumps(
        {
            "regulation": regulation,
            "score": score.score,
            "per_file": score.per_file,
            "counts": score.counts,
            "findings": [asdict(f) for f in findings],
        },
        indent=2,
        ensure_ascii=False,
    )
