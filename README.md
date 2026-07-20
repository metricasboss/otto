# OTTO - Privacy Guardian

**Automated privacy compliance for AI-assisted coding**

> By [Métricas Boss](https://github.com/metricasboss) - A comunidade brasileira de Analytics & Privacy

---

## The Problem

AI assistants like Claude, Copilot, and ChatGPT are transforming how we code. But they don't know LGPD or GDPR.

**Common scenario:**
1. Developer asks Claude: *"Add user tracking to this page"*
2. Claude generates code that collects CPF, email, phone
3. Developer commits without reviewing
4. **Violation goes to production**
5. **Fine: up to R$ 50 million**

**OTTO solves this.**

It sits between the AI and your commits, catching privacy violations before they become fines.

## Overview

OTTO automatically validates AI-generated code against LGPD and GDPR, blocking violations before they reach production.

**Why you need this:**
- AI assistants generate code fast, but don't validate compliance
- Developers trust AI output without reviewing privacy implications
- Manual code review is slow and misses subtle violations
- LGPD/GDPR fines start at R$ 50M / €20M per violation

**Supported Regulations:**
- 🇧🇷 LGPD (Lei 13.709/18) - Brazil
- 🇪🇺 GDPR (EU 2016/679) - Europe

---

## Who This Is For

**Developers using AI assistants:**
- Claude Code, GitHub Copilot, ChatGPT, Cursor, etc.
- Writing code fast without privacy expertise
- Need compliance without slowing down

**Teams shipping to Brazil/Europe:**
- Startups moving fast
- Companies handling user data
- Anyone who can't afford a R$ 50M mistake

---

## Quick Install

```bash
git clone https://github.com/metricasboss/otto.git
cd otto
./install.sh
```

**Default:** Installs LGPD + GDPR for all detected editors.

**Options:**
```bash
./install.sh lgpd        # Brazil only
./install.sh gdpr        # Europe only
./install.sh --no-hooks  # Skip automatic protection
```

**Supported editors:**
- Claude Code (with automatic hooks)
- Cursor (manual `/otto` only)
- OpenCode (manual `/otto` only)
- Codex (manual `/otto` only)
- Antigravity (manual `/otto` only)

**Note:** Automatic protection (hooks) only works on Claude Code. Other editors require manual invocation with `/otto`.

---

## What OTTO Detects

### LGPD (Brazil)
- CPF/RG/CNPJ hardcoded in code
- Personal data in logs (console.log, logger)
- Tracking/analytics without consent verification
- SQL queries violating data minimization (SELECT *)
- Passwords in plaintext
- API keys and secrets exposed
- Cookies set without consent
- Data sharing with third parties without authorization
- SQL injection vulnerabilities

### GDPR (Europe)
- SSN/National ID numbers exposed
- Personal data in logs
- Tracking without consent
- Queries violating data minimization
- Unencrypted sensitive data
- Health/biometric data (special categories)
- localStorage misuse for sensitive data
- External data transfers without legal basis

---

## How It Works

### Multi-Editor Support

OTTO works with multiple AI coding editors:

**Claude Code (Full Support):**
- Automatic invocation when Claude detects personal data
- Real-time feedback during coding
- **Automatic hooks**: Validates before edits/commits
- Fix suggestions with compliant code

**Other Editors (Cursor, OpenCode, Codex, Antigravity):**
- Manual invocation only: `/otto` or `/otto scan <path>`
- Same violation detection patterns
- No automatic hooks (editor limitation)
- Useful for manual code review

### Automatic Protection (Claude Code Only)

When hooks are enabled on Claude Code:

- **Before edits**: Blocks privacy violations before they're saved
- **Before commits**: Ensures clean commits
- **CI/CD ready**: Can integrate into your build pipeline
- Critical violations deny the edit via a PreToolUse hook; the agent receives the article and suggested fix and can self-correct.

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
      - uses: actions/checkout@v7
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
upload may fail without failing the job (the steps are fenced with
continue-on-error), but the gate still enforces. SARIF annotations on
private repos require GitHub Advanced Security.

---

## Usage

### Automatic Mode (Recommended)

Once installed with hooks enabled, OTTO works automatically:

```javascript
// You write code with privacy issues
console.log('User:', user); // Exposes PII

// OTTO blocks and suggests fix:
// Use: console.log('User ID:', user.id)
```

### Manual Mode

Invoke OTTO directly in Claude Code:

```bash
# Analyze current context
/otto

# Scan specific directory
/otto scan src/

# Scan before commit
/otto scan .
```

### Standalone Scanner

Run the scanner directly on files:

```bash
python3 -m otto scan src/ --format text          # from a repo checkout
python3 -m otto scan src/ --format sarif > otto.sarif
```

---

## Example Output

```
OTTO - LGPD Privacy Analysis

VIOLATIONS FOUND: 3

File: src/auth/login.js

1. CPF Exposure
   Line: 15
   Severity: CRITICAL

   Issue:
   CPF brasileiro exposto no código

   Legal basis violated:
   LGPD Art. 46 (Dados Sensíveis)

   Fine risk:
   Até R$ 50 milhões

   SUGGESTED FIX:
   Remove hardcoded CPF. Retrieve from encrypted database
   or use environment variable for tests.

[... more violations ...]

SUMMARY:
   • 3 critical violations
   • Risk: up to R$ 150 million

NEXT STEPS:
1. Fix critical violations immediately
2. Implement consent verification system
3. Add privacy tests to CI/CD
4. Document legal basis for data processing

OTTO protected your users today.
```

---

## Fines You Can Avoid

### LGPD (Brazil)
- Up to R$ 50 million per violation (Art. 52)
- Public disclosure of violations
- Data blocking/deletion orders

### GDPR (Europe)
- Up to €20M or 4% of annual global turnover (whichever is higher)
- Applies per violation
- Cumulative fines for multiple violations

**Example:** 3 critical violations = potential R$ 150M (LGPD) or €60M (GDPR)

---

## Real-World Example: AI-Generated Code

### What AI Generates (Unsafe)

```javascript
// Developer prompt: "Add analytics tracking for user login"
// AI generates:

const user = await getUser(userId);
console.log('User logged in:', user); // ❌ Logs PII
analytics.track('login', {
  email: user.email,        // ❌ No consent check
  cpf: user.cpf,           // ❌ Sensitive data
  location: user.address   // ❌ Unnecessary data
});
```

**What happens:**
- ❌ AI doesn't know LGPD requires consent
- ❌ AI doesn't know CPF is sensitive data
- ❌ AI doesn't know about data minimization
- 💰 **Fine: R$ 150 million** (3 violations)

### What OTTO Catches

```
OTTO - LGPD Analysis

❌ 3 VIOLATIONS FOUND

1. Personal data in logs (Line 3)
   LGPD Art. 46 - Fine: R$ 50M
   Fix: console.log('User ID:', user.id)

2. Tracking without consent (Line 4)
   LGPD Art. 7º - Fine: R$ 50M
   Fix: if (user.hasConsent('analytics')) { ... }

3. Unnecessary data collection (Line 6)
   LGPD Art. 6º III - Fine: R$ 50M
   Fix: Remove 'location' field
```

### What You Commit (Safe)

```javascript
// OTTO auto-corrected:

const user = await getUser(userId);
console.log('User ID:', user.id); // ✅ No PII

if (user.hasConsent('analytics')) { // ✅ Consent check
  analytics.track('login', {
    userId: hash(user.id)  // ✅ Anonymized, no sensitive data
  });
}
```

**Result:** ✅ LGPD compliant, zero fines

---

## Project Structure

```
otto/
├── install.sh                    # Interactive installer
├── README.md                     # This file
├── QUICKSTART.md                 # 2-minute setup guide
├── LICENSE                       # MIT License
│
├── otto/                         # Python engine package
│   ├── cli.py                    # `python3 -m otto scan ...`
│   ├── hook.py                   # PreToolUse hook entry point
│   └── engine/
│       ├── rules.py              # Rule loading + Rule dataclass
│       ├── scanner.py            # Scan orchestration + false-positive layers
│       ├── scorer.py             # Compliance scoring
│       ├── validators.py         # CPF/CNPJ check-digit validators
│       └── reporters/            # text / json / sarif output
│
├── scripts/
│   └── run_hook.py               # Installed launcher for otto/hook.py
│
├── skills/
│   ├── lgpd/                     # Brazilian regulation
│   │   ├── SKILL.md              # LGPD skill definition
│   │   └── patterns.json         # LGPD violation patterns
│   │
│   └── gdpr/                     # European regulation
│       ├── SKILL.md              # GDPR skill definition
│       └── patterns.json         # GDPR violation patterns
│
├── tests/                        # pytest suite
│
└── examples/
    ├── unsafe_code.js            # Code with violations
    └── safe_code.js              # Compliant code
```

---

## Privacy & Security

OTTO itself respects your privacy:

- **No data collection**: Runs entirely locally
- **No network calls**: Patterns are local JSON files
- **Open source**: Audit the code yourself
- **No telemetry**: Your code never leaves your machine

---

## Contributing

Contributions are welcome! Especially:

- New violation patterns
- Support for other regulations (CCPA, PIPEDA, etc.)
- Bug fixes and improvements
- Documentation updates
- Test cases

### How to Contribute

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-pattern`
3. Add your changes
4. Test thoroughly
5. Submit a pull request

### Adding New Patterns

Edit `skills/lgpd/patterns.json` or `skills/gdpr/patterns.json`:

```json
{
  "pattern_name": {
    "regex": "your-regex-here",
    "severity": "critical|high|medium|low",
    "article": "Regulation Article",
    "message": "Description of the violation",
    "fix": "How to fix it",
    "fine": "Penalty amount"
  }
}
```

---

## Documentation

- [README.md](README.md) - Complete guide (this file)
- [QUICKSTART.md](QUICKSTART.md) - 2-minute setup
- [DEPLOY.md](DEPLOY.md) - Deployment instructions
- [demo/](demo/) - Demo script and GIF recording instructions

---

## Resources

### LGPD (Brazil)
- [Full LGPD text (Portuguese)](http://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [ANPD - National Data Protection Authority](https://www.gov.br/anpd/)

### GDPR (Europe)
- [Full GDPR text](https://gdpr-info.eu/)
- [European Data Protection Board](https://edpb.europa.eu/)

### Privacy Best Practices
- [OWASP Privacy Guide](https://owasp.org/www-project-top-ten/)
- [Privacy by Design Principles](https://www.ipc.on.ca/privacy-by-design/)

---

## Troubleshooting

### OTTO not showing up

**Claude Code:**
1. Check installation: `ls -la ~/.claude/skills/otto/`
2. Restart Claude Code
3. Run `/help` to see if `/otto` is listed

**Cursor:**
1. Check installation: `ls -la ~/.cursor/skills/otto/`
2. Restart Cursor
3. Type `/otto` to invoke manually

**Other editors:** Check respective skill directories

### Hooks not working (Claude Code only)

1. Check settings: `cat ~/.claude/settings.json`
2. Verify Python is installed: `python3 --version`
3. Make scanner executable: `chmod +x ~/.claude/skills/otto/engine/run_hook.py`
4. **Note:** Hooks only work on Claude Code, not other editors

### False positives

OTTO uses regex patterns and may flag legitimate code. You can:

1. Add context in comments explaining why code is safe
2. Adjust patterns in `~/.claude/skills/otto/engine/skills/<regulation>/patterns.json`
3. Disable specific patterns by removing them from JSON

---

## Support

- Issues: [GitHub Issues](https://github.com/metricasboss/otto/issues)
- Discussions: [GitHub Discussions](https://github.com/metricasboss/otto/discussions)
- Community: [Métricas Boss](https://github.com/metricasboss)

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

## Acknowledgments

Built by the [Métricas Boss](https://github.com/metricasboss) community for developers who value privacy compliance.
