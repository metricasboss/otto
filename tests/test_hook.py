import io
import json

from otto.hook import main


def run_hook(payload):
    stdin = io.StringIO(json.dumps(payload))
    stdout = io.StringIO()
    code = main(stdin=stdin, stdout=stdout)
    out = stdout.getvalue()
    return code, json.loads(out) if out.strip() else None


def test_critical_content_denied():
    code, out = run_hook({
        "tool_name": "Write",
        "tool_input": {"file_path": "src/app.js",
                       "content": 'const cpf = "529.982.247-25";\n'},
    })
    assert code == 0
    hso = out["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert "LGPD Art. 46" in hso["permissionDecisionReason"]


def test_edit_new_string_scanned():
    code, out = run_hook({
        "tool_name": "Edit",
        "tool_input": {"file_path": "src/app.js", "old_string": "x",
                       "new_string": 'console.log("body", req.body);\n'},
    })
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_clean_content_silent():
    code, out = run_hook({
        "tool_name": "Write",
        "tool_input": {"file_path": "src/app.js", "content": "const ok = true;\n"},
    })
    assert code == 0
    assert out is None


def test_noncritical_only_informs_but_allows():
    code, out = run_hook({
        "tool_name": "Write",
        "tool_input": {"file_path": "src/app.js",
                       "content": 'db.query("SELECT * FROM users");\n'},
    })
    assert code == 0
    assert "hookSpecificOutput" not in out
    assert "OTTO" in out["systemMessage"]


def test_test_file_edit_not_blocked():
    code, out = run_hook({
        "tool_name": "Write",
        "tool_input": {"file_path": "src/user.test.js",
                       "content": 'const cpf = "529.982.247-25";\n'},
    })
    assert out is None


def test_invalid_json_exits_zero():
    stdin = io.StringIO("not json{")
    stdout = io.StringIO()
    assert main(stdin=stdin, stdout=stdout) == 0
    assert stdout.getvalue() == ""


def test_empty_content_exits_zero():
    code, out = run_hook({"tool_name": "Write", "tool_input": {"file_path": "a.js"}})
    assert code == 0 and out is None


def test_innocent_health_object_not_denied():
    code, out = run_hook({
        "tool_name": "Write",
        "tool_input": {"file_path": "src/app.js",
                       "content": "const health = { status: 'ok' };\n"},
    })
    assert code == 0
    if out is not None:
        assert "hookSpecificOutput" not in out
