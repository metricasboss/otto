from __future__ import annotations

from typing import List

from otto.engine.scanner import Finding
from otto.engine.scorer import ScoreResult

_REG_NAMES = {"lgpd": "LGPD", "gdpr": "GDPR", "both": "LGPD+GDPR"}
_EMOJI = {"critical": "🚨", "high": "⚠️", "medium": "⚡", "low": "ℹ️"}


def render(findings: List[Finding], score: ScoreResult, regulation: str) -> str:
    name = _REG_NAMES.get(regulation, "Privacy")
    if not findings:
        return (
            f"🛡️ OTTO - {name} Analysis\n\n"
            f"✅ No violations detected. Privacy score: {score.score}/100\n\n"
            "🛡️ OTTO protected your users today.\n"
        )

    lines = [f"🛡️ OTTO - {name} Privacy Analysis", "",
             f"❌ VIOLATIONS FOUND: {len(findings)} — Privacy score: {score.score}/100", ""]
    for i, f in enumerate(findings, 1):
        lines += [
            f"{i}. {_EMOJI[f.severity]} {f.rule_id.replace('_', ' ').title()}",
            f"   File: {f.file_path or 'stdin'}:{f.line}",
            f"   Severity: {f.severity.upper()}" + (f" ({f.note})" if f.note else ""),
            f"   Issue: {f.message}",
            f"   Legal basis: {f.article}",
            f"   Fine risk: {f.fine}",
            f"   SUGGESTED FIX: {f.fix}",
            "",
        ]
    lines += ["━" * 42, "", "📊 SUMMARY:"]
    for sev in ("critical", "high", "medium", "low"):
        if score.counts.get(sev):
            lines.append(f"   • {score.counts[sev]} {sev} violation(s) {_EMOJI[sev]}")
    lines += ["", f"📉 Privacy score: {score.score}/100"
              + (" (critical findings cap the score at 59)" if score.counts.get("critical") else ""),
              "", "🛡️ OTTO protected your users today.", ""]
    return "\n".join(lines)
