# OTTO Privacy Review Engine — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the monolithic `scripts/scan_privacy.py` regex scanner into a deterministic privacy review engine: Python package, 0-100 score, text/JSON/SARIF output, false-positive defenses, and a `PreToolUse` hook that actually blocks before saving.

**Architecture:** A stdlib-only Python package `otto/` with four engine units (rules loader, scanner, scorer, reporters) behind a single CLI (`python3 -m otto scan`). The Claude Code hook and future surfaces (GitHub Action, MCP) all call this same engine. Rules stay in `skills/{lgpd,gdpr}/patterns.json` with a backward-compatible extended schema.

**Tech Stack:** Python ≥3.9, stdlib only (json, re, argparse, dataclasses, fnmatch, pathlib). Tests: pytest. No third-party runtime dependencies — ever.

**Spec:** `docs/superpowers/specs/2026-07-17-otto-privacy-review-engine-design.md`

## Global Constraints

- **Zero third-party Python dependencies** in `otto/` (pytest is dev-only).
- **Python ≥3.9** compatible (`from __future__ import annotations` in every module).
- **Deterministic:** same input → same findings → same score. No timestamps, no randomness, no network.
- **Score model:** start 100; deduct critical −25, high −10, medium −4, low −1; floor 0; **any critical caps score at 59**; default gate `--fail-under 60`.
- **Backward compatible `patterns.json`:** old 7-field rules must load without modification.
- **`patterns.json` files stay where they are:** `skills/lgpd/patterns.json`, `skills/gdpr/patterns.json`.
- Run all tests from repo root: `python3 -m pytest tests/ -v`.
- Commit after every task (messages given per task).

## File Map (end state)

```
otto/
├── __init__.py               # version string
├── __main__.py               # python3 -m otto
├── cli.py                    # argparse CLI, main(argv) -> int
├── hook.py                   # PreToolUse hook, main() -> int
└── engine/
    ├── __init__.py
    ├── rules.py              # Rule dataclass, load_rules()
    ├── validators.py         # validate_cpf, VALIDATORS
    ├── scanner.py            # Finding, scan_content, scan_paths
    ├── scorer.py             # ScoreResult, compute_score
    └── reporters/
        ├── __init__.py       # get_renderer(fmt)
        ├── text.py
        ├── json_out.py
        └── sarif.py
scripts/run_hook.py           # launcher copied by install.sh (replaces scan_privacy.py)
conftest.py                   # empty; puts repo root on sys.path for pytest
tests/
├── test_rules.py
├── test_validators.py
├── test_scanner.py
├── test_scanner_fp.py
├── test_scorer.py
├── test_reporters.py
├── test_cli.py
├── test_hook.py
├── test_rule_fixtures.py     # generic fixture harness
├── test_integration.py       # examples/ score regression
└── fixtures/rules/<regulation>__<rule_id>/{flag.js,clean.js}
.github/workflows/test.yml
```

`scripts/scan_privacy.py` is **deleted** in Task 11 (replaced by the package + `run_hook.py`).

---

### Task 1: Package scaffold + rules loader

**Files:**
- Create: `otto/__init__.py`, `otto/engine/__init__.py`, `otto/engine/rules.py`, `conftest.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Consumes: `skills/lgpd/patterns.json`, `skills/gdpr/patterns.json` (existing 7-field format).
- Produces: `Rule` dataclass (fields: `id, regex, severity, article, message, fix, fine, category, regulation, files, exclude_files, negative_context, validator`), `SEVERITIES` tuple, `DEFAULT_EXCLUDES` list, `load_rules(regulation: str = "both", base_dir: Optional[Path] = None) -> List[Rule]`. Raises `ValueError` on missing required field, invalid severity, or unknown regulation.

- [ ] **Step 1: Scaffold + failing test**

Create empty `conftest.py`, `otto/__init__.py` containing `__version__ = "2.0.0"`, empty `otto/engine/__init__.py`. Write `tests/test_rules.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_rules.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'otto.engine.rules'`

- [ ] **Step 3: Implement `otto/engine/rules.py`**

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

SEVERITIES = ("critical", "high", "medium", "low")

DEFAULT_EXCLUDES = [
    "**/*.md",
    "**/*.test.*",
    "**/*.spec.*",
    "**/tests/**",
    "**/test/**",
    "**/fixtures/**",
    "**/node_modules/**",
    "**/.git/**",
]

REQUIRED_FIELDS = ("regex", "severity", "article", "message", "fix")


@dataclass
class Rule:
    id: str
    regex: str
    severity: str
    article: str
    message: str
    fix: str
    fine: str = "Significant penalties"
    category: str = "general"
    regulation: str = "lgpd"
    files: List[str] = field(default_factory=lambda: ["**/*"])
    exclude_files: List[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDES))
    negative_context: List[str] = field(default_factory=list)
    validator: Optional[str] = None


def _load_file(path: Path, regulation: str) -> List[Rule]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rules: List[Rule] = []
    for rule_id, raw in data.items():
        for req in REQUIRED_FIELDS:
            if req not in raw:
                raise ValueError(f"Rule '{rule_id}' missing required field '{req}'")
        if raw["severity"] not in SEVERITIES:
            raise ValueError(f"Rule '{rule_id}' has invalid severity '{raw['severity']}'")
        rules.append(
            Rule(
                id=rule_id,
                regex=raw["regex"],
                severity=raw["severity"],
                article=raw["article"],
                message=raw["message"],
                fix=raw["fix"],
                fine=raw.get("fine", "Significant penalties"),
                category=raw.get("category", "general"),
                regulation=regulation,
                files=raw.get("files", ["**/*"]),
                exclude_files=raw.get("exclude_files", list(DEFAULT_EXCLUDES)),
                negative_context=[t.lower() for t in raw.get("negative_context", [])],
                validator=raw.get("validator"),
            )
        )
    return rules


def load_rules(regulation: str = "both", base_dir: Optional[Path] = None) -> List[Rule]:
    if regulation not in ("lgpd", "gdpr", "both"):
        raise ValueError(f"Unknown regulation: {regulation!r} (use lgpd, gdpr or both)")
    base = base_dir or Path(__file__).resolve().parent.parent.parent / "skills"
    rules: List[Rule] = []
    if regulation in ("lgpd", "both"):
        rules += _load_file(base / "lgpd" / "patterns.json", "lgpd")
    if regulation in ("gdpr", "both"):
        gdpr_path = base / "gdpr" / "patterns.json"
        if gdpr_path.exists() or regulation == "gdpr":
            rules += _load_file(gdpr_path, "gdpr")
    return rules
```

