# 🛡️ OTTO.ai - Privacy Guardian

**Automated privacy compliance for Claude Code**

Named in honor of Otto - Protecting personal data like you protect family.

---

## 🌍 Multi-Regulation Support

- 🇧🇷 **LGPD** (Lei 13.709/18) - Brazil
- 🇪🇺 **GDPR** (EU 2016/679) - Europe

OTTO.ai automatically detects privacy violations in your code before they reach production, helping you avoid fines up to **R$ 50 million (LGPD)** or **€20M / 4% turnover (GDPR)**.

---

## ⚡ Quick Install

```bash
# Clone the repository
git clone https://github.com/yourusername/otto.git
cd otto

# Run the installer
chmod +x install.sh
./install.sh
```

The installer will:
1. Ask which regulation you want (LGPD, GDPR, or both)
2. Install OTTO.ai as a Claude Code skill
3. Optionally configure automatic protection (hooks)
4. Set everything up automatically

---

## 🎯 What OTTO.ai Detects

### 🇧🇷 LGPD Violations

✅ CPF/RG/CNPJ hardcoded in code
✅ Personal data in logs (console.log, logger)
✅ Tracking/analytics without consent
✅ SQL queries violating data minimisation
✅ Passwords in plaintext
✅ API keys exposed
✅ Cookies without consent
✅ Data sharing with third parties
✅ SQL injection risks

### 🇪🇺 GDPR Violations

✅ SSN/National ID numbers exposed
✅ Personal data in logs
✅ Tracking without consent
✅ SELECT * queries (data minimisation)
✅ Unencrypted sensitive data
✅ Health/biometric data (special categories)
✅ API keys and secrets
✅ localStorage misuse
✅ External data transfers

---

## 💰 Fines You Can Avoid

### LGPD (Brazil)
- **Up to R$ 50 million per violation** (Art. 52)
- Public disclosure of violations
- Data blocking/deletion orders

### GDPR (Europe)
- **Up to €20M or 4% of annual global turnover** (whichever is higher)
- Applies per violation
- Cumulative fines for multiple violations

**Example:** 3 critical violations = potential R$ 150M (LGPD) or €60M (GDPR)

---

## 🚀 How to Use

### Automatic Mode (Recommended)

Once installed with hooks enabled, OTTO.ai works automatically:

```javascript
// You write code with privacy issues
console.log('User:', user); // ❌ Exposes PII

// OTTO.ai blocks and suggests fix:
// 🛡️ OTTO.ai detected privacy violation
// Use: console.log('User ID:', user.id)
```

### Manual Mode

Invoke OTTO.ai directly in Claude Code:

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

## 📋 Example Output

```
🛡️ OTTO.ai - LGPD Privacy Analysis

❌ VIOLATIONS FOUND: 3

📁 File: src/auth/login.js

1. 🚨 Cpf Exposure
   Line: 15
   Severity: CRITICAL

   ⚠️  Issue:
   CPF brasileiro exposto no código

   📋 Legal basis violated:
   LGPD Art. 46 (Dados Sensíveis)

   💰 Fine risk:
   Até R$ 50 milhões

   🔧 SUGGESTED FIX:
   Remova o CPF hardcoded. Busque de banco de dados
   criptografado ou use variável de ambiente para testes.

2. 🚨 User Logging
   Line: 23
   Severity: CRITICAL

   ⚠️  Issue:
   Possível exposição de dados pessoais em logs

   📋 Legal basis violated:
   LGPD Art. 46 (Segurança)

   💰 Fine risk:
   Até R$ 50 milhões

   🔧 SUGGESTED FIX:
   Log apenas IDs não-sensíveis: console.log('User ID:', user.id)
   ou use logger.sanitize(user)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SUMMARY:
   • 3 critical violations 🚨
   • 0 high severity violations ⚠️
   • 0 medium severity violations ⚡

✅ NEXT STEPS:
1. Fix critical violations immediately
2. Implement consent verification system
3. Add privacy tests to CI/CD
4. Document legal basis for data processing

🛡️ OTTO.ai protected your users today.
```

---

## 🔧 How It Works

### As a Claude Code Skill

OTTO.ai integrates seamlessly with Claude Code:

