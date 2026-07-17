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