Note the `base_dir` resolution: `otto/engine/rules.py` → three `.parent`s up → repo root → `skills/`. The installed layout (Task 11) copies `skills/` next to `otto/`, so the same relative walk works there.

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_rules.py -v`
Expected: 5 passed. (If `test_missing_field_raises` fails because the gdpr dir is missing in tmp_path: the `gdpr_path.exists()` guard above handles it for "lgpd"-only base dirs.)

- [ ] **Step 5: Commit**

```bash
git add conftest.py otto/ tests/test_rules.py
git commit -m "feat(engine): add otto package with rules loader and extended schema"
```

---

### Task 2: CPF check-digit validator

**Files:**
- Create: `otto/engine/validators.py`
- Test: `tests/test_validators.py`

**Interfaces:**
- Produces: `validate_cpf(text: str) -> bool` (extracts digits from the matched text, validates the two check digits), `VALIDATORS: Dict[str, Callable[[str], bool]]` mapping `"cpf" -> validate_cpf`. Task 4 calls `VALIDATORS[rule.validator](match_text)`.

- [ ] **Step 1: Write failing test** — `tests/test_validators.py`:

```python
from otto.engine.validators import VALIDATORS, validate_cpf


def test_valid_cpf():
    assert validate_cpf("529.982.247-25") is True


def test_invalid_check_digits():
    assert validate_cpf("123.456.789-00") is False


def test_repeated_digits_invalid():
    assert validate_cpf("111.111.111-11") is False


def test_wrong_length_invalid():
    assert validate_cpf("12.345.678-9") is False


def test_registry():
    assert VALIDATORS["cpf"] is validate_cpf
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_validators.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `otto/engine/validators.py`**

```python
from __future__ import annotations

from typing import Callable, Dict


def validate_cpf(text: str) -> bool:
    """True if text contains a mathematically valid CPF (check digits ok)."""
    digits = [int(c) for c in text if c.isdigit()]
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    for i in (9, 10):
        total = sum(d * w for d, w in zip(digits[:i], range(i + 1, 1, -1)))
        if (total * 10) % 11 % 10 != digits[i]:
            return False
    return True


VALIDATORS: Dict[str, Callable[[str], bool]] = {"cpf": validate_cpf}
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_validators.py -v` — Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add otto/engine/validators.py tests/test_validators.py
git commit -m "feat(engine): add CPF check-digit validator"
```

---

### Task 3: Scanner core

**Files:**
- Create: `otto/engine/scanner.py`
- Test: `tests/test_scanner.py`

**Interfaces:**
- Consumes: `Rule` from Task 1.
- Produces: `Finding` dataclass (`rule_id, regulation, severity, category, article, message, fix, fine, file_path, line, matched_text, note=""`), `SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}`, `scan_content(content: str, file_path: str, rules: List[Rule]) -> List[Finding]`, `scan_paths(paths: List[str], rules: List[Rule]) -> List[Finding]`. Findings sorted by (severity, file_path, line); deduped on `(rule_id, file_path, line)`.

This task implements plain matching only. Globs, negative_context, otto-ignore, and validators come in Task 4 (the hooks for them are stubbed as always-pass helpers here so Task 4 only fills them in).

- [ ] **Step 1: Write failing test** — `tests/test_scanner.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_scanner.py -v` — Expected: FAIL, module not found.

- [ ] **Step 3: Implement `otto/engine/scanner.py`**

```python
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Tuple

from otto.engine.rules import Rule

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass
class Finding:
    rule_id: str
    regulation: str
    severity: str
    category: str
    article: str
    message: str
    fix: str
    fine: str
    file_path: str
    line: int
    matched_text: str
    note: str = ""


def _applies_to_file(file_path: str, rule: Rule) -> bool:
    # Filled in by Task 4 (glob include/exclude). Until then: everything applies.
    return True


def _is_suppressed(line_text: str, lines: List[str], line_num: int, rule_id: str) -> bool:
    # Filled in by Task 4 (otto-ignore). Until then: nothing is suppressed.
    return False


def _adjust_severity(rule: Rule, line_text: str) -> Tuple[str, str]:
    # Filled in by Task 4 (negative_context downgrade).
    return rule.severity, ""


def _passes_validator(rule: Rule, matched_text: str) -> bool:
    # Filled in by Task 4 (check-digit validators).
    return True


def scan_content(content: str, file_path: str, rules: List[Rule]) -> List[Finding]:
    findings: List[Finding] = []
    seen: Set[Tuple[str, str, int]] = set()
    lines = content.split("\n")
    for rule in rules:
        if not _applies_to_file(file_path, rule):
            continue
        try:
            matches = re.finditer(rule.regex, content, re.IGNORECASE | re.MULTILINE)
        except re.error as exc:
            print(f"otto: skipping rule '{rule.id}' (invalid regex: {exc})", file=sys.stderr)
            continue
        for match in matches:
            line_num = content[: match.start()].count("\n") + 1
            key = (rule.id, file_path, line_num)
            if key in seen:
                continue
            line_text = lines[line_num - 1] if line_num <= len(lines) else ""
            if _is_suppressed(line_text, lines, line_num, rule.id):
                continue
            if not _passes_validator(rule, match.group(0)):
                continue
            severity, note = _adjust_severity(rule, line_text)
            seen.add(key)
            findings.append(
                Finding(
                    rule_id=rule.id,
                    regulation=rule.regulation,
                    severity=severity,
                    category=rule.category,
                    article=rule.article,
                    message=rule.message,
                    fix=rule.fix,
                    fine=rule.fine,
                    file_path=file_path,
                    line=line_num,
                    matched_text=match.group(0)[:80],
                    note=note,
                )
            )
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.file_path, f.line))
    return findings


def scan_paths(paths: List[str], rules: List[Rule]) -> List[Finding]:
    findings: List[Finding] = []
    for raw in paths:
        path = Path(raw)
        files = [path] if path.is_file() else sorted(
            p for p in path.rglob("*") if p.is_file()
        )
        for file in files:
            try:
                content = file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            findings += scan_content(content, str(file), rules)
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.file_path, f.line))
    return findings
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_scanner.py -v` — Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add otto/engine/scanner.py tests/test_scanner.py
git commit -m "feat(engine): add scanner core with Finding, dedup and sorting"
```

---

### Task 4: False-positive layers (globs, negative_context, otto-ignore, validators)

**Files:**
- Modify: `otto/engine/scanner.py` (replace the four stub helpers)
- Test: `tests/test_scanner_fp.py`

**Interfaces:**
- Consumes: `Rule.files/exclude_files/negative_context/validator` (Task 1), `VALIDATORS` (Task 2).
- Produces: final behavior of `scan_content` — glob filtering, `negative_context` downgrade to `low` with note `"possible test data (negative context matched)"`, suppression via `otto-ignore: <rule-id> -- <reason>` (same line or line above; **reason mandatory**), validator gate.

- [ ] **Step 1: Write failing test** — `tests/test_scanner_fp.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_scanner_fp.py -v`
Expected: failures on excludes/validator/downgrade/ignore tests (stubs pass everything).

- [ ] **Step 3: Replace the four stubs in `otto/engine/scanner.py`**

Add imports at top: `from fnmatch import fnmatch` and `from otto.engine.validators import VALIDATORS`. Replace the stub helpers with:

