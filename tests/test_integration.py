from pathlib import Path

from otto.engine.rules import load_rules
from otto.engine.scanner import scan_paths
from otto.engine.scorer import compute_score


def _score(path):
    findings = scan_paths([path], load_rules("both"))
    return compute_score(findings), findings


def test_unsafe_example_fails_gate():
    score, findings = _score("examples/unsafe_code.js")
    assert score.score <= 59
    assert any(f.severity == "critical" for f in findings)


def test_safe_example_is_perfect():
    score, findings = _score("examples/safe_code.js")
    assert findings == [], [f.rule_id for f in findings]
    assert score.score == 100


def test_cookie_without_consent_anchors_to_violating_line():
    unsafe_path = Path("examples/unsafe_code.js")
    source_lines = unsafe_path.read_text(encoding="utf-8").split("\n")
    expected_line = next(
        i + 1 for i, text in enumerate(source_lines) if "document.cookie" in text
    )

    _, findings = _score(str(unsafe_path))
    cookie_findings = [f for f in findings if f.rule_id == "cookie_without_consent"]
    assert len(cookie_findings) == 1
    finding = cookie_findings[0]
    assert finding.line == expected_line
    assert "document.cookie" in source_lines[finding.line - 1]
    assert "document.cookie" in finding.matched_text
