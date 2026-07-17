from pathlib import Path

import pytest

from otto.engine.rules import DEFAULT_EXCLUDES, Rule, load_rules


def test_load_lgpd_rules():
    rules = load_rules("lgpd")
    ids = [r.id for r in rules]
    assert "cpf_exposure" in ids
    cpf = next(r for r in rules if r.id == "cpf_exposure")
    assert cpf.severity == "critical"
    assert cpf.regulation == "lgpd"
    assert cpf.article.startswith("LGPD")


def test_load_both_merges():
    both = load_rules("both")
    regs = {r.regulation for r in both}
    assert regs == {"lgpd", "gdpr"}
    assert len(both) == len(load_rules("lgpd")) + len(load_rules("gdpr"))


def test_old_schema_gets_defaults():
    rule = next(r for r in load_rules("lgpd") if r.id == "rg_exposure")
    assert rule.files == ["**/*"]
    assert rule.exclude_files == DEFAULT_EXCLUDES
    assert rule.negative_context == []
    assert rule.validator is None
    assert rule.category == "general"


def test_invalid_regulation_raises():
    with pytest.raises(ValueError):
        load_rules("ccpa")


def test_missing_field_raises(tmp_path):
    bad = tmp_path / "lgpd" / "patterns.json"
    bad.parent.mkdir(parents=True)
    bad.write_text('{"broken": {"regex": "x"}}')
    with pytest.raises(ValueError, match="broken"):
        load_rules("lgpd", base_dir=tmp_path)
