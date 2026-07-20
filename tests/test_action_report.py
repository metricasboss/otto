import json
import subprocess
import sys

from otto.action.report import MARKER, build_comment

CRITICAL_REPORT = {
    "regulation": "both",
    "score": 59,
    "per_file": {"src/app.js": 59},
    "counts": {"critical": 1, "high": 0, "medium": 0, "low": 0},
    "findings": [
        {
            "rule_id": "cpf_exposure", "regulation": "lgpd", "severity": "critical",
            "category": "sensitive_data", "article": "LGPD Art. 46 (Dados Sensíveis)",
            "message": "CPF brasileiro exposto no código",
            "fix": "Remova o CPF | use env var", "fine": "Até R$ 50 milhões",
            "file_path": "src/app.js", "line": 7, "matched_text": "529.982.247-25",
            "note": "",
        }
    ],
}

CLEAN_REPORT = {"regulation": "both", "score": 100, "per_file": {},
                "counts": {"critical": 0, "high": 0, "medium": 0, "low": 0}, "findings": []}


def test_marker_and_score_headline():
    body = build_comment(CRITICAL_REPORT)
    assert body.startswith(MARKER)
    assert "59/100" in body
    assert "cap the score at 59" in body


def test_findings_table_row():
    body = build_comment(CRITICAL_REPORT)
    assert "`src/app.js:7`" in body
    assert "LGPD Art. 46" in body
    assert "Até R$ 50 milhões" in body
    assert "cpf_exposure" in body


def test_pipes_escaped_in_cells():
    body = build_comment(CRITICAL_REPORT)
    assert "Remova o CPF \\| use env var" in body


def test_clean_variant():
    body = build_comment(CLEAN_REPORT)
    assert "100/100" in body
    assert "No privacy violations" in body
    assert "cap the score" not in body


def test_cli_shim(tmp_path):
    report_file = tmp_path / "r.json"
    report_file.write_text(json.dumps(CLEAN_REPORT), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "otto.action.report", str(report_file)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert MARKER in proc.stdout


def test_cli_shim_usage_error():
    proc = subprocess.run(
        [sys.executable, "-m", "otto.action.report"], capture_output=True, text=True,
    )
    assert proc.returncode == 2


def _make_finding(i):
    return {
        "rule_id": f"rule_{i}", "regulation": "lgpd", "severity": "high",
        "category": "sensitive_data", "article": "LGPD Art. 46",
        "message": "m", "fix": "f", "fine": "x",
        "file_path": f"src/app{i}.js", "line": i, "matched_text": "x", "note": "",
    }


def test_findings_table_capped_at_50_rows():
    report = {
        "regulation": "both", "score": 0, "per_file": {},
        "counts": {"critical": 0, "high": 51, "medium": 0, "low": 0},
        "findings": [_make_finding(i) for i in range(51)],
    }
    body = build_comment(report)
    # 50 data rows + 1 header separator line ("|---|...") -- count table rows
    # via the distinctive "rule_" ids we generated.
    row_count = sum(1 for line in body.splitlines() if line.startswith("| ") and "rule_" in line)
    assert row_count == 50
    assert "...and 1 more finding(s)" in body or "and 1 more finding(s)" in body
    assert "run `python3 -m otto scan` locally for the full report" in body


def test_backtick_in_fix_text_does_not_break_cell():
    report = {
        "regulation": "both", "score": 59, "per_file": {"src/app.js": 59},
        "counts": {"critical": 1, "high": 0, "medium": 0, "low": 0},
        "findings": [{
            "rule_id": "cpf_exposure", "regulation": "lgpd", "severity": "critical",
            "category": "sensitive_data", "article": "LGPD Art. 46",
            "message": "m", "fix": "Use `env.CPF` instead", "fine": "x",
            "file_path": "src/app.js", "line": 1, "matched_text": "x", "note": "",
        }],
    }
    body = build_comment(report)
    assert "`" not in body.split("Use", 1)[1].split("instead", 1)[0]
