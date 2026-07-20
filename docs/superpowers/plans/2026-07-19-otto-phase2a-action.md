# OTTO Phase 2a — Engine Hardening + GitHub Action Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the four Phase 1 hardening gaps, then ship a composite GitHub Action that reviews PR-changed files with the OTTO engine: sticky score comment, SARIF annotations, fail-under gate.

**Architecture:** Hardening touches `otto/hook.py`, `otto/engine/reporters/sarif.py`, `otto/engine/{rules,scanner}.py`, and `install.sh`. The Action is `action.yml` (composite, repo root) whose only logic-bearing code is a new stdlib module `otto/action/report.py` (JSON report → markdown comment); everything else is thin bash/github-script steps. Dogfooding workflow validates the Action live on the Phase 2a PR itself.

**Tech Stack:** Python ≥3.9 stdlib only; composite GitHub Action (bash + `actions/github-script`); pytest (dev-only).

**Spec:** `docs/superpowers/specs/2026-07-18-otto-github-action-design.md`

## Global Constraints

- **Zero third-party Python dependencies**; Python ≥3.9; `from __future__ import annotations` in every module; deterministic.
- Current suite is **157 green** (`python3 -m pytest tests/ -v` from repo root) and must stay green through every task.
- Action inputs, exact names and defaults: `fail-under`=`"60"`, `regulation`=`"both"`, `comment`=`"true"`, `sarif`=`"true"`.
- Sticky comment marker, exact string: `<!-- otto-privacy-report -->`.
- The Action never fails a job because commenting or SARIF upload failed; the ONLY failure paths are the gate (score < fail-under), the non-PR-event guard, and real scan errors.
- Fixture-harness contract from Phase 1 holds: every rule has `flag.js`/`clean.js`; fix regexes, never weaken fixtures.
- Third-party action versions: known-good majors are `actions/checkout@v4`, `actions/setup-python@v5`, `actions/github-script@v7`, `github/codeql-action/upload-sarif@v3`. Tasks that reference them must verify the newest existing major with `gh api repos/<owner>/<repo>/tags --jq '.[].name' | head` and pin the newest (the Node 20 deprecation warning means newer majors likely exist); if the check fails offline, use the known-good major.

## File Map (end state of new/changed files)

```
action.yml                          # NEW: composite action, repo root
otto/action/__init__.py             # NEW: empty
otto/action/report.py               # NEW: build_comment() + `-m otto.action.report` shim
otto/hook.py                        # MODIFIED: MultiEdit edits[] coverage
otto/engine/reporters/sarif.py      # MODIFIED: relative URIs
otto/engine/rules.py                # MODIFIED: case_sensitive field
otto/engine/scanner.py              # MODIFIED: per-rule flags
skills/gdpr/patterns.json           # MODIFIED: national_id_eu case_sensitive
install.sh                          # MODIFIED: legacy dir cleanup, --no-hooks cleanup split
.github/workflows/test.yml          # MODIFIED: action version bumps
.github/workflows/otto.yml          # NEW: dogfooding workflow
README.md                           # MODIFIED: GitHub Action section
tests/test_hook.py                  # MODIFIED: +2 tests
tests/test_reporters.py             # MODIFIED: +3 tests
tests/test_scanner.py               # MODIFIED: +2 tests
tests/test_rules.py                 # MODIFIED: +1 test
tests/test_action_report.py         # NEW
tests/fixtures/rules/gdpr__national_id_eu/clean.js  # MODIFIED
```

---

### Task 1: MultiEdit hook coverage

**Files:**
- Modify: `otto/hook.py:32-36`
- Test: `tests/test_hook.py`