```python
SUPPRESS_RE = re.compile(r"otto-ignore:\s*([\w,\- ]+?)\s*--\s*(\S.+)")


def _glob_match(path: str, pattern: str) -> bool:
    if fnmatch(path, pattern):
        return True
    # "**/" must also match zero directories: "**/*.md" matches "README.md"
    if pattern.startswith("**/") and fnmatch(path, pattern[3:]):
        return True
    return False


def _applies_to_file(file_path: str, rule: Rule) -> bool:
    if not file_path:
        return True  # hook mode / stdin: no path to filter on
    path = file_path.replace("\\", "/")
    if not any(_glob_match(path, g) for g in rule.files):
        return False
    if any(_glob_match(path, g) for g in rule.exclude_files):
        return False
    return True


def _is_suppressed(line_text: str, lines: List[str], line_num: int, rule_id: str) -> bool:
    candidates = [line_text]
    if line_num >= 2:
        candidates.append(lines[line_num - 2])
    for text in candidates:
        match = SUPPRESS_RE.search(text)
        if match:
            suppressed_ids = [r.strip() for r in match.group(1).split(",")]
            if rule_id in suppressed_ids:
                return True
    return False


def _adjust_severity(rule: Rule, line_text: str) -> Tuple[str, str]:
    lowered = line_text.lower()
    for term in rule.negative_context:
        if term in lowered:
            return "low", "possible test data (negative context matched)"
    return rule.severity, ""


def _passes_validator(rule: Rule, matched_text: str) -> bool:
    if rule.validator is None:
        return True
    validator = VALIDATORS.get(rule.validator)
    if validator is None:
        return True  # unknown validator name: fail open, rule still applies
    return validator(matched_text)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_scanner_fp.py tests/test_scanner.py -v`
Expected: all pass (Task 3 tests set `exclude_files=[]` where needed, so they stay green).

- [ ] **Step 5: Commit**

```bash
git add otto/engine/scanner.py tests/test_scanner_fp.py
git commit -m "feat(engine): glob filtering, negative-context downgrade, otto-ignore, validators"
```

---

### Task 5: Scorer

**Files:**
- Create: `otto/engine/scorer.py`
- Test: `tests/test_scorer.py`

**Interfaces:**
- Consumes: `Finding` (Task 3).
- Produces: `DEDUCTIONS = {"critical": 25, "high": 10, "medium": 4, "low": 1}`, `ScoreResult` dataclass (`score: int, per_file: Dict[str, int], counts: Dict[str, int]`), `compute_score(findings: List[Finding]) -> ScoreResult`.

- [ ] **Step 1: Write failing test** — `tests/test_scorer.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_scorer.py -v` — Expected: FAIL, module not found.

- [ ] **Step 3: Implement `otto/engine/scorer.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from otto.engine.scanner import Finding

DEDUCTIONS = {"critical": 25, "high": 10, "medium": 4, "low": 1}
CRITICAL_CAP = 59


def _score(findings: List[Finding]) -> int:
    score = max(0, 100 - sum(DEDUCTIONS[f.severity] for f in findings))
    if any(f.severity == "critical" for f in findings):
        score = min(score, CRITICAL_CAP)
    return score


@dataclass
class ScoreResult:
    score: int
    per_file: Dict[str, int]
    counts: Dict[str, int]


def compute_score(findings: List[Finding]) -> ScoreResult:
    files = sorted({f.file_path for f in findings})
    per_file = {
        fp: _score([f for f in findings if f.file_path == fp]) for fp in files
    }
    counts = {sev: sum(1 for f in findings if f.severity == sev) for sev in DEDUCTIONS}
    return ScoreResult(score=_score(findings), per_file=per_file, counts=counts)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_scorer.py -v` — Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add otto/engine/scorer.py tests/test_scorer.py
git commit -m "feat(engine): deterministic 0-100 scorer with critical cap at 59"
```

---

### Task 6: Reporters (text, JSON, SARIF)

**Files:**
- Create: `otto/engine/reporters/__init__.py`, `otto/engine/reporters/text.py`, `otto/engine/reporters/json_out.py`, `otto/engine/reporters/sarif.py`
- Test: `tests/test_reporters.py`

**Interfaces:**
- Consumes: `Finding` (Task 3), `ScoreResult` (Task 5).
- Produces: each reporter module exposes `render(findings: List[Finding], score: ScoreResult, regulation: str) -> str`. `otto/engine/reporters/__init__.py` exposes `get_renderer(fmt: str)` returning that callable for `"text" | "json" | "sarif"`, raising `ValueError` otherwise.

- [ ] **Step 1: Write failing test** — `tests/test_reporters.py`:

```python
import json

from otto.engine.reporters import get_renderer
from otto.engine.scanner import Finding
from otto.engine.scorer import compute_score

FINDING = Finding(
    rule_id="cpf_exposure", regulation="lgpd", severity="critical",
    category="sensitive_data", article="LGPD Art. 46 (Dados Sensíveis)",
    message="CPF brasileiro exposto no código", fix="Remova o CPF hardcoded.",
    fine="Até R$ 50 milhões", file_path="src/app.js", line=7,
    matched_text="529.982.247-25",
)
SCORE = compute_score([FINDING])


def test_text_contains_score_article_and_fix():
    out = get_renderer("text")([FINDING], SCORE, "lgpd")
    assert "59/100" in out
    assert "LGPD Art. 46" in out
    assert "Remova o CPF hardcoded." in out
    assert "src/app.js" in out


def test_text_clean_scan():
    clean = compute_score([])
    out = get_renderer("text")([], clean, "both")
    assert "100/100" in out
    assert "No violations" in out


def test_json_structure():
    data = json.loads(get_renderer("json")([FINDING], SCORE, "lgpd"))
    assert data["score"] == 59
    assert data["counts"]["critical"] == 1
    assert data["findings"][0]["rule_id"] == "cpf_exposure"
    assert data["findings"][0]["line"] == 7
    assert data["per_file"]["src/app.js"] == 59


def test_sarif_is_valid_2_1_0():
    doc = json.loads(get_renderer("sarif")([FINDING], SCORE, "lgpd"))
    assert doc["version"] == "2.1.0"
    run = doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "OTTO"
    result = run["results"][0]
    assert result["ruleId"] == "cpf_exposure"
    assert result["level"] == "error"
    loc = result["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"]["uri"] == "src/app.js"
    assert loc["region"]["startLine"] == 7
    rule_ids = [r["id"] for r in run["tool"]["driver"]["rules"]]
    assert "cpf_exposure" in rule_ids


def test_unknown_format_raises():
    import pytest
    with pytest.raises(ValueError):
        get_renderer("xml")
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_reporters.py -v` — Expected: FAIL, module not found.

- [ ] **Step 3: Implement the reporters**

`otto/engine/reporters/__init__.py`:

```python
from __future__ import annotations

from otto.engine.reporters import json_out, sarif, text

_RENDERERS = {"text": text.render, "json": json_out.render, "sarif": sarif.render}


def get_renderer(fmt: str):
    if fmt not in _RENDERERS:
        raise ValueError(f"Unknown format: {fmt!r} (use text, json or sarif)")
    return _RENDERERS[fmt]
