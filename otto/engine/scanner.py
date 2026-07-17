from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Tuple

from otto.engine.rules import Rule

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass
class Finding:
    rule_id: str
    regulation: str
    severity: str
    category: str
    article: str
    message: str
    fix: str
    fine: str
    file_path: str
    line: int
    matched_text: str
    note: str = ""


def _applies_to_file(file_path: str, rule: Rule) -> bool:
    # Filled in by Task 4 (glob include/exclude). Until then: everything applies.
    return True


def _is_suppressed(line_text: str, lines: List[str], line_num: int, rule_id: str) -> bool:
    # Filled in by Task 4 (otto-ignore). Until then: nothing is suppressed.
    return False


def _adjust_severity(rule: Rule, line_text: str) -> Tuple[str, str]:
    # Filled in by Task 4 (negative_context downgrade).
    return rule.severity, ""


def _passes_validator(rule: Rule, matched_text: str) -> bool:
    # Filled in by Task 4 (check-digit validators).
    return True


def scan_content(content: str, file_path: str, rules: List[Rule]) -> List[Finding]:
    findings: List[Finding] = []
    seen: Set[Tuple[str, str, int]] = set()
    lines = content.split("\n")
    for rule in rules:
        if not _applies_to_file(file_path, rule):
            continue
        try:
            matches = re.finditer(rule.regex, content, re.IGNORECASE | re.MULTILINE)
        except re.error as exc:
            print(f"otto: skipping rule '{rule.id}' (invalid regex: {exc})", file=sys.stderr)
            continue
        for match in matches:
            line_num = content[: match.start()].count("\n") + 1
            key = (rule.id, file_path, line_num)
            if key in seen:
                continue
            line_text = lines[line_num - 1] if line_num <= len(lines) else ""
            if _is_suppressed(line_text, lines, line_num, rule.id):
                continue
            if not _passes_validator(rule, match.group(0)):
                continue
            severity, note = _adjust_severity(rule, line_text)
            seen.add(key)
            findings.append(
                Finding(
                    rule_id=rule.id,
                    regulation=rule.regulation,
                    severity=severity,
                    category=rule.category,
                    article=rule.article,
                    message=rule.message,
                    fix=rule.fix,
                    fine=rule.fine,
                    file_path=file_path,
                    line=line_num,
                    matched_text=match.group(0)[:80],
                    note=note,
                )
            )
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.file_path, f.line))
    return findings


def scan_paths(paths: List[str], rules: List[Rule]) -> List[Finding]:
    findings: List[Finding] = []
    for raw in paths:
        path = Path(raw)
        files = [path] if path.is_file() else sorted(
            p for p in path.rglob("*") if p.is_file()
        )
        for file in files:
            try:
                content = file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            findings += scan_content(content, str(file), rules)
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.file_path, f.line))
    return findings