**Interfaces:**
- Consumes: existing `main(stdin, stdout)` and test helper `run_hook(payload)` already in `tests/test_hook.py`.
- Produces: hook scans the concatenation of `new_string`, `content`, and every `edits[].new_string` in `tool_input`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_hook.py`:

```python
def test_multiedit_payload_scanned():
    code, out = run_hook({
        "tool_name": "MultiEdit",
        "tool_input": {
            "file_path": "src/app.js",
            "edits": [
                {"old_string": "a", "new_string": "const ok = true;"},
                {"old_string": "b", "new_string": 'const cpf = "529.982.247-25";'},
            ],
        },
    })
    assert code == 0
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_multiedit_clean_payload_silent():
    code, out = run_hook({
        "tool_name": "MultiEdit",
        "tool_input": {
            "file_path": "src/app.js",
            "edits": [{"old_string": "a", "new_string": "const ok = true;"}],
        },
    })
    assert code == 0
    assert out is None
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_hook.py -v`
Expected: `test_multiedit_payload_scanned` FAILS (out is None — edits never scanned); `test_multiedit_clean_payload_silent` passes vacuously.

- [ ] **Step 3: Implement** — in `otto/hook.py`, replace the two content-extraction lines:

```python
    tool_input = data.get("tool_input", {})
    parts = [
        tool_input.get("new_string") or "",
        tool_input.get("content") or "",
    ]
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        parts += [e.get("new_string") or "" for e in edits if isinstance(e, dict)]
    content = "\n".join(p for p in parts if p)
    file_path = tool_input.get("file_path", "")
    if not content:
        return 0
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_hook.py -v` — Expected: 9 passed.
Then full suite: `python3 -m pytest tests/ -q` — Expected: 159 passed.

- [ ] **Step 5: Commit**

```bash
git add otto/hook.py tests/test_hook.py
git commit -m "fix(hook): scan MultiEdit edits[] payloads"
```

---

### Task 2: SARIF path relativization

**Files:**
- Modify: `otto/engine/reporters/sarif.py`
- Test: `tests/test_reporters.py`

**Interfaces:**
- Consumes: `Finding.file_path` (str, possibly absolute).
- Produces: SARIF `artifactLocation.uri` is CWD-relative POSIX for paths inside CWD; unchanged otherwise; `"stdin"` for empty.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_reporters.py` (uses the module-level `FINDING`/`SCORE` already defined there):

```python
import dataclasses


def _finding_at(path):
    return dataclasses.replace(FINDING, file_path=path)


def test_sarif_relativizes_paths_under_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = _finding_at(str(tmp_path / "src" / "app.js"))
    doc = json.loads(get_renderer("sarif")([f], SCORE, "lgpd"))
    uri = doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert uri == "src/app.js"


def test_sarif_leaves_outside_paths_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path / "." if (tmp_path / ".").exists() else tmp_path)
    f = _finding_at("/somewhere/else/app.js")
    doc = json.loads(get_renderer("sarif")([f], SCORE, "lgpd"))
    uri = doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert uri == "/somewhere/else/app.js"


def test_sarif_relative_path_stays_posix():
    doc = json.loads(get_renderer("sarif")([_finding_at("src/app.js")], SCORE, "lgpd"))
    uri = doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert uri == "src/app.js"
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_reporters.py -v`
Expected: `test_sarif_relativizes_paths_under_cwd` FAILS (uri is absolute); other two pass.

- [ ] **Step 3: Implement** — in `otto/engine/reporters/sarif.py`, add after the imports:

```python
from pathlib import Path


def _relative_uri(file_path: str) -> str:
    if not file_path:
        return "stdin"
    path = Path(file_path)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return file_path
    return path.as_posix()
```

and change the location line to:

```python
                            "artifactLocation": {"uri": _relative_uri(f.file_path)},
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_reporters.py -v` — Expected: 8 passed.
Full suite: `python3 -m pytest tests/ -q` — Expected: 162 passed.

- [ ] **Step 5: Commit**

```bash
git add otto/engine/reporters/sarif.py tests/test_reporters.py
git commit -m "fix(sarif): emit CWD-relative URIs for Code Scanning mapping"
```

---

### Task 3: Per-rule case sensitivity

**Files:**
- Modify: `otto/engine/rules.py` (Rule dataclass + `_load_file`), `otto/engine/scanner.py:105`, `skills/gdpr/patterns.json` (`national_id_eu`), `tests/fixtures/rules/gdpr__national_id_eu/clean.js`
- Test: `tests/test_rules.py`, `tests/test_scanner.py`

