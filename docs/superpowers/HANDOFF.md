# OTTO — Handoff

**Last updated:** 2026-07-20
**Repo:** `metricasboss/otto` · **Branch:** `main` (clean, synced with origin)

## What OTTO is

Privacy compliance engine for AI-assisted coding. Scans code for LGPD/GDPR violations, produces a **deterministic 0-100 score** (same diff → same score, always), and surfaces findings with the violated article, fine exposure, and a suggested fix. Modeled on the [Rams.ai](https://www.rams.ai/) thesis for design-quality review, applied to privacy: "AI gives you an opinion, OTTO keeps score."

## Where things stand

**Phase 1 (merged, `b334fee`) — core engine:**
- `otto/` package: `engine/{rules,scanner,scorer,validators,reporters/}`, `cli.py`, `hook.py` — stdlib-only, zero third-party deps, Python ≥3.9.
- 44 rules (LGPD + GDPR) in `skills/{lgpd,gdpr}/patterns.json`, each with a mandatory `flag.js`/`clean.js` fixture pair enforced by `tests/test_rule_fixtures.py`.
- Score model: 100 − (critical×25 + high×10 + medium×4 + low×1), floor 0, **any critical caps the score at 59**.
- Claude Code `PreToolUse` hook: denies edits with a critical finding before they're saved (the README's "blocks before saved" promise, made real).
- CLI: `python3 -m otto scan <path> --format text|json|sarif --regulation lgpd|gdpr|both --fail-under N`.

**Phase 2a (merged, PR #1 `7224a6d` + PR #2 `e4f1711`) — GitHub Action:**
- `action.yml`: composite action at repo root. `uses: metricasboss/otto@main` scans only PR-changed files, posts a sticky score comment, uploads SARIF (Code Scanning inline annotations), fails the check below `fail-under` (default 60).
- `otto/action/report.py`: pure, tested markdown-comment builder (score headline, findings table, 50-row cap, cell escaping).
- Hardening closed from the Phase 1 final review: MultiEdit hook coverage, SARIF CWD-relative URIs, per-rule `case_sensitive` flag, installer legacy-layout purge, shallow-clone-safe git diff, NUL-safe file lists (`--paths-from`, no `xargs` batching), self-scan exclusion for `skills/*/patterns.json` (OTTO no longer flags its own rule definitions).
- **Dogfooding is live**: `.github/workflows/otto.yml` runs the action on every PR to this repo. Verified end-to-end on PR #1: a probe commit with a valid CPF failed the check with a 59/100 comment citing LGPD Art. 46; reverting it updated the *same* comment to 100/100 and turned the check green.
- Optional custom bot branding wired (PR #2): `github-token` input lets a consumer pass a GitHub App installation token so the comment posts as their own bot instead of `github-actions[bot]`.

Suite: **180 tests, all green.** CI matrix: Python 3.9 + 3.12.

## Immediate next step (waiting on the user)

**Otto's avatar isn't showing yet.** To get the sticky comment posted as `otto[bot]` with Otto's face instead of the generic GitHub Actions icon, the user needs to do a ~5-minute manual GitHub App setup (documented in README.md under "Optional: comment as your own bot"):

1. Org Settings → Developer settings → New GitHub App ("OTTO Privacy Guardian"), no webhook, permission `Pull requests: Read & write`, upload Otto's image as the App avatar.
2. Generate a private key, install the App on `metricasboss/otto`.
3. Add repo secrets `OTTO_APP_ID` and `OTTO_APP_PRIVATE_KEY`.

Once those secrets exist, `.github/workflows/otto.yml` (already updated) mints the App token automatically and passes it to the action — no further code changes needed. This is the one open loop from this session.

## Backlog / next phases (not started)

- **Release tag `v2`** — pin a stable major for Marketplace listing and so `uses: metricasboss/otto@v2` doesn't ride `main`.
- **Phase 2b — optional LLM contextual pass**: user's own API key, filters scanner candidates for semantic false positives (e.g. "is there a consent check elsewhere in this flow?") without ever computing the score — the score stays the deterministic engine's job. Needs its own spec/brainstorm; deliberately deferred out of Phase 2a scope.
- **Phase 3 — MCP server**: exposes the scanner to any agent (Cursor, Codex, OpenCode, Antigravity) that isn't Claude Code, replacing today's "manual `/otto` only" limitation for those editors.
- **Minor items surfaced in reviews but not blocking** (see `docs/superpowers/plans/*` self-review notes and the SDD ledgers in `.superpowers/sdd/progress.md` inside the now-removed worktrees — captured in PR review threads if not already fixed): xargs GNU-only assumption resolved via `--paths-from`; comment table >50 rows truncated; a few Minor-severity nitpicks (dead imports, cosmetic report inaccuracies) were accepted as-is per the review calibration (not worth the churn).

## How this was built (process notes for continuing the pattern)

Both phases followed: **brainstorming → spec → writing-plans → subagent-driven-development (worktree-isolated) → task-by-task review → final whole-branch review → live PR acceptance test → merge.**

- Specs: `docs/superpowers/specs/2026-07-17-otto-privacy-review-engine-design.md` (Phase 1), `docs/superpowers/specs/2026-07-18-otto-github-action-design.md` (Phase 2a).
- Plans: `docs/superpowers/plans/2026-07-17-otto-engine-phase1.md`, `docs/superpowers/plans/2026-07-19-otto-phase2a-action.md`.
- Each phase's final whole-branch review found real cross-task issues neither task-level review could see alone (Phase 1: three critical-severity rules were too broad and would hard-block innocent edits once the hook went `PreToolUse`; Phase 2a: OTTO's own rule-definition JSON tripped OTTO's own keyword rules, which would have made the dogfood acceptance test structurally unpassable). Both were caught and fixed before merge — the whole-branch review step earned its keep both times.
- If continuing with subagents: read the two plan files' "Self-Review Notes" sections for what's already covered, and prefer opening a fresh spec via `superpowers:brainstorming` for Phase 2b/3 rather than bolting them onto the existing plans — they're genuinely separate subsystems (LLM pass has its own design uncertainty; MCP is a different protocol surface entirely).

## Key files to know

| Path | What it is |
|---|---|
| `otto/engine/{rules,scanner,scorer,validators}.py` | The deterministic core |
| `otto/engine/reporters/{text,json_out,sarif}.py` | Output formats |
| `otto/hook.py` + `scripts/run_hook.py` | Claude Code PreToolUse integration |
| `otto/action/report.py` | PR comment markdown builder |
| `action.yml` | The composite GitHub Action |
| `.github/workflows/otto.yml` | Dogfood workflow (this repo uses its own action) |
| `.github/workflows/test.yml` | CI: pytest matrix + self-scan + canary |
| `skills/{lgpd,gdpr}/patterns.json` | The 44 rules |
| `tests/fixtures/rules/` | Mandatory flag/clean pair per rule |
| `install.sh` | Multi-editor installer (Claude Code hooks, Cursor/OpenCode/Codex/Antigravity manual-only) |
