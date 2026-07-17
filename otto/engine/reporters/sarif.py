from __future__ import annotations

import json
from typing import List

from otto.engine.scanner import Finding
from otto.engine.scorer import ScoreResult

_LEVELS = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}


def render(findings: List[Finding], score: ScoreResult, regulation: str) -> str:
    rules_meta = {}
    results = []
    for f in findings:
        rules_meta.setdefault(
            f.rule_id,
            {
                "id": f.rule_id,
                "shortDescription": {"text": f.message},
                "fullDescription": {"text": f"{f.message} — {f.article}. Fine risk: {f.fine}"},
                "help": {"text": f.fix},
            },
        )
        results.append(
            {
                "ruleId": f.rule_id,
                "level": _LEVELS[f.severity],
                "message": {"text": f"{f.message} ({f.article}). Suggested fix: {f.fix}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": f.file_path or "stdin"},
                            "region": {"startLine": f.line},
                        }
                    }
                ],
            }
        )
    doc = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "OTTO",
                        "informationUri": "https://github.com/metricasboss/otto",
                        "rules": sorted(rules_meta.values(), key=lambda r: r["id"]),
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)
