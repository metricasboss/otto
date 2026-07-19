from __future__ import annotations

import json
import sys
from typing import List, Optional

MARKER = "<!-- otto-privacy-report -->"
_SEV_EMOJI = {"critical": "🚨", "high": "⚠️", "medium": "⚡", "low": "ℹ️"}
MAX_TABLE_ROWS = 50


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").replace("`", "′")


def build_comment(report: dict) -> str:
    score = report["score"]
    findings = report.get("findings", [])
    counts = report.get("counts", {})
    cap_note = " (critical findings cap the score at 59)" if counts.get("critical") else ""

    lines = [MARKER, "## 🛡️ OTTO Privacy Report", "",
             f"**Privacy score: {score}/100**{cap_note}", ""]
    if not findings:
        lines.append("✅ No privacy violations in the files changed by this PR.")
    else:
        lines += [f"❌ **{len(findings)} finding(s)** in changed files:", "",
                  "| Severity | Location | Rule | Legal basis | Fine risk | Suggested fix |",
                  "|---|---|---|---|---|---|"]
        shown = findings[:MAX_TABLE_ROWS]
        remaining = len(findings) - len(shown)
        for f in shown:
            lines.append(
                f"| {_SEV_EMOJI.get(f['severity'], '')} {_cell(f['severity'])} "
                f"| `{_cell(f['file_path'])}:{f['line']}` "
                f"| {_cell(f['rule_id'])} "
                f"| {_cell(f['article'])} "
                f"| {_cell(f['fine'])} "
                f"| {_cell(f['fix'])} |"
            )
        if remaining > 0:
            lines.append(
                f"_...and {remaining} more finding(s) — run `python3 -m otto scan` "
                "locally for the full report._"
            )
    lines += ["", "---",
              "_Deterministic score by [OTTO](https://github.com/metricasboss/otto)"
              " — same diff, same score. Not legal advice._"]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else argv
    if len(argv) != 1:
        print("usage: python3 -m otto.action.report <report.json>", file=sys.stderr)
        return 2
    with open(argv[0], encoding="utf-8") as fh:
        report = json.load(fh)
    print(build_comment(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