```

`otto/engine/reporters/text.py` (port of the old `format_output`, plus score):

```python
from __future__ import annotations

from typing import List

from otto.engine.scanner import Finding
from otto.engine.scorer import ScoreResult

_REG_NAMES = {"lgpd": "LGPD", "gdpr": "GDPR", "both": "LGPD+GDPR"}
_EMOJI = {"critical": "🚨", "high": "⚠️", "medium": "⚡", "low": "ℹ️"}


def render(findings: List[Finding], score: ScoreResult, regulation: str) -> str:
    name = _REG_NAMES.get(regulation, "Privacy")
    if not findings:
        return (
            f"🛡️ OTTO - {name} Analysis\n\n"
            f"✅ No violations detected. Privacy score: {score.score}/100\n\n"
            "🛡️ OTTO protected your users today.\n"
        )

    lines = [f"🛡️ OTTO - {name} Privacy Analysis", "",
             f"❌ VIOLATIONS FOUND: {len(findings)} — Privacy score: {score.score}/100", ""]
    for i, f in enumerate(findings, 1):
        lines += [
            f"{i}. {_EMOJI[f.severity]} {f.rule_id.replace('_', ' ').title()}",
            f"   File: {f.file_path or 'stdin'}:{f.line}",
            f"   Severity: {f.severity.upper()}" + (f" ({f.note})" if f.note else ""),
            f"   Issue: {f.message}",
            f"   Legal basis: {f.article}",
            f"   Fine risk: {f.fine}",
            f"   SUGGESTED FIX: {f.fix}",
            "",
        ]
    lines += ["━" * 42, "", "📊 SUMMARY:"]
    for sev in ("critical", "high", "medium", "low"):
        if score.counts.get(sev):
            lines.append(f"   • {score.counts[sev]} {sev} violation(s) {_EMOJI[sev]}")
    lines += ["", f"📉 Privacy score: {score.score}/100"
              + (" (critical findings cap the score at 59)" if score.counts.get("critical") else ""),
              "", "🛡️ OTTO protected your users today.", ""]
    return "\n".join(lines)
```

`otto/engine/reporters/json_out.py`:

```python
from __future__ import annotations

import json
from dataclasses import asdict
from typing import List

from otto.engine.scanner import Finding
from otto.engine.scorer import ScoreResult


def render(findings: List[Finding], score: ScoreResult, regulation: str) -> str:
    return json.dumps(
        {
            "regulation": regulation,
            "score": score.score,
            "per_file": score.per_file,
            "counts": score.counts,
            "findings": [asdict(f) for f in findings],
        },
        indent=2,
        ensure_ascii=False,
    )
```

`otto/engine/reporters/sarif.py`:

```python
from __future__ import annotations

import json
from typing import List

from otto.engine.scanner import Finding
from otto.engine.scorer import ScoreResult

_LEVELS = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}


def render(findings: List[Finding], score: ScoreResult, regulation: str) -> str:
    rules_meta = {}
    results = []
    for f in findings:
        rules_meta.setdefault(
            f.rule_id,
            {
                "id": f.rule_id,
                "shortDescription": {"text": f.message},
                "fullDescription": {"text": f"{f.message} — {f.article}. Fine risk: {f.fine}"},
                "help": {"text": f.fix},
            },
        )
        results.append(
            {
                "ruleId": f.rule_id,
                "level": _LEVELS[f.severity],
                "message": {"text": f"{f.message} ({f.article}). Suggested fix: {f.fix}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": f.file_path or "stdin"},
                            "region": {"startLine": f.line},
                        }
                    }
                ],
            }
        )
    doc = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "OTTO",
                        "informationUri": "https://github.com/metricasboss/otto",
                        "rules": sorted(rules_meta.values(), key=lambda r: r["id"]),
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_reporters.py -v` — Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add otto/engine/reporters/ tests/test_reporters.py
git commit -m "feat(engine): text, json and sarif reporters with score"
```

---

### Task 7: CLI

**Files:**
- Create: `otto/cli.py`, `otto/__main__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_rules` (Task 1), `scan_paths` (Task 3), `compute_score` (Task 5), `get_renderer` (Task 6).
- Produces: `main(argv: Optional[List[str]] = None) -> int`. Usage: `otto scan <path...> [--format text|json|sarif] [--regulation lgpd|gdpr|both] [--fail-under N]`. Defaults: format=text, regulation=both, fail-under=60. Returns 0 if `score >= fail_under`, else 1. `python3 -m otto` dispatches to it.

- [ ] **Step 1: Write failing test** — `tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_cli.py -v` — Expected: FAIL, module not found.

- [ ] **Step 3: Implement**

`otto/cli.py`:

```python
from __future__ import annotations

import argparse
from typing import List, Optional

from otto.engine.reporters import get_renderer
from otto.engine.rules import load_rules
from otto.engine.scanner import scan_paths
from otto.engine.scorer import compute_score


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="otto", description="OTTO - Privacy Guardian")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Scan files or directories for privacy violations")
    scan.add_argument("paths", nargs="+", help="Files or directories to scan")
    scan.add_argument("--format", choices=["text", "json", "sarif"], default="text")
    scan.add_argument("--regulation", choices=["lgpd", "gdpr", "both"], default="both")
    scan.add_argument("--fail-under", type=int, default=60, metavar="N",
                      help="Exit non-zero if score is below N (default: 60)")
    args = parser.parse_args(argv)

    rules = load_rules(args.regulation)
    findings = scan_paths(args.paths, rules)
    score = compute_score(findings)
    print(get_renderer(args.format)(findings, score, args.regulation))
    return 0 if score.score >= args.fail_under else 1
```

`otto/__main__.py`:

```python
import sys

from otto.cli import main

sys.exit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_cli.py -v` — Expected: 6 passed.
Also smoke-test by hand: `python3 -m otto scan examples/ | head -30` — expect findings from `examples/unsafe_code.js`.

- [ ] **Step 5: Commit**

```bash
git add otto/cli.py otto/__main__.py tests/test_cli.py
git commit -m "feat(cli): otto scan with format, regulation and fail-under gate"
```

---

### Task 8: PreToolUse hook

**Files:**
- Create: `otto/hook.py`, `scripts/run_hook.py`
- Test: `tests/test_hook.py`

**Interfaces:**
- Consumes: `load_rules`, `scan_content`, `compute_score`, text renderer.
- Produces: `otto/hook.py` with `main(stdin=None, stdout=None) -> int` reading Claude Code PreToolUse JSON from stdin. Behavior:
  - Critical finding → print `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "<text report>"}}`, return 0.
  - Non-critical findings only → print `{"systemMessage": "OTTO: N non-critical privacy finding(s) ..."}`, return 0.
  - No findings / no content / invalid JSON → print nothing (invalid JSON: message on stderr), return 0. **The hook never blocks via exit code; blocking is done via the deny JSON.**
  - Regulation from `~/.claude/skills/otto/.regulation` if present, else `both`.
