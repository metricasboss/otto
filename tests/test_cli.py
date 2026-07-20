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


def test_paths_from_nul_delimited_file_scans_both(tmp_path, capsys):
    a = tmp_path / "a.js"
    b = tmp_path / "b.js"
    a.write_text("const ok = true;\n")
    b.write_text('const cpf = "529.982.247-25";\n')
    zlist = tmp_path / "paths.zlist"
    zlist.write_bytes((str(a) + "\0" + str(b) + "\0").encode())
    assert main(["scan", "--paths-from", str(zlist), "--fail-under", "0"]) == 0
    out = capsys.readouterr().out
    assert "59/100" in out or "LGPD Art. 46" in out


def test_paths_from_handles_space_containing_path(tmp_path, capsys):
    d = tmp_path / "dir with space"
    d.mkdir()
    f = d / "file with space.js"
    f.write_text("const ok = true;\n")
    zlist = tmp_path / "paths.zlist"
    zlist.write_bytes((str(f) + "\0").encode())
    assert main(["scan", "--paths-from", str(zlist)]) == 0
    assert "100/100" in capsys.readouterr().out


def test_paths_from_additive_with_positional(tmp_path, capsys):
    a = tmp_path / "a.js"
    a.write_text("const ok = true;\n")
    b = tmp_path / "b.js"
    b.write_text('const cpf = "529.982.247-25";\n')
    zlist = tmp_path / "paths.zlist"
    zlist.write_bytes((str(b) + "\0").encode())
    assert main(["scan", str(a), "--paths-from", str(zlist), "--fail-under", "0"]) == 0
    out = capsys.readouterr().out
    assert "LGPD Art. 46" in out


def test_no_paths_given_errors(capsys):
    assert main(["scan"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "otto: no paths given" in captured.err


def test_empty_paths_from_file_and_no_positional_errors(tmp_path, capsys):
    zlist = tmp_path / "empty.zlist"
    zlist.write_bytes(b"")
    assert main(["scan", "--paths-from", str(zlist)]) == 2
    captured = capsys.readouterr()
    assert "otto: no paths given" in captured.err


def test_paths_from_missing_path_still_errors(tmp_path, capsys):
    zlist = tmp_path / "paths.zlist"
    zlist.write_bytes(b"does/not/exist\0")
    assert main(["scan", "--paths-from", str(zlist)]) == 2
    captured = capsys.readouterr()
    assert "otto: path not found: does/not/exist" in captured.err
