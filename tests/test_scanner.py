from otto.engine.rules import Rule
from otto.engine.scanner import Finding, scan_content, scan_paths

RULE = Rule(
    id="password_plaintext",
    regex="password\\s*[:=]\\s*[\"'][^\"']+[\"']",
    severity="critical",
    article="LGPD Art. 46 (Segurança)",
    message="Senha em plaintext",
    fix="Use hash",
    exclude_files=[],
)


def test_finds_violation_with_line_number():
    content = "const a = 1;\nconst password = \"hunter2secret\";\n"
    findings = scan_content(content, "src/app.js", [RULE])
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "password_plaintext"
    assert f.line == 2
    assert f.file_path == "src/app.js"
    assert "password" in f.matched_text


def test_clean_content_no_findings():
    assert scan_content("const x = 1;\n", "src/app.js", [RULE]) == []


def test_dedup_same_rule_same_line():
    findings = scan_content('password = "abcdef";\n', "a.js", [RULE, RULE])
    assert len(findings) == 1


def test_invalid_regex_skipped():
    bad = Rule(id="bad", regex="[unclosed", severity="low",
               article="X", message="m", fix="f", exclude_files=[])
    assert scan_content('password = "x";\n', "a.js", [bad]) == []


def test_sorted_by_severity_then_line():
    low = Rule(id="low_rule", regex="TODO_PRIVACY", severity="low",
               article="X", message="m", fix="f", exclude_files=[])
    content = "TODO_PRIVACY\nconst password = \"hunter2secret\";\n"
    findings = scan_content(content, "a.js", [low, RULE])
    assert [f.rule_id for f in findings] == ["password_plaintext", "low_rule"]


def test_scan_paths_walks_directory(tmp_path):
    (tmp_path / "app.js").write_text('const password = "hunter2secret";\n')
    sub = tmp_path / "lib"
    sub.mkdir()
    (sub / "b.js").write_text("const ok = true;\n")
    findings = scan_paths([str(tmp_path)], [RULE])
    assert len(findings) == 1
    assert findings[0].file_path.endswith("app.js")


def test_scan_paths_skips_binary(tmp_path):
    (tmp_path / "img.bin").write_bytes(b"\xff\xfe\x00password = 'x'")
    (tmp_path / "app.js").write_text('const password = "hunter2secret";\n')
    findings = scan_paths([str(tmp_path)], [RULE])
    assert len(findings) == 1


MULTILINE_RULE = Rule(
    id="multiline_rule",
    regex=r"(?:^.*\n){0,2}^.*document\.cookie\s*=",
    severity="high",
    article="X",
    message="m",
    fix="f",
    exclude_files=[],
)


def test_multiline_match_anchors_to_last_line():
    content = (
        "// comment line 1\n"
        "function setCookie(userId) {\n"
        "  document.cookie = `user_id=${userId}`;\n"
        "}\n"
    )
    findings = scan_content(content, "src/app.js", [MULTILINE_RULE])
    assert len(findings) == 1
    f = findings[0]
    assert f.line == 3
    assert "document.cookie" in f.matched_text
    assert "comment" not in f.matched_text


def test_multiline_match_otto_ignore_on_final_line_suppresses():
    content = (
        "// comment line 1\n"
        "function setCookie(userId) {\n"
        "  document.cookie = `user_id=${userId}`; // otto-ignore: multiline_rule -- test data\n"
        "}\n"
    )
    findings = scan_content(content, "src/app.js", [MULTILINE_RULE])
    assert findings == []


def test_case_sensitive_rule_skips_lowercase():
    rule = Rule(id="ns", regex="\\b[A-Z]{2}\\d{6,9}[A-Z]?\\b", severity="high",
                article="X", message="m", fix="f", exclude_files=[], case_sensitive=True)
    assert scan_content('const sha = "ab1234567";\n', "src/a.js", [rule]) == []
    assert len(scan_content('const id = "AB1234567";\n', "src/a.js", [rule])) == 1


def test_case_insensitive_default_matches_lowercase():
    rule = Rule(id="ns", regex="\\b[A-Z]{2}\\d{6,9}[A-Z]?\\b", severity="high",
                article="X", message="m", fix="f", exclude_files=[])
    assert len(scan_content('const sha = "ab1234567";\n', "src/a.js", [rule])) == 1