- `scripts/run_hook.py`: launcher that adds its own directory to `sys.path` and calls `otto.hook.main()` (needed for the installed layout where `otto/` is not on the path).

- [ ] **Step 1: Write failing test** — `tests/test_hook.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_hook.py -v` — Expected: FAIL, module not found.

- [ ] **Step 3: Implement**

`otto/hook.py`:

```python
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional, TextIO

from otto.engine.reporters.text import render
from otto.engine.rules import load_rules
from otto.engine.scanner import scan_content
from otto.engine.scorer import compute_score


def _regulation() -> str:
    reg_file = Path.home() / ".claude" / "skills" / "otto" / ".regulation"
    if reg_file.exists():
        value = reg_file.read_text(encoding="utf-8").strip()
        if value in ("lgpd", "gdpr", "both"):
            return value
    return "both"


def main(stdin: Optional[TextIO] = None, stdout: Optional[TextIO] = None) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    try:
        data = json.load(stdin)
    except (json.JSONDecodeError, ValueError):
        print("otto hook: invalid JSON input", file=sys.stderr)
        return 0

    tool_input = data.get("tool_input", {})
    content = tool_input.get("new_string") or tool_input.get("content") or ""
    file_path = tool_input.get("file_path", "")
    if not content:
        return 0

    regulation = _regulation()
    rules = load_rules(regulation)
    findings = scan_content(content, file_path, rules)
    if not findings:
        return 0

    score = compute_score(findings)
    if any(f.severity == "critical" for f in findings):
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": render(findings, score, regulation),
            }
        }
    else:
        payload = {
            "systemMessage": (
                f"OTTO: {len(findings)} non-critical privacy finding(s) in "
                f"{file_path or 'this edit'} (score {score.score}/100). "
                "Run `python3 -m otto scan <path>` for details."
            )
        }
    print(json.dumps(payload, ensure_ascii=False), file=stdout)
    return 0
```

`scripts/run_hook.py`:

```python
#!/usr/bin/env python3
"""Launcher for the OTTO PreToolUse hook in the installed layout.

install.sh copies this file next to the otto/ package; adding this file's
directory to sys.path makes `import otto` work without installation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from otto.hook import main  # noqa: E402

sys.exit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_hook.py -v` — Expected: 7 passed.
Note: `test_noncritical_only_informs_but_allows` depends on `select_all_users` being high (it is). If Task 9 later changes severities, this test's fixture content must stay a non-critical rule.

- [ ] **Step 5: Commit**

```bash
git add otto/hook.py scripts/run_hook.py tests/test_hook.py
git commit -m "feat(hook): PreToolUse hook that denies critical privacy violations"
```

---

### Task 9: Fixture harness + existing-rule cleanup

**Files:**
- Modify: `skills/lgpd/patterns.json`, `skills/gdpr/patterns.json`
- Create: `tests/test_rule_fixtures.py`, `tests/fixtures/rules/<regulation>__<rule_id>/{flag.js,clean.js}` for every existing rule
- Test: `tests/test_rule_fixtures.py`

**Interfaces:**
- Consumes: `load_rules`, `scan_content`.
- Produces: harness convention every future rule must follow — directory `tests/fixtures/rules/{regulation}__{rule_id}/` containing `flag.js` (MUST produce ≥1 finding for that rule at any severity except a downgrade) and `clean.js` (MUST produce 0 findings for that rule). Completeness test fails if any loaded rule lacks fixtures.

- [ ] **Step 1: Write the harness** — `tests/test_rule_fixtures.py`:

```python
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
```

Run: `python3 -m pytest tests/test_rule_fixtures.py -v` — Expected: `test_every_rule_has_fixtures` FAILS listing all 32 rules. That failing list is your fixture TODO.

- [ ] **Step 2: Apply rule cleanups to `skills/lgpd/patterns.json`**

Replace the listed fields on these rules (leave other rules and other fields untouched):

- `cpf_exposure` — add: `"category": "sensitive_data"`, `"validator": "cpf"`, `"negative_context": ["mock", "example", "exemplo", "faker", "dummy", "teste"]`
- `rg_exposure` — add: `"category": "sensitive_data"`
- `cnpj_exposure` — add: `"category": "sensitive_data"`
- `email_hardcoded` — replace regex (old one had a broken lookahead) and add context:
  - `"regex": "[\"'][A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}[\"']"`
  - `"negative_context": ["example.com", "test@", "noreply@", "no-reply@", "dummy"]`
- `phone_br` — add: `"negative_context": ["example", "teste", "mock"]`
- `user_logging` — replace regex so its own suggested fix (`console.log('User ID:', user.id)`) stops matching. The lookahead skips the call when `user.id` appears anywhere in the arguments:
  - `"regex": "(console\\.log|logger\\.(info|debug|error|warn))\\((?![^)]*\\buser\\.id\\b)[^)]*\\buser\\b[^)]*\\)"`
- `request_logging` — replace regex so sanitized logging stops matching:
  - `"regex": "^(?!.*sanitiz).*(console\\.log|logger\\.\\w+)\\([^)]*req\\.body"`
- `tracking_without_consent` — replace regex so consent-guarded calls stop matching:
  - `"regex": "^(?!.*hasConsent).*analytics\\.track\\([^)]*(email|cpf|phone)"`
- `cookie_without_consent` — replace regex (old negative lookahead was position-inert, matched everything):
  - `"regex": "^(?!.*consent).*document\\.cookie\\s*="`
- `sql_injection_risk` — replace regex to also catch template literals opened with backticks:
  - `` "regex": "query\\([\"'`][^\"'`)]*(\\$\\{[^}]+\\}|[\"'`]\\s*\\+\\s*[a-zA-Z])" ``

- [ ] **Step 3: Apply rule cleanups to `skills/gdpr/patterns.json`**

- `ssn_us_exposure`, `national_id_eu`, `nhs_number` — add: `"category": "sensitive_data"`
- `email_hardcoded` — same regex replacement and `negative_context` as the LGPD version (Step 2)
- `phone_international` — replace regex (old one matched any 4+ digits after `+`, e.g. timezone offsets):
  - `"regex": "\\+\\d{1,3}[\\s.-]?\\(?\\d{2,4}\\)?[\\s.-]?\\d{3,4}[\\s.-]?\\d{4,9}"`
- `user_logging` — same regex replacement as LGPD (Step 2)
- `request_logging` — same regex replacement as LGPD (Step 2)
- `tracking_without_consent` — `"regex": "^(?!.*hasConsent).*analytics\\.track\\([^)]*(email|ssn|phone)"`
- `cookie_without_consent` — same regex replacement as LGPD (Step 2)
- `sql_injection_risk` — same regex replacement as LGPD (Step 2)
- `health_data_exposure` — add: `"category": "special_category"`, `"negative_context": ["healthcheck", "health_check", "/health"]`
- `biometric_data` — add: `"category": "special_category"`, `"negative_context": ["device fingerprint", "browser fingerprint", "fingerprintjs"]`

