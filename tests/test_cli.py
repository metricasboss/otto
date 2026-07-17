import json

import pytest

from otto.cli import main


@pytest.fixture
def dirty_dir(tmp_path):
    (tmp_path / "app.js").write_text('const cpf = "529.982.247-25";\n')
    return tmp_path


@pytest.fixture
def clean_dir(tmp_path):
    (tmp_path / "app.js").write_text("const ok = true;\n")
    return tmp_path


def test_clean_scan_exits_zero(clean_dir, capsys):
    assert main(["scan", str(clean_dir)]) == 0
    assert "100/100" in capsys.readouterr().out


def test_critical_fails_default_gate(dirty_dir, capsys):
    assert main(["scan", str(dirty_dir)]) == 1
    out = capsys.readouterr().out
    assert "59/100" in out
    assert "LGPD Art. 46" in out


def test_fail_under_zero_always_passes(dirty_dir):
    assert main(["scan", str(dirty_dir), "--fail-under", "0"]) == 0


def test_json_format(dirty_dir, capsys):
    main(["scan", str(dirty_dir), "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["score"] == 59


def test_sarif_format(dirty_dir, capsys):
    main(["scan", str(dirty_dir), "--format", "sarif"])
    data = json.loads(capsys.readouterr().out)
    assert data["version"] == "2.1.0"


def test_regulation_flag(dirty_dir):
    # CPF rule is LGPD-only: gdpr-only scan of a CPF passes
    assert main(["scan", str(dirty_dir), "--regulation", "gdpr"]) == 0


def test_nonexistent_path_errors(capsys):
    assert main(["scan", "does/not/exist"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "otto: path not found: does/not/exist" in captured.err


def test_nonexistent_path_alongside_valid_path_still_errors(clean_dir, capsys):
    assert main(["scan", str(clean_dir), "does/not/exist"]) == 2
    captured = capsys.readouterr()
    assert "otto: path not found: does/not/exist" in captured.err


def test_valid_path_still_works_after_existence_check(clean_dir, capsys):
    assert main(["scan", str(clean_dir)]) == 0
    assert "100/100" in capsys.readouterr().out
