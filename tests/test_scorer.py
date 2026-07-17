from otto.engine.scanner import Finding
from otto.engine.scorer import compute_score


def make(severity, file_path="a.js", line=1):
    return Finding(rule_id="r", regulation="lgpd", severity=severity, category="general",
                   article="X", message="m", fix="f", fine="$", file_path=file_path,
                   line=line, matched_text="x")


def test_clean_scan_is_100():
    result = compute_score([])
    assert result.score == 100
    assert result.per_file == {}
    assert result.counts == {"critical": 0, "high": 0, "medium": 0, "low": 0}


def test_deductions():
    # 100 - 10 - 4 - 1 = 85
    result = compute_score([make("high"), make("medium"), make("low")])
    assert result.score == 85


def test_critical_caps_at_59():
    # 100 - 25 = 75, but critical caps at 59
    result = compute_score([make("critical")])
    assert result.score == 59


def test_floor_zero():
    result = compute_score([make("critical") for _ in range(10)])
    assert result.score == 0


def test_per_file_scores():
    findings = [make("critical", "bad.js"), make("low", "meh.js")]
    result = compute_score(findings)
    assert result.per_file == {"bad.js": 59, "meh.js": 99}


def test_counts():
    result = compute_score([make("critical"), make("critical"), make("low")])
    assert result.counts == {"critical": 2, "high": 0, "medium": 0, "low": 1}


def test_deterministic():
    findings = [make("high"), make("critical")]
    assert compute_score(findings).score == compute_score(findings).score == 59