- [ ] **Step 4: Author fixtures for all 32 existing rules**

Create `tests/fixtures/rules/<key>/flag.js` and `clean.js` with exactly one line each from this table. GDPR rules that duplicate LGPD ones use the same content unless listed separately.

| key | flag.js | clean.js |
|---|---|---|
| lgpd__cpf_exposure | `const cpf = "529.982.247-25";` | `const cpf = "123.456.789-00";` |
| lgpd__rg_exposure | `const rg = "12.345.678-9";` | `const version = "v1.2.3";` |
| lgpd__cnpj_exposure | `const cnpj = "12.345.678/0001-95";` | `const cnpj = process.env.COMPANY_CNPJ;` |
| lgpd__email_hardcoded | `const admin = "lucian@empresa.com.br";` | `const admin = process.env.ADMIN_EMAIL;` |
| lgpd__phone_br | `const tel = "(11) 99999-8888";` | `const tel = process.env.SUPPORT_PHONE;` |
| lgpd__user_logging | `console.log('user data', user);` | `console.log('User ID:', user.id);` |
| lgpd__request_logging | `console.log('body', req.body);` | `logger.info(sanitize(req.body));` |
| lgpd__tracking_without_consent | `analytics.track('login', { email: user.email });` | `if (user.hasConsent('analytics')) analytics.track('login', { email: user.email });` |
| lgpd__select_all_users | `db.query("SELECT * FROM users");` | `db.query("SELECT id, name FROM users");` |
| lgpd__password_plaintext | `const password = "hunter2secret";` | `const password = await bcrypt.hash(input, 10);` |
| lgpd__api_key_exposure | `const api_key = "sk_live_1234567890abcdefghij";` | `const api_key = process.env.API_KEY;` |
| lgpd__localstorage_sensitive | `localStorage.setItem('token', jwt);` | `sessionStorage.setItem('theme', 'dark');` |
| lgpd__cookie_without_consent | `document.cookie = "session=abc";` | `if (cookieConsent.hasConsent('functional')) document.cookie = "pref=1";` |
| lgpd__external_data_sharing | `axios.post('https://api.thirdparty.com', user.profile);` | `axios.post('/internal/metrics', { count: 1 });` |
| lgpd__sql_injection_risk | ``db.query(`SELECT * FROM users WHERE id = ${userId}`);`` | `db.query('SELECT * FROM users WHERE id = ?', [userId]);` |
| gdpr__ssn_us_exposure | `const ssn = "078-05-1120";` | `const date = "2026-07-17";` |
| gdpr__national_id_eu | `const id = "AB1234567";` | `const country = "BR";` |
| gdpr__nhs_number | `const nhs = "943 476 5919";` | `const t = "12 345 6789";` |
| gdpr__email_hardcoded | same as lgpd | same as lgpd |
| gdpr__phone_international | `const phone = "+44 20 7946 0958";` | `const tz = "+0200";` |
| gdpr__user_logging | same as lgpd | same as lgpd |
| gdpr__request_logging | same as lgpd | same as lgpd |
| gdpr__tracking_without_consent | `analytics.track('signup', { email: user.email });` | `if (user.hasConsent('analytics')) analytics.track('signup', { email: user.email });` |
| gdpr__select_all_users | `db.query("SELECT * FROM customers");` | `db.query("SELECT id FROM customers");` |
| gdpr__password_plaintext | same as lgpd | same as lgpd |
| gdpr__api_key_exposure | same as lgpd | same as lgpd |
| gdpr__localstorage_sensitive | same as lgpd | same as lgpd |
| gdpr__cookie_without_consent | same as lgpd | same as lgpd |
| gdpr__external_data_sharing | same as lgpd | same as lgpd |
| gdpr__sql_injection_risk | same as lgpd | same as lgpd |
| gdpr__health_data_exposure | `const diagnosis = "F41.1";` | `const healthcheckUrl = "/healthz";` |
| gdpr__biometric_data | `enrollFingerprint(user.id);` | `const shape = "geometric";` |

- [ ] **Step 5: Run full suite, fix regex fallout**

Run: `python3 -m pytest tests/ -v`
Expected: all pass. If a flag fixture doesn't trigger or a clean fixture triggers, the regex from Steps 2-3 is wrong for that case — adjust the regex (not the fixture) until the pair passes. The fixture pair is the contract.

- [ ] **Step 6: Commit**

```bash
git add skills/ tests/test_rule_fixtures.py tests/fixtures/
git commit -m "feat(rules): fixture harness for every rule + tighten loose regexes"
```

---

### Task 10: New rules (12)

**Files:**
- Modify: `skills/lgpd/patterns.json` (8 new), `skills/gdpr/patterns.json` (4 new)
- Create: fixture pairs for each new rule
- Test: existing harness (`tests/test_rule_fixtures.py`) — completeness test forces the fixtures.

**Interfaces:**
- Consumes: harness convention from Task 9.
- Produces: 12 new rules loaded by `load_rules`; total rule count 44.

- [ ] **Step 1: Add 8 rules to `skills/lgpd/patterns.json`**

