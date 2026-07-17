# OTTO Privacy Review Engine — Design (Phase 1: Core Engine)

**Date:** 2026-07-17
**Status:** Approved for planning
**Approach:** A — own deterministic engine, Rams-style ("AI gives you an opinion, OTTO keeps score")

## Thesis

Evolve OTTO from a regex hook scanner into a privacy review engine for AI-assisted coding, modeled on what Rams.ai did for design quality: deterministic 0-100 privacy score, findings that cite the violated LGPD/GDPR article with fine exposure and a suggested fix, delivered across three surfaces (skill/hook, GitHub Action, MCP server).

**Strategy:** OSS-first. No hosted infra, no billing in this phase. The free path is 100% local with zero network calls. A hosted SaaS may come later once demand is validated.

## Phasing

1. **Phase 1 (this spec):** Core engine — score, structured output, rule quality, hook fix.
2. **Phase 2 (future spec):** GitHub Action — scan PR diffs, inline comments (article + fine + fix), score as a check. Optional LLM contextual pass using the user's API key.
3. **Phase 3 (future spec):** MCP server exposing the scanner to any agent (Cursor, Codex, OpenCode, Antigravity).

Phases 2 and 3 consume the Phase 1 engine through its CLI. Nothing in Phase 1 may assume a specific surface.

## Phase 1 Scope

### 1. Architecture

Refactor the monolithic `scripts/scan_privacy.py` into a Python package. Python stays: it is the current language, and the engine must run with **stdlib only** (no pip install) so the hook and any CI can run it cold.

```
otto/
├── engine/
│   ├── rules.py        # load + validate patterns.json (new schema)
│   ├── scanner.py      # apply rules to files/paths
│   ├── scorer.py       # deterministic 0-100 score
│   └── reporters/      # text (current human format), json, sarif
├── cli.py              # `otto scan <path>` --format --regulation --fail-under
└── hook.py             # Claude Code hook entrypoint (stdin JSON)
```

- The CLI is the single interface. Hook, Action (Phase 2), and MCP (Phase 3) all shell out to the same engine.
- `--format sarif` gives GitHub Code Scanning upload and PR annotations with no bespoke integration code.
- `--regulation lgpd|gdpr|both` preserved from current scanner.

### 2. Scoring model

- Score starts at 100. Deductions by severity: critical −25, high −10, medium −4, low −1. Floor 0.
- **Any critical finding caps the score at 59.** A scan never "passes" with exposed CPF/sensitive data.
- Deterministic: same input, same score, always. The score is the engine's, never an LLM's.
- Per-file score and aggregate scan score.
- `--fail-under N` (default 60): exit code non-zero below the threshold. This is the gate the hook and CI use.

### 3. Rules format and false-positive reduction

`patterns.json` schema gains new optional fields (backward compatible; existing fields remain valid):

```json
{
  "id": "cpf_exposure",
  "regex": "...",
  "severity": "critical",
  "category": "sensitive_data",
  "article": "LGPD Art. 46",
  "message": "...",
  "fix": "...",
  "fine": "...",
  "files": ["**/*.js", "**/*.py", "**/*.ts"],
  "exclude_files": ["**/*.test.*", "**/fixtures/**", "**/*.md"],
  "negative_context": ["mock", "example", "faker", "dummy"]
}
```

False-positive attack (the current engine's biggest weakness):

- **`files` / `exclude_files` globs:** PII in test files, fixtures, or markdown is not a production violation. Today the scanner flags everything.
- **`negative_context`:** if the matched line contains one of these terms, the finding is downgraded to `low` with a "possible test data" note — transparent downgrade, never silent suppression.
- **CPF check-digit validation:** regex finds the shape; the engine validates the check digits. `111.111.111-11` and made-up CPFs stop being critical.
- **Inline suppression:** `otto-ignore: <rule-id> -- <reason>` comment on the line. Reason is mandatory — suppressions become an audit trail.

**Rule set target:** clean up the current 28 rules (loose regexes tightened) + ~12 new high-value rules (webhooks sending PII, sensitive data in URLs/query strings, retention without TTL, geolocation without consent). ≈40 rules, every one with test fixtures.

### 4. Hook fix

The installed hook is currently `PostToolUse` — it runs **after** the file is written, contradicting the README's "blocks before saved" promise.

- Hook becomes **`PreToolUse`** (matcher `Edit|Write`): scans the incoming content before it lands.
- Critical finding → `permissionDecision: "deny"` with the formatted reason (article + fix), so the agent self-corrects.
- Non-critical findings do not block; they are returned as additional context in the hook response.
- `install.sh` updated accordingly; existing PostToolUse entries migrated/removed on reinstall.

### 5. Testing

- Pytest suite. Every rule ships with at least one fixture that MUST flag and one that MUST NOT flag (the `examples/` unsafe/safe pair becomes part of the suite).
- Score regression tests: fixtures with pinned expected scores.
- Repo CI runs the suite — OTTO self-tests.

## Out of scope (Phase 1)

- GitHub Action / PR comments (Phase 2)
- LLM contextual analysis (Phase 2, optional layer, user's API key)
- MCP server (Phase 3)
- Hosted SaaS, billing, telemetry of any kind
- New regulations (CCPA, PIPEDA) — schema should not preclude them, but no rules are written

## Success criteria

- `otto scan examples/unsafe_code.js` returns score ≤ 59 with critical findings citing articles; `examples/safe_code.js` returns 100.
- `otto scan --format sarif` output is accepted by GitHub Code Scanning.
- Hook denies an Edit that introduces a hardcoded valid CPF, and the denial message contains the article and suggested fix.
- Full test suite green in CI; every rule has both fixtures.
- Zero third-party Python dependencies.
