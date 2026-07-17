from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import List, Set, Tuple

from otto.engine.rules import Rule
from otto.engine.validators import VALIDATORS

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SUPPRESS_RE = re.compile(r"otto-ignore:\s*([\w,\- ]+?)\s*--\s*(\S.+)")


def _glob_match(path: str, pattern: str) -> bool:
    if fnmatch(path, pattern):
        return True
    # "**/" must also match zero directories: "**/*.md" matches "README.md"
    if pattern.startswith("**/") and fnmatch(path, pattern[3:]):
        return True
    return False


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
    if not file_path:
        return True  # hook mode / stdin: no path to filter on
    path = file_path.replace("\\", "/")
    if not any(_glob_match(path, g) for g in rule.files):
        return False
    if any(_glob_match(path, g) for g in rule.exclude_files):
        return False
    return True


def _is_suppressed(line_text: str, lines: List[str], line_num: int, rule_id: str) -> bool:
    candidates = [line_text]
    if line_num >= 2:
        candidates.append(lines[line_num - 2])
    for text in candidates:
        match = SUPPRESS_RE.search(text)
        if match:
            suppressed_ids = [r.strip() for r in match.group(1).split(",")]
            if rule_id in suppressed_ids:
                return True
    return False


def _adjust_severity(rule: Rule, line_text: str) -> Tuple[str, str]:
    lowered = line_text.lower()
    for term in rule.negative_context:
        if term in lowered:
            return "low", "possible test data (negative context matched)"
    return rule.severity, ""


def _passes_validator(rule: Rule, matched_text: str) -> bool:
    if rule.validator is None:
        return True
    validator = VALIDATORS.get(rule.validator)
    if validator is None:
        return True  # unknown validator name: fail open, rule still applies
    return validator(matched_text)


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