```json
"pii_in_url": {
  "regex": "[?&](cpf|email|telefone|phone|rg|cnpj)=",
  "severity": "high",
  "category": "data_exposure",
  "article": "LGPD Art. 46 (Segurança)",
  "message": "Dado pessoal transmitido em query string (fica em logs de servidor, proxies e histórico)",
  "fix": "Envie dados pessoais no body de um POST, nunca na URL.",
  "fine": "Até R$ 50 milhões"
},
"gtag_pii": {
  "regex": "(gtag|dataLayer\\.push|mixpanel\\.track|amplitude\\.track)\\([^)]*(email|cpf|phone|telefone)",
  "severity": "critical",
  "category": "consent",
  "article": "LGPD Art. 7º I (Consentimento)",
  "message": "PII enviado para ferramenta de analytics/tag manager",
  "fix": "Envie apenas IDs pseudonimizados: gtag('event', 'login', { user_id: hash(id) })",
  "fine": "Até R$ 50 milhões"
},
"pii_in_error_message": {
  "regex": "(throw\\s+new\\s+Error|raise\\s+\\w*(Error|Exception))\\([^)]*(cpf|email|user\\.)",
  "severity": "medium",
  "category": "data_exposure",
  "article": "LGPD Art. 46 (Segurança)",
  "message": "Dado pessoal em mensagem de erro (pode vazar em logs e telas de erro)",
  "fix": "Inclua apenas IDs no erro: throw new Error(`User ${user.id} not found`)",
  "fine": "Até R$ 50 milhões"
},
"hardcoded_jwt": {
  "regex": "eyJ[A-Za-z0-9_-]{20,}\\.[A-Za-z0-9_-]{10,}",
  "severity": "high",
  "category": "secrets",
  "article": "LGPD Art. 46 (Segurança)",
  "message": "JWT hardcoded no código (tokens carregam identidade do titular)",
  "fix": "Remova o token. Use variável de ambiente ou secret manager.",
  "fine": "Até R$ 50 milhões"
},
"ip_logging": {
  "regex": "(console\\.log|logger\\.\\w+)\\([^)]*(req\\.ip|remote_addr|x-forwarded-for)",
  "severity": "medium",
  "category": "data_exposure",
  "article": "LGPD Art. 46 (IP é dado pessoal)",
  "message": "Endereço IP sendo logado sem anonimização",
  "fix": "Anonimize antes de logar: logger.info(anonymizeIp(req.ip))",
  "fine": "Até R$ 50 milhões"
},
"geolocation_without_consent": {
  "regex": "^(?!.*consent).*(getCurrentPosition|watchPosition)\\s*\\(",
  "severity": "medium",
  "category": "consent",
  "article": "LGPD Art. 7º I (Consentimento)",
  "message": "Coleta de geolocalização sem verificação de consentimento no mesmo fluxo",
  "fix": "Condicione: if (user.hasConsent('geolocation')) navigator.geolocation.getCurrentPosition(...)",
  "fine": "Até R$ 50 milhões"
},
"webhook_pii": {
  "regex": "(hooks\\.slack\\.com|discord\\.com/api/webhooks)",
  "severity": "high",
  "category": "third_party",
  "article": "LGPD Art. 7º I + Art. 16 (Compartilhamento)",
  "message": "Webhook de terceiro no código — verifique se dados pessoais fluem para ele",
  "fix": "Garanta minimização: envie apenas dados agregados/anonimizados ao webhook.",
  "fine": "Até R$ 50 milhões"
},
"retention_without_ttl": {
  "regex": "^(?!.*(ttl|expire|EX)).*(cache|redis)\\.set\\([^)]*(user|email|cpf|profile)",
  "severity": "medium",
  "category": "retention",
  "article": "LGPD Art. 15/16 (Término do tratamento)",
  "message": "Dado pessoal em cache sem TTL — retenção indefinida viola término do tratamento",
  "fix": "Defina expiração: cache.set(key, value, { ttl: 3600 })",
  "fine": "Até R$ 50 milhões"
}
```

- [ ] **Step 2: Add 4 rules to `skills/gdpr/patterns.json`**

```json
"pii_in_url": {
  "regex": "[?&](ssn|email|phone|dob)=",
  "severity": "high",
  "category": "data_exposure",
  "article": "GDPR Art. 32 (Security)",
  "message": "Personal data transmitted in query string (persisted in server logs, proxies, history)",
  "fix": "Send personal data in a POST body, never in the URL.",
  "fine": "Up to €20M or 4% turnover"
},
"gtag_pii": {
  "regex": "(gtag|dataLayer\\.push|mixpanel\\.track|amplitude\\.track)\\([^)]*(email|ssn|phone)",
  "severity": "critical",
  "category": "consent",
  "article": "GDPR Art. 6(1)(a) (Consent)",
  "message": "PII sent to analytics/tag management tool",
  "fix": "Send only pseudonymized IDs: gtag('event', 'login', { user_id: hash(id) })",
  "fine": "Up to €20M or 4% turnover"
},
"consent_default_true": {
  "regex": "(consent|opt[_-]?in)\\s*[:=]\\s*true",
  "severity": "high",
  "category": "consent",
  "article": "GDPR Art. 7(3) + Recital 32 (pre-ticked consent is invalid)",
  "message": "Consent defaulting to true — pre-ticked consent is not valid consent",
  "fix": "Default to false and require an affirmative user action to enable.",
  "fine": "Up to €20M or 4% turnover"
},
"dob_hardcoded": {
  "regex": "(birth[_-]?date|date[_-]?of[_-]?birth|dob)\\s*[:=]\\s*[\"']\\d",
  "severity": "medium",
  "category": "sensitive_data",
  "article": "GDPR Art. 32 (Security)",
  "message": "Date of birth hardcoded in code",
  "fix": "Remove the hardcoded date of birth; fetch from a secure source.",
  "fine": "Up to €20M or 4% turnover"
}
```

- [ ] **Step 3: Run harness to see the 12 missing fixture dirs**

Run: `python3 -m pytest tests/test_rule_fixtures.py::test_every_rule_has_fixtures -v`
Expected: FAIL listing exactly the 12 new keys.

- [ ] **Step 4: Author the 12 fixture pairs**

| key | flag.js | clean.js |
|---|---|---|
| lgpd__pii_in_url | `fetch('/api/user?cpf=' + cpf);` | `fetch('/api/user/' + id);` |
| lgpd__gtag_pii | `gtag('event', 'login', { email: user.email });` | `gtag('event', 'login', { user_id: hash(id) });` |
| lgpd__pii_in_error_message | `throw new Error('Not found: ' + user.email);` | `throw new Error('User not found: ' + id);` |
| lgpd__hardcoded_jwt | `const t = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0In0";` | `const t = process.env.JWT_TOKEN;` |
| lgpd__ip_logging | `logger.info('client', req.ip);` | `logger.info('request received');` |
| lgpd__geolocation_without_consent | `navigator.geolocation.getCurrentPosition(cb);` | `if (user.hasConsent('geo')) navigator.geolocation.getCurrentPosition(cb); // consent` |
| lgpd__webhook_pii | `fetch('https://hooks.slack.com/services/T00/B00/xyz', opts);` | `fetch(process.env.ALERT_WEBHOOK_URL, opts);` |
| lgpd__retention_without_ttl | `cache.set('profile:' + id, user);` | `cache.set('profile:' + id, user, { ttl: 3600 });` |
| gdpr__pii_in_url | `fetch('/api/user?email=' + email);` | `fetch('/api/user/' + id);` |
| gdpr__gtag_pii | `mixpanel.track('signup', { email: user.email });` | `mixpanel.track('signup', { user_id: hash(id) });` |
| gdpr__consent_default_true | `const settings = { consent: true };` | `const settings = { consent: false };` |
| gdpr__dob_hardcoded | `const dob = "1990-04-12";` | `const dob = row.date_of_birth;` |

Note `gdpr__dob_hardcoded/flag.js`: the line must be exactly `const dob = "1990-04-12";` — `dob =` followed by a quoted digit matches. The clean line has no quoted digit after the assignment.

- [ ] **Step 5: Run full suite**

Run: `python3 -m pytest tests/ -v`
Expected: all pass, harness now parametrizes 44 rules. Same contract as Task 9: if a pair fails, fix the regex, not the fixture.

- [ ] **Step 6: Commit**

```bash
git add skills/ tests/fixtures/
git commit -m "feat(rules): 12 new rules (PII in URLs, analytics, webhooks, retention, consent defaults)"
```

---

### Task 11: install.sh PreToolUse migration, delete legacy scanner, README

**Files:**
- Modify: `install.sh`, `README.md`, `QUICKSTART.md` (if it references `scan_privacy.py`)
- Delete: `scripts/scan_privacy.py`

