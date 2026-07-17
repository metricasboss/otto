from otto.engine.rules import DEFAULT_EXCLUDES, Rule
from otto.engine.scanner import scan_content

CPF_RULE = Rule(
    id="cpf_exposure",
    regex="\\b\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}\\b",
    severity="critical",
    article="LGPD Art. 46",
    message="CPF exposto",
    fix="Remova",
    negative_context=["mock", "faker", "example"],
    validator="cpf",
)

VALID_CPF = 'const cpf = "529.982.247-25";\n'


def test_flags_valid_cpf_in_source():
    findings = scan_content(VALID_CPF, "src/app.js", [CPF_RULE])
    assert len(findings) == 1
    assert findings[0].severity == "critical"


def test_default_excludes_skip_markdown():
    assert scan_content(VALID_CPF, "docs/guide.md", [CPF_RULE]) == []


def test_default_excludes_skip_test_files():
    assert scan_content(VALID_CPF, "src/user.test.js", [CPF_RULE]) == []
    assert scan_content(VALID_CPF, "app/tests/user.py", [CPF_RULE]) == []


def test_files_include_globs_restrict():
    js_only = Rule(id="r", regex="secret_token", severity="high", article="X",
                   message="m", fix="f", files=["**/*.js"], exclude_files=[])
    assert scan_content("secret_token\n", "a.py", [js_only]) == []
    assert len(scan_content("secret_token\n", "src/a.js", [js_only])) == 1


def test_invalid_cpf_not_flagged():
    assert scan_content('const cpf = "123.456.789-00";\n', "src/app.js", [CPF_RULE]) == []


def test_negative_context_downgrades_to_low():
    findings = scan_content('const mockCpf = "529.982.247-25";\n', "src/app.js", [CPF_RULE])
    assert len(findings) == 1
    assert findings[0].severity == "low"
    assert "possible test data" in findings[0].note


def test_otto_ignore_same_line_with_reason():
    content = 'const cpf = "529.982.247-25"; // otto-ignore: cpf_exposure -- CPF publico da receita\n'
    assert scan_content(content, "src/app.js", [CPF_RULE]) == []


def test_otto_ignore_line_above():
    content = ('// otto-ignore: cpf_exposure -- dado sintetico aprovado\n'
               'const cpf = "529.982.247-25";\n')
    assert scan_content(content, "src/app.js", [CPF_RULE]) == []


def test_otto_ignore_without_reason_does_not_suppress():
    content = 'const cpf = "529.982.247-25"; // otto-ignore: cpf_exposure\n'
    assert len(scan_content(content, "src/app.js", [CPF_RULE])) == 1


def test_otto_ignore_other_rule_does_not_suppress():
    content = 'const cpf = "529.982.247-25"; // otto-ignore: email_hardcoded -- n/a\n'
    assert len(scan_content(content, "src/app.js", [CPF_RULE])) == 1


def test_empty_file_path_scans_everything():
    # Hook mode may pass empty file_path; globs must not exclude it.
    assert len(scan_content(VALID_CPF, "", [CPF_RULE])) == 1
