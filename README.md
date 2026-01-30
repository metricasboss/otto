# OTTO - Privacy Guardian

**Automated privacy compliance for AI-assisted coding**

> By [Métricas Boss](https://github.com/metricasboss) - A comunidade brasileira de Analytics & Privacy

---

## Demo

> **Recording demo GIF...** See `demo/` folder for instructions to record.
>
> Quick preview: Run `./demo/demo_script.sh` to see OTTO in action

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

The installer will:
1. Ask which regulation you want (LGPD, GDPR, or both)
2. Install OTTO as a Claude Code skill
3. Optionally configure automatic protection via hooks
4. Set everything up in `~/.claude/skills/otto/`

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

### As a Claude Code Skill

OTTO integrates seamlessly with Claude Code:

1. **Automatic invocation**: Claude uses OTTO when it detects code accessing personal data
2. **Real-time feedback**: Get immediate warnings about privacy violations
3. **Fix suggestions**: Receive corrected code that complies with regulations
4. **Educational**: Learn privacy principles while coding

### As a Hook (Optional)

When hooks are enabled, OTTO validates code automatically:

- **Before edits**: Blocks privacy violations before they're saved
- **Before commits**: Ensures clean commits
- **CI/CD ready**: Can integrate into your build pipeline

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
python3 ~/.claude/skills/otto/scripts/scan_privacy.py myfile.js
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
├── skills/
│   ├── lgpd/                     # Brazilian regulation
│   │   ├── SKILL.md              # LGPD skill definition
│   │   └── patterns.json         # LGPD violation patterns
│   │
│   └── gdpr/                     # European regulation
│       ├── SKILL.md              # GDPR skill definition
│       └── patterns.json         # GDPR violation patterns
│
├── scripts/
│   └── scan_privacy.py           # Python scanner engine
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

### OTTO not showing up in Claude Code

1. Check installation: `ls -la ~/.claude/skills/otto/`
2. Restart Claude Code
3. Run `/help` to see if `/otto` is listed

### Hooks not working

1. Check settings: `cat ~/.claude/settings.json`
2. Verify Python is installed: `python3 --version`
3. Make scanner executable: `chmod +x ~/.claude/skills/otto/scripts/scan_privacy.py`

### False positives

OTTO uses regex patterns and may flag legitimate code. You can:

1. Add context in comments explaining why code is safe
2. Adjust patterns in `~/.claude/skills/otto/scripts/patterns.json`
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

Named in honor of **Otto**, because protecting data should be as natural as protecting family.

Built by the [Métricas Boss](https://github.com/metricasboss) community for developers who value privacy compliance.

---

**OTTO** - Guarding your code like family

*Making privacy compliance automatic, one line of code at a time.*