**Interfaces:**
- Consumes: `scripts/run_hook.py` (Task 8), `otto/` package, `skills/` patterns.
- Produces: installed layout `~/.claude/skills/otto/engine/{otto/, skills/, run_hook.py}` plus the existing `SKILL.md`/`.regulation` handling; `~/.claude/settings.json` gets a **PreToolUse** hook and any legacy OTTO PostToolUse hooks are removed.

- [ ] **Step 1: Update the copy logic in `install.sh` (function `install_for_editor`)**

Replace the lines that copy the scanner:

```bash
# OLD (remove):
mkdir -p "$skills_dir/scripts"
cp "$SCRIPT_DIR/scripts/scan_privacy.py" "$skills_dir/scripts/"
chmod +x "$skills_dir/scripts/scan_privacy.py"
```

```bash
# NEW:
mkdir -p "$skills_dir/engine"
cp -R "$SCRIPT_DIR/otto" "$skills_dir/engine/otto"
mkdir -p "$skills_dir/engine/skills/lgpd" "$skills_dir/engine/skills/gdpr"
cp "$SCRIPT_DIR/skills/lgpd/patterns.json" "$skills_dir/engine/skills/lgpd/"
cp "$SCRIPT_DIR/skills/gdpr/patterns.json" "$skills_dir/engine/skills/gdpr/"
cp "$SCRIPT_DIR/scripts/run_hook.py" "$skills_dir/engine/run_hook.py"
chmod +x "$skills_dir/engine/run_hook.py"
```

Keep the existing SKILL.md / regulation-specific copy logic untouched.

- [ ] **Step 2: Replace the hook configuration (function `configure_claude_hooks`)**

Replace the embedded Python block with:

```python
import json, sys

settings_file = '$settings_file'
skills_dir = '$skills_dir'

with open(settings_file) as f:
    settings = json.load(f)

hooks = settings.setdefault('hooks', {})

# Remove legacy OTTO PostToolUse hooks (pre-2.0 installs)
if 'PostToolUse' in hooks:
    hooks['PostToolUse'] = [
        h for h in hooks['PostToolUse']
        if 'scan_privacy.py' not in json.dumps(h)
    ]
    if not hooks['PostToolUse']:
        del hooks['PostToolUse']

pre = hooks.setdefault('PreToolUse', [])
otto_hook = {
    'matcher': 'Edit|Write',
    'hooks': [{
        'type': 'command',
        'command': f'python3 {skills_dir}/engine/run_hook.py'
    }]
}
# Replace any previous OTTO PreToolUse entry, then append the current one
pre[:] = [h for h in pre if 'run_hook.py' not in json.dumps(h)]
pre.append(otto_hook)

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
```

- [ ] **Step 3: Delete the legacy scanner and update docs**

```bash
git rm scripts/scan_privacy.py
```

In `README.md`:
- "Standalone Scanner" section: replace the `python3 ~/.claude/skills/otto/scripts/scan_privacy.py myfile.js` command with:
  ```bash
  python3 -m otto scan src/ --format text          # from a repo checkout
  python3 -m otto scan src/ --format sarif > otto.sarif
  ```
- "Automatic Protection" section: keep the "Before edits: Blocks" claim — it is now true — and add one line: "Critical violations deny the edit via a PreToolUse hook; the agent receives the article and suggested fix and can self-correct."
- Troubleshooting "Hooks not working": update paths `scripts/scan_privacy.py` → `engine/run_hook.py`, and `~/.claude/skills/otto/scripts/patterns.json` → `~/.claude/skills/otto/engine/skills/<regulation>/patterns.json`.
- Project Structure section: update the tree to the new layout (otto/ package, scripts/run_hook.py, tests/).

Check `QUICKSTART.md` and `DEPLOY.md` for `scan_privacy.py` references and apply the same substitutions:

```bash
grep -rn "scan_privacy" README.md QUICKSTART.md DEPLOY.md install.sh
```
Expected after edits: no matches.

- [ ] **Step 4: Verify installer end-to-end in a sandbox HOME**

```bash
HOME=/tmp/otto-test-home bash install.sh lgpd
cat /tmp/otto-test-home/.claude/settings.json
echo '{"tool_name":"Write","tool_input":{"file_path":"a.js","content":"const cpf = \"529.982.247-25\";"}}' \
  | python3 /tmp/otto-test-home/.claude/skills/otto/engine/run_hook.py
```
Expected: settings.json contains a `PreToolUse` entry (and no OTTO `PostToolUse`); the hook prints a deny JSON with `"permissionDecision": "deny"`.

- [ ] **Step 5: Commit**

```bash
git add install.sh README.md QUICKSTART.md DEPLOY.md
git rm --cached scripts/scan_privacy.py 2>/dev/null; true
git commit -m "feat(install): PreToolUse hook with legacy migration; retire scan_privacy.py"
```

---

### Task 12: CI + integration score regression

**Files:**
- Create: `.github/workflows/test.yml`, `tests/test_integration.py`
- Modify: `examples/unsafe_code.js` (make its CPF check-digit valid so the CPF rule still fires)

**Interfaces:**
- Consumes: everything above.
- Produces: green CI on pushes/PRs; pinned score contract for `examples/`.

- [ ] **Step 1: Write the integration test** — `tests/test_integration.py`:

```python
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
```

- [ ] **Step 2: Run and fix the examples**

Run: `python3 -m pytest tests/test_integration.py -v`

Two known adjustments:
1. In `examples/unsafe_code.js`, replace any CPF literal with the check-digit-valid `529.982.247-25` (the validator from Task 2 rejects fake CPFs, which is correct — the unsafe example must use a *valid-shaped* one to demonstrate the rule).
2. If `safe_code.js` trips any rule, that is a false positive by definition (the file is the compliant reference). Fix the **rule** (tighten regex or add `negative_context`) — never weaken the test.

Re-run until both pass.

- [ ] **Step 3: Create `.github/workflows/test.yml`**

```yaml
name: tests

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install pytest
      - run: python3 -m pytest tests/ -v
      - name: OTTO self-scan (sanity)
        run: python3 -m otto scan examples/unsafe_code.js --fail-under 0
```

- [ ] **Step 4: Full suite + commit**

Run: `python3 -m pytest tests/ -v` — Expected: all pass.

```bash
git add .github/workflows/test.yml tests/test_integration.py examples/
git commit -m "ci: test workflow + pinned score regression for examples"
```

---

## Self-Review Notes (already applied)

- Spec coverage: architecture→T1-8, scoring→T5, rules schema/FP→T1/T4/T9, ~40 rules→T9/T10 (44 total), hook PreToolUse→T8/T11, SARIF→T6, tests-per-rule→T9 harness, CI→T12, success criteria→T12 + T11 Step 4. Spec's "score ≤59 for unsafe example" and "hook denies valid CPF" are asserted in T12/T11.
- The spec says "current 28 rules"; actual count is 32 (15 LGPD + 17 GDPR). The plan uses the real count.
- Type consistency: `render(findings, score, regulation)` uniform across reporters; `Finding`/`ScoreResult` field names identical in Tasks 3/5/6/8.
