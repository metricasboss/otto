from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

SEVERITIES = ("critical", "high", "medium", "low")

DEFAULT_EXCLUDES = [
    "**/*.md",
    "**/*.test.*",
    "**/*.spec.*",
    "**/tests/**",
    "**/test/**",
    "**/fixtures/**",
    "**/node_modules/**",
    "**/.git/**",
]

REQUIRED_FIELDS = ("regex", "severity", "article", "message", "fix")


@dataclass
class Rule:
    id: str
    regex: str
    severity: str
    article: str
    message: str
    fix: str
    fine: str = "Significant penalties"
    category: str = "general"
    regulation: str = "lgpd"
    files: List[str] = field(default_factory=lambda: ["**/*"])
    exclude_files: List[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDES))
    negative_context: List[str] = field(default_factory=list)
    validator: Optional[str] = None
    case_sensitive: bool = False


def _load_file(path: Path, regulation: str) -> List[Rule]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rules: List[Rule] = []
    for rule_id, raw in data.items():
        for req in REQUIRED_FIELDS:
            if req not in raw:
                raise ValueError(f"Rule '{rule_id}' missing required field '{req}'")
        if raw["severity"] not in SEVERITIES:
            raise ValueError(f"Rule '{rule_id}' has invalid severity '{raw['severity']}'")
        rules.append(
            Rule(
                id=rule_id,
                regex=raw["regex"],
                severity=raw["severity"],
                article=raw["article"],
                message=raw["message"],
                fix=raw["fix"],
                fine=raw.get("fine", "Significant penalties"),
                category=raw.get("category", "general"),
                regulation=regulation,
                files=raw.get("files", ["**/*"]),
                exclude_files=raw.get("exclude_files", list(DEFAULT_EXCLUDES)),
                negative_context=[t.lower() for t in raw.get("negative_context", [])],
                validator=raw.get("validator"),
                case_sensitive=bool(raw.get("case_sensitive", False)),
            )
        )
    return rules


def load_rules(regulation: str = "both", base_dir: Optional[Path] = None) -> List[Rule]:
    if regulation not in ("lgpd", "gdpr", "both"):
        raise ValueError(f"Unknown regulation: {regulation!r} (use lgpd, gdpr or both)")
    base = base_dir or Path(__file__).resolve().parent.parent.parent / "skills"
    rules: List[Rule] = []
    if regulation in ("lgpd", "both"):
        rules += _load_file(base / "lgpd" / "patterns.json", "lgpd")
    if regulation in ("gdpr", "both"):
        gdpr_path = base / "gdpr" / "patterns.json"
        if gdpr_path.exists() or regulation == "gdpr":
            rules += _load_file(gdpr_path, "gdpr")
    return rules
