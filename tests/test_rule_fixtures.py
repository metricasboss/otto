from pathlib import Path

import pytest

from otto.engine.rules import load_rules
from otto.engine.scanner import scan_content

FIXTURES = Path(__file__).parent / "fixtures" / "rules"
ALL_RULES = {f"{r.regulation}__{r.id}": r for r in load_rules("both")}


def test_every_rule_has_fixtures():
    missing = [key for key in ALL_RULES
               if not (FIXTURES / key / "flag.js").exists()
               or not (FIXTURES / key / "clean.js").exists()]
    assert missing == [], f"Rules without fixtures: {missing}"


def test_no_orphan_fixture_dirs():
    orphans = [d.name for d in FIXTURES.iterdir() if d.is_dir() and d.name not in ALL_RULES]
    assert orphans == [], f"Fixture dirs without a rule: {orphans}"


@pytest.mark.parametrize("key", sorted(ALL_RULES), ids=str)
def test_flag_fixture_flags(key):
    rule = ALL_RULES[key]
    content = (FIXTURES / key / "flag.js").read_text(encoding="utf-8")
    # synthetic src/ path so DEFAULT_EXCLUDES do not swallow the fixture
    findings = scan_content(content, "src/app/flag.js", [rule])
    assert findings, f"{key}: flag.js did not trigger the rule"
    assert findings[0].severity == rule.severity, (
        f"{key}: flag.js was downgraded ({findings[0].note}); "
        "flag fixtures must not contain negative-context terms"
    )


@pytest.mark.parametrize("key", sorted(ALL_RULES), ids=str)
def test_clean_fixture_is_clean(key):
    rule = ALL_RULES[key]
    content = (FIXTURES / key / "clean.js").read_text(encoding="utf-8")
    findings = scan_content(content, "src/app/clean.js", [rule])
    assert findings == [], f"{key}: clean.js triggered {[f.rule_id for f in findings]}"
