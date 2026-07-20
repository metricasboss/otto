from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional, TextIO

from otto.engine.reporters.text import render
from otto.engine.rules import load_rules
from otto.engine.scanner import scan_content
from otto.engine.scorer import compute_score


def _regulation() -> str:
    reg_file = Path.home() / ".claude" / "skills" / "otto" / ".regulation"
    if reg_file.exists():
        value = reg_file.read_text(encoding="utf-8").strip()
        if value in ("lgpd", "gdpr", "both"):
            return value
    return "both"


def main(stdin: Optional[TextIO] = None, stdout: Optional[TextIO] = None) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    try:
        data = json.load(stdin)
    except (json.JSONDecodeError, ValueError):
        print("otto hook: invalid JSON input", file=sys.stderr)
        return 0

    tool_input = data.get("tool_input", {})
    parts = [
        tool_input.get("new_string") or "",
        tool_input.get("content") or "",
    ]
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        parts += [e.get("new_string") or "" for e in edits if isinstance(e, dict)]
    content = "\n".join(p for p in parts if p)
    file_path = tool_input.get("file_path", "")
    if not content:
        return 0

    regulation = _regulation()
    rules = load_rules(regulation)
    findings = scan_content(content, file_path, rules)
    if not findings:
        return 0

    score = compute_score(findings)
    if any(f.severity == "critical" for f in findings):
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": render(findings, score, regulation),
            }
        }
    else:
        payload = {
            "systemMessage": (
                f"OTTO: {len(findings)} non-critical privacy finding(s) in "
                f"{file_path or 'this edit'} (score {score.score}/100). "
                "Run `python3 -m otto scan <path>` for details."
            )
        }
    print(json.dumps(payload, ensure_ascii=False), file=stdout)
    return 0