**Interfaces:**
- Consumes: `Rule` dataclass, `scan_content`.
- Produces: `Rule.case_sensitive: bool = False`; scanner omits `re.IGNORECASE` when true.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rules.py`:

```python
def test_case_sensitive_defaults_false():
    rule = next(r for r in load_rules("lgpd") if r.id == "cpf_exposure")
    assert rule.case_sensitive is False
```

Append to `tests/test_scanner.py`:

```python
def test_case_sensitive_rule_skips_lowercase():
    rule = Rule(id="ns", regex="\\b[A-Z]{2}\\d{6,9}[A-Z]?\\b", severity="high",
                article="X", message="m", fix="f", exclude_files=[], case_sensitive=True)
    assert scan_content('const sha = "ab1234567";\n', "src/a.js", [rule]) == []
    assert len(scan_content('const id = "AB1234567";\n', "src/a.js", [rule])) == 1


def test_case_insensitive_default_matches_lowercase():
    rule = Rule(id="ns", regex="\\b[A-Z]{2}\\d{6,9}[A-Z]?\\b", severity="high",
                article="X", message="m", fix="f", exclude_files=[])
    assert len(scan_content('const sha = "ab1234567";\n', "src/a.js", [rule])) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_rules.py tests/test_scanner.py -v`
Expected: FAIL — `Rule.__init__() got an unexpected keyword argument 'case_sensitive'`.

- [ ] **Step 3: Implement**

In `otto/engine/rules.py`, add to the `Rule` dataclass (after `validator`):

```python
    case_sensitive: bool = False
```

and in `_load_file`'s `Rule(...)` construction add:

```python
                case_sensitive=bool(raw.get("case_sensitive", False)),
```

In `otto/engine/scanner.py`, replace the `re.finditer` line:

```python
        flags = re.MULTILINE if rule.case_sensitive else re.IGNORECASE | re.MULTILINE
        try:
            matches = re.finditer(rule.regex, content, flags)
```

In `skills/gdpr/patterns.json`, add to `national_id_eu`:

```json
    "case_sensitive": true
```

Replace `tests/fixtures/rules/gdpr__national_id_eu/clean.js` content with (single line — the exact regression from the Phase 1 review):

```javascript
const sha = "ab1234567";
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/ -q` — Expected: 165 passed (harness re-validates national_id_eu with the new clean fixture).

- [ ] **Step 5: Commit**

```bash
git add otto/engine/rules.py otto/engine/scanner.py skills/gdpr/patterns.json tests/
git commit -m "feat(rules): per-rule case_sensitive flag; fix national_id_eu lowercase FP"
```

---

### Task 4: Installer cleanup + workflow version bumps

**Files:**
- Modify: `install.sh`, `.github/workflows/test.yml`

**Interfaces:**
- Consumes: current `install_for_editor` / `configure_claude_hooks` structure (read the file first).
- Produces: legacy `$skills_dir/scripts/` removed on install; legacy PostToolUse cleanup runs even with `--no-hooks`; workflow uses newest existing action majors.

- [ ] **Step 1: Split legacy-hook cleanup out of `configure_claude_hooks`**

In `install.sh`, add a new function after `install_for_editor` and BEFORE `configure_claude_hooks`:

```bash
# Remove pre-2.0 OTTO hooks from settings (runs even with --no-hooks:
# cleanup is not hook installation)
cleanup_legacy_hooks() {
  local skills_dir=$1
  local settings_file="$HOME/.claude/settings.json"
  [ -f "$settings_file" ] || return 0

  python3 -c "
import json

settings_file = '$settings_file'
skills_dir = '$skills_dir'

with open(settings_file) as f:
    settings = json.load(f)

hooks = settings.get('hooks', {})
if 'PostToolUse' in hooks:
    legacy_marker = skills_dir + '/scripts/'
    hooks['PostToolUse'] = [
        h for h in hooks['PostToolUse']
        if legacy_marker not in json.dumps(h)
    ]
    if not hooks['PostToolUse']:
        del hooks['PostToolUse']

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
"
}
```

Delete the corresponding legacy-removal block (the `if 'PostToolUse' in hooks:` section) from the Python inside `configure_claude_hooks`, leaving only the PreToolUse add/replace logic there.

- [ ] **Step 2: Wire the cleanup + remove legacy dir**

In `install_for_editor`, right after the engine copy block (after the `chmod +x` line), add:

```bash
  # Remove pre-2.0 layout leftovers
  rm -rf "$skills_dir/scripts"