1. **Automatic invocation**: Claude invokes OTTO.ai when it detects code accessing personal data
2. **Real-time feedback**: Get immediate warnings about privacy violations
3. **Fix suggestions**: Receive corrected code that complies with regulations
4. **Educational**: Learn privacy principles while coding

### As a Hook (Optional)

When hooks are enabled, OTTO.ai validates code automatically:

- **Before edits**: Blocks privacy violations before they're saved
- **Before commits**: Ensures clean commits
- **CI/CD ready**: Can integrate into your build pipeline

---

## 📂 Project Structure

```
otto/
├── install.sh                    # Interactive installer
├── README.md                     # This file
├── skills/
│   ├── lgpd/                     # 🇧🇷 Brazilian regulation
│   │   ├── SKILL.md              # LGPD skill definition
│   │   └── patterns.json         # LGPD violation patterns
│   └── gdpr/                     # 🇪🇺 European regulation
│       ├── SKILL.md              # GDPR skill definition
│       └── patterns.json         # GDPR violation patterns
└── scripts/
    └── scan_privacy.py           # Python scanner engine
```

---

## 🎨 Examples

### ❌ Before OTTO.ai (Unsafe)

```javascript
// Hard-coded sensitive data
const user = {
  cpf: "123.456.789-00",
  email: "user@example.com"
};

// Logging personal data
console.log('User data:', user);

// Tracking without consent
analytics.track('login', {
  email: user.email,
  cpf: user.cpf
});

// Exposing all data
const users = await db.query('SELECT * FROM users');
```

**Risk**: Up to R$ 200 million in LGPD fines (4 violations × R$ 50M)

### ✅ After OTTO.ai (Safe)

```javascript
// No hardcoded data
const user = await getUserFromDB(userId);

// Safe logging (only IDs)
console.log('User ID:', user.id);

// Tracking with consent
if (user.hasConsent('analytics')) {
  analytics.track('login', {
    userId: hashUserId(user.id) // Pseudonymized
  });
}

// Data minimization
const users = await db.query(
  'SELECT id, name, email FROM users'
);
```

**Result**: ✅ LGPD/GDPR compliant, zero violation risk

---

## 🔒 Privacy & Security

OTTO.ai itself respects your privacy:

- ✅ **No data collection**: Runs entirely locally
- ✅ **No network calls**: Patterns are local JSON files
- ✅ **Open source**: Audit the code yourself
- ✅ **No telemetry**: Your code never leaves your machine

---

## 🤝 Contributing

Contributions are welcome! Especially:

- 🆕 New violation patterns
- 🌍 Support for other regulations (CCPA, PIPEDA, etc.)
- 🐛 Bug fixes and improvements
- 📖 Documentation updates
- 🧪 Test cases

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

## 📚 Resources

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

## 🐛 Troubleshooting

### OTTO.ai not showing up in Claude Code

1. Check installation: `ls -la ~/.claude/skills/otto/`
2. Restart Claude Code
3. Run `/help` to see if `/otto` is listed

### Hooks not working

1. Check settings: `cat ~/.claude/settings.json`
2. Verify Python is installed: `python3 --version`
3. Make scanner executable: `chmod +x ~/.claude/skills/otto/scripts/scan_privacy.py`

### False positives

OTTO.ai uses regex patterns and may flag legitimate code. You can:

1. Add context in comments explaining why code is safe
2. Adjust patterns in `~/.claude/skills/otto/scripts/patterns.json`
3. Disable specific patterns by removing them from JSON

---

## 📄 License

MIT License - Use and modify freely.

See [LICENSE](LICENSE) file for details.

---

## 💬 Support

- 🐛 **Bug reports**: [GitHub Issues](https://github.com/yourusername/otto/issues)
- 💡 **Feature requests**: [GitHub Discussions](https://github.com/yourusername/otto/discussions)
- 📧 **Email**: your-email@example.com

---

## 🙏 Acknowledgments

- Named in honor of **Otto**, because protecting data is like protecting family
- Inspired by the need for practical privacy compliance tools
- Built for the Claude Code community

---

## ⭐ Star Us!

If OTTO.ai helped you avoid a privacy violation, please star the repository!

---

**🛡️ OTTO.ai** - Guarding your code like family

*Making privacy compliance automatic, one line of code at a time.*