```

In the Claude Code block at the bottom (`install_for_editor "Claude Code" ...`), change it to run cleanup unconditionally:

```bash
if [ -d "$HOME/.claude" ]; then
  install_for_editor "Claude Code" "$HOME/.claude/skills/otto" true
  cleanup_legacy_hooks "$HOME/.claude/skills/otto"
  INSTALLED=$((INSTALLED + 1))
fi
```

(`install_for_editor` still calls `configure_claude_hooks` only when hooks are enabled — cleanup now happens regardless.)

- [ ] **Step 3: Sandbox verification**

```bash
SB=/private/tmp/claude-501/-Users-lucianfialho-Code-metricasboss-otto/85c46012-6c78-4e35-9cf2-dbecbca34d27/scratchpad/otto-p2a-home
rm -rf "$SB" && mkdir -p "$SB/.claude/skills/otto/scripts"
touch "$SB/.claude/skills/otto/scripts/scan_privacy.py"
printf '%s' '{"hooks":{"PostToolUse":[{"matcher":"Edit|Write","hooks":[{"type":"command","command":"python3 '"$SB"'/.claude/skills/otto/scripts/scan_privacy.py"}]}]}}' > "$SB/.claude/settings.json"
HOME="$SB" bash install.sh lgpd --no-hooks
python3 - "$SB" <<'EOF'
import json, sys, pathlib
sb = pathlib.Path(sys.argv[1])
s = json.loads((sb / ".claude" / "settings.json").read_text())
assert "PostToolUse" not in s.get("hooks", {}), "legacy hook not cleaned"
assert "PreToolUse" not in s.get("hooks", {}), "--no-hooks must not add hooks"
assert not (sb / ".claude" / "skills" / "otto" / "scripts").exists(), "legacy dir survives"
print("sandbox OK")
EOF
```

Expected: `sandbox OK`. Then run once more WITHOUT `--no-hooks` and assert `PreToolUse` IS present:

```bash
HOME="$SB" bash install.sh lgpd
python3 -c "import json;s=json.load(open('$SB/.claude/settings.json'));assert s['hooks']['PreToolUse'],'missing';print('hooks OK')"
```

- [ ] **Step 4: Bump workflow action versions**

Check newest majors (`gh api repos/actions/checkout/tags --jq '.[].name' | head -5`, same for `actions/setup-python`). Update `.github/workflows/test.yml` to the newest existing majors (expected `actions/checkout@v5` and `actions/setup-python@v6`; if a check shows those don't exist, keep the known-good `@v4`/`@v5`). Run `bash -n install.sh` for syntax. Full suite: `python3 -m pytest tests/ -q` — 165 passed (installer changes don't affect it, this is the regression guard).

- [ ] **Step 5: Commit**

```bash
git add install.sh .github/workflows/test.yml
git commit -m "fix(install): purge legacy layout even with --no-hooks; bump CI action majors"
```

---

### Task 5: Comment builder (`otto/action/report.py`)

**Files:**
- Create: `otto/action/__init__.py` (empty), `otto/action/report.py`
- Test: `tests/test_action_report.py`

**Interfaces:**
- Consumes: the JSON produced by `otto scan --format json` (keys: `score`, `counts`, `findings[]` with `file_path/line/rule_id/severity/article/fine/fix`, `per_file`, `regulation`).
- Produces: `MARKER = "<!-- otto-privacy-report -->"`, `build_comment(report: dict) -> str`, and CLI `python3 -m otto.action.report <report.json>` printing the comment to stdout (exit 0; exit 2 on usage error).

- [ ] **Step 1: Write the failing tests** — `tests/test_action_report.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_action_report.py -v` — Expected: FAIL, `No module named 'otto.action'`.

- [ ] **Step 3: Implement** — create empty `otto/action/__init__.py` and `otto/action/report.py`:

```python
from __future__ import annotations

import json
import sys
from typing import List, Optional

MARKER = "<!-- otto-privacy-report -->"
_SEV_EMOJI = {"critical": "🚨", "high": "⚠️", "medium": "⚡", "low": "ℹ️"}


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def build_comment(report: dict) -> str:
    score = report["score"]
    findings = report.get("findings", [])
    counts = report.get("counts", {})
    cap_note = " (critical findings cap the score at 59)" if counts.get("critical") else ""

    lines = [MARKER, "## 🛡️ OTTO Privacy Report", "",
             f"**Privacy score: {score}/100**{cap_note}", ""]
    if not findings:
        lines.append("✅ No privacy violations in the files changed by this PR.")
    else:
        lines += [f"❌ **{len(findings)} finding(s)** in changed files:", "",
                  "| Severity | Location | Rule | Legal basis | Fine risk | Suggested fix |",
                  "|---|---|---|---|---|---|"]
        for f in findings:
            lines.append(
                f"| {_SEV_EMOJI.get(f['severity'], '')} {_cell(f['severity'])} "
                f"| `{_cell(f['file_path'])}:{f['line']}` "
                f"| {_cell(f['rule_id'])} "
                f"| {_cell(f['article'])} "
                f"| {_cell(f['fine'])} "
                f"| {_cell(f['fix'])} |"
            )
    lines += ["", "---",
              "_Deterministic score by [OTTO](https://github.com/metricasboss/otto)"
              " — same diff, same score. Not legal advice._"]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else argv
    if len(argv) != 1:
        print("usage: python3 -m otto.action.report <report.json>", file=sys.stderr)
        return 2
    with open(argv[0], encoding="utf-8") as fh:
        report = json.load(fh)
    print(build_comment(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_action_report.py -v` — Expected: 6 passed.
Full suite: `python3 -m pytest tests/ -q` — Expected: 171 passed.

- [ ] **Step 5: Commit**

```bash
git add otto/action/ tests/test_action_report.py
git commit -m "feat(action): markdown comment builder for PR privacy report"
```

---

### Task 6: Composite `action.yml`

**Files:**
- Create: `action.yml` (repo root)

**Interfaces:**
- Consumes: `python3 -m otto scan <files> --regulation R --fail-under N --format json|sarif|text` (exit 1 below gate, 2 on missing path), `python3 -m otto.action.report <json>` (Task 5).
- Produces: `uses: metricasboss/otto@<ref>` with inputs `fail-under`/`regulation`/`comment`/`sarif`.

- [ ] **Step 1: Verify third-party action majors**

Per Global Constraints, check newest majors for `actions/setup-python`, `actions/github-script`, `github/codeql-action`. Use the newest that exists; the YAML below writes the known-good majors — update them per your check.

- [ ] **Step 2: Create `action.yml`**

```yaml
name: "OTTO Privacy Review"
description: "LGPD/GDPR privacy review for AI-era codebases: deterministic 0-100 score, article citations and suggested fixes on every PR"
branding:
  icon: shield
  color: green

inputs:
  fail-under:
    description: "Fail the check if the privacy score is below this value (0 disables the gate)"
    default: "60"
  regulation:
    description: "lgpd, gdpr or both"
    default: "both"
  comment:
    description: "Post/update the sticky PR comment"
    default: "true"
  sarif:
    description: "Upload SARIF to GitHub Code Scanning"
    default: "true"

runs:
  using: composite
  steps:
    - name: Guard event type
      shell: bash
      run: |
        if [ "$GITHUB_EVENT_NAME" != "pull_request" ]; then
          echo "::error::OTTO action supports pull_request events only (got $GITHUB_EVENT_NAME)"
          exit 1
        fi

    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: Detect changed files
      id: files
      shell: bash
      working-directory: ${{ github.workspace }}
      run: |
        git fetch --no-tags origin "$GITHUB_BASE_REF"
        git diff --name-only --diff-filter=d "origin/$GITHUB_BASE_REF...HEAD" > "$RUNNER_TEMP/otto-files.txt"
        : > "$RUNNER_TEMP/otto-existing.txt"
        while IFS= read -r f; do
          [ -f "$f" ] && printf '%s\n' "$f" >> "$RUNNER_TEMP/otto-existing.txt"
        done < "$RUNNER_TEMP/otto-files.txt"
        count=$(wc -l < "$RUNNER_TEMP/otto-existing.txt" | tr -d ' ')
        echo "count=$count" >> "$GITHUB_OUTPUT"
        echo "OTTO: $count changed file(s) to scan"

    - name: Scan changed files
      if: steps.files.outputs.count != '0'
      shell: bash
      working-directory: ${{ github.workspace }}
      env:
        PYTHONPATH: ${{ github.action_path }}
      run: |
        xargs -a "$RUNNER_TEMP/otto-existing.txt" \
          python3 -m otto scan --regulation "${{ inputs.regulation }}" --fail-under 0 --format json \
          > "$RUNNER_TEMP/otto-report.json"
        xargs -a "$RUNNER_TEMP/otto-existing.txt" \
          python3 -m otto scan --regulation "${{ inputs.regulation }}" --fail-under 0 --format sarif \
          > "$RUNNER_TEMP/otto.sarif"

    - name: Build comment body
      if: inputs.comment == 'true'
      shell: bash
      working-directory: ${{ github.workspace }}
      env:
        PYTHONPATH: ${{ github.action_path }}
      run: |
        if [ "${{ steps.files.outputs.count }}" = "0" ]; then
          printf '%s' '{"regulation":"${{ inputs.regulation }}","score":100,"per_file":{},"counts":{"critical":0,"high":0,"medium":0,"low":0},"findings":[]}' \
            > "$RUNNER_TEMP/otto-report.json"
        fi
        python3 -m otto.action.report "$RUNNER_TEMP/otto-report.json" > "$RUNNER_TEMP/otto-comment.md"

    - name: Upsert sticky comment
      if: inputs.comment == 'true'
      uses: actions/github-script@v7
      continue-on-error: true
      env:
        COMMENT_PATH: ${{ runner.temp }}/otto-comment.md
      with:
        script: |
          const fs = require('fs');
          const body = fs.readFileSync(process.env.COMMENT_PATH, 'utf8');
          const marker = '<!-- otto-privacy-report -->';
          const {data: comments} = await github.rest.issues.listComments({
            owner: context.repo.owner,
            repo: context.repo.repo,
            issue_number: context.issue.number,
            per_page: 100,
          });
          const existing = comments.find(c => c.body && c.body.includes(marker));
          if (existing) {
            await github.rest.issues.updateComment({
              owner: context.repo.owner, repo: context.repo.repo,
              comment_id: existing.id, body,
            });
          } else {
            await github.rest.issues.createComment({
              owner: context.repo.owner, repo: context.repo.repo,
              issue_number: context.issue.number, body,
            });
          }

    - name: Upload SARIF
      if: inputs.sarif == 'true' && steps.files.outputs.count != '0'
      uses: github/codeql-action/upload-sarif@v3
      continue-on-error: true
      with:
        sarif_file: ${{ runner.temp }}/otto.sarif

    - name: Privacy gate
      if: steps.files.outputs.count != '0'
      shell: bash
      working-directory: ${{ github.workspace }}
      env:
        PYTHONPATH: ${{ github.action_path }}
      run: |
        xargs -a "$RUNNER_TEMP/otto-existing.txt" \
          python3 -m otto scan --regulation "${{ inputs.regulation }}" \
          --fail-under "${{ inputs.fail-under }}" --format text
```

- [ ] **Step 3: Local sanity of the step pipeline**

Simulate the scan→comment pipeline locally (this is the only part testable off-runner):

```bash
TMP=/private/tmp/claude-501/-Users-lucianfialho-Code-metricasboss-otto/85c46012-6c78-4e35-9cf2-dbecbca34d27/scratchpad
python3 -m otto scan examples/unsafe_code.js --fail-under 0 --format json > "$TMP/otto-report.json"
python3 -m otto.action.report "$TMP/otto-report.json" | head -12
```

Expected: markdown starting with the marker, `## 🛡️ OTTO Privacy Report`, a `0/100` score headline with the cap note, and table rows citing LGPD articles.

- [ ] **Step 4: Commit**

```bash
git add action.yml
git commit -m "feat(action): composite GitHub Action with sticky score comment, SARIF and gate"
```

---

### Task 7: Dogfooding workflow + README + live PR verification

**Files:**
- Create: `.github/workflows/otto.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: `action.yml` (Task 6) via `uses: ./`.
- Produces: the Phase 2a PR itself demonstrates the action live.

- [ ] **Step 1: Create `.github/workflows/otto.yml`**

```yaml
name: privacy

on: pull_request

permissions:
  contents: read
  pull-requests: write
  security-events: write

jobs:
  otto:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: ./
        with:
          fail-under: "60"
```

(Match the checkout major to whatever Task 4 pinned in `test.yml`.)

- [ ] **Step 2: Add the README section**

Insert after the "Automatic Protection (Claude Code Only)" section:

```markdown
### GitHub Action (PR privacy review)

Add OTTO to any repository's CI — every pull request gets a deterministic
0-100 privacy score, findings with the violated LGPD/GDPR article and fine
exposure, inline annotations (via Code Scanning), and a failing check when
the score drops below your gate.

```yaml
# .github/workflows/otto.yml
name: privacy
on: pull_request
permissions:
  contents: read
  pull-requests: write      # sticky score comment
  security-events: write    # SARIF annotations (optional)
jobs:
  otto:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0    # required: OTTO diffs against the PR base
      - uses: metricasboss/otto@main
        with:
          fail-under: 60    # fail the check below this score (0 = report-only)
          regulation: both  # lgpd | gdpr | both
```

| input | default | description |
|---|---|---|
| `fail-under` | `60` | Fail the check if the PR score is below this value; `0` disables the gate |
| `regulation` | `both` | `lgpd`, `gdpr` or `both` |
| `comment` | `true` | Post/update the sticky score comment |
| `sarif` | `true` | Upload SARIF for inline annotations |

Only the files changed by the PR are scanned — your PR is scored on what it
introduces, not the repo's pre-existing debt. Any critical finding caps the
score at 59, so a hardcoded CPF can never pass a default gate.

**Limitations:** fork PRs run with a read-only token — the comment and SARIF
upload are skipped with a warning, but the gate still enforces. SARIF
annotations on private repos require GitHub Advanced Security.
```

- [ ] **Step 3: Full suite + commit**

Run: `python3 -m pytest tests/ -q` — Expected: 171 passed.

```bash
git add .github/workflows/otto.yml README.md
git commit -m "feat(action): dogfooding workflow + README GitHub Action docs"
```

- [ ] **Step 4: Live verification on the Phase 2a PR**

This task runs at branch-finish time (execution option 2 — push and PR — is REQUIRED for this phase; the dogfood run needs a real PR):

1. Push the feature branch, open the PR against `main`.
2. Add a probe commit: file `probe_privacy.js` at repo root containing exactly `const cpf = "529.982.247-25";` — push.
3. Wait for the `privacy` check: expect **failure**, a sticky comment with score ≤59 citing `LGPD Art. 46`, and (Code Scanning enabled) an inline annotation. Capture evidence: `gh pr checks`, `gh pr view --comments`.
4. Revert the probe commit (`git revert --no-edit <sha>`) — push. Expect the check to turn **green** and the SAME comment (no duplicate) to update to 100/100. Verify with `gh pr view --comments` (one OTTO comment only).
5. If any expectation fails, fix the action and repeat. The PR merges only after this passes — it IS the acceptance test from the spec.

---

## Self-Review Notes (applied)

- Spec coverage: hardening 1-4 → Tasks 1-4; comment builder → Task 5; action.yml (inputs/steps/edge cases) → Task 6; dogfood + README + live acceptance → Task 7. Fork-PR handling = `continue-on-error` on comment/SARIF steps (Task 6) + README limitation note (Task 7). Arg-length: file list flows through `xargs -a`, never inline args.
- Version pins are written as known-good majors with a mandated newest-major check (Global Constraints) — not placeholders.
- Type consistency: `build_comment(report: dict) -> str` + `MARKER` used identically in Tasks 5-6; `steps.files.outputs.count` string-compared consistently; report JSON keys match the Phase 1 `json_out` reporter (`score/counts/findings/per_file/regulation`).
- Test count progression: 157 → 159 (T1) → 162 (T2) → 165 (T3) → 171 (T5). Task 4 adds no pytest tests (sandbox verification instead); Tasks 6-7 are validated by the live PR.
