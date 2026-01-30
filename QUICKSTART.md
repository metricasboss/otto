# 🚀 OTTO - Quick Start Guide

Get OTTO running in 2 minutes!

---

## Step 1: Installation

```bash
# Clone the repository
git clone https://github.com/metricasboss/otto.git
cd otto

# Run the installer
./install.sh
```

**Interactive prompts:**

1. **Choose regulation:**
   - `1` for LGPD (Brazil)
   - `2` for GDPR (Europe)
   - `3` for Both

2. **Enable automatic protection?**
   - `y` for automatic hooks (recommended)
   - `n` for manual only

---

## Step 2: Test It

### Quick Test (Standalone)

```bash
# Scan the unsafe example
python3 scripts/scan_privacy.py examples/unsafe_code.js

# Should show ~10 violations detected
```

### Test in Claude Code

```bash
# Start Claude Code
claude

# In the REPL, invoke OTTO:
/otto

# Or type:
"Check this code for privacy issues"
```

Claude will automatically use OTTO when relevant!

---

## Step 3: Use in Your Project

### Automatic Mode (if hooks enabled)

Just code normally in Claude Code. OTTO watches and alerts automatically:

```javascript
// You write:
console.log('User:', user);

// OTTO blocks:
🛡️ OTTO detected privacy violation
Use: console.log('User ID:', user.id)
```

### Manual Mode

```bash
# In Claude Code REPL:
/otto scan src/

# Or analyze current file:
/otto
```

---

## What Gets Detected

### 🇧🇷 LGPD (Brazil)
- ✅ CPF/RG/CNPJ in code
- ✅ Personal data in logs
- ✅ Tracking without consent
- ✅ SQL SELECT * (minimization)
- ✅ Plaintext passwords
- ✅ Hardcoded API keys
- ✅ Cookies without consent
- ✅ SQL injection risks

### 🇪🇺 GDPR (Europe)
- ✅ SSN/National IDs
- ✅ Personal data in logs
- ✅ Tracking without consent
- ✅ Data minimization violations
- ✅ Unencrypted sensitive data
- ✅ Special categories (health, biometric)
- ✅ External data transfers

---

## Common Commands

```bash
# Check OTTO installation
ls -la ~/.claude/skills/otto/

# View configuration
cat ~/.claude/settings.json | grep -A 10 "hooks"

# Test scanner directly
python3 ~/.claude/skills/otto/scripts/scan_privacy.py myfile.js

# Change regulation
cd ~/.claude/skills/otto/
echo "gdpr" > .regulation  # Switch to GDPR
echo "lgpd" > .regulation  # Switch to LGPD
echo "both" > .regulation  # Use both
```

---

## Example: Before & After

### ❌ Before OTTO

```javascript
const user = { cpf: "123.456.789-00" };
console.log('User:', user);
analytics.track('login', { email: user.email });
```

**Risk:** R$ 150 million in fines (3 violations × R$ 50M)

### ✅ After OTTO

```javascript
const user = await getUserFromDB(userId);
console.log('User ID:', user.id);
if (user.hasConsent('analytics')) {
  analytics.track('login', { userId: hash(user.id) });
}
```

**Result:** Zero violations, LGPD/GDPR compliant ✅

---

## Troubleshooting

### OTTO not appearing in Claude Code

```bash
# Check installation
ls ~/.claude/skills/otto/SKILL.md

# Restart Claude Code
# Run /help to see available skills
```

### Hooks not working

```bash
# Verify Python
python3 --version

# Make script executable
chmod +x ~/.claude/skills/otto/scripts/scan_privacy.py

# Check settings
cat ~/.claude/settings.json
```

### False positives

OTTO uses regex patterns and may flag some safe code. This is normal!

**Options:**
1. Review and ignore if code is actually safe
2. Adjust patterns in `~/.claude/skills/otto/scripts/patterns.json`
3. Add comments explaining why code is safe

---

## Next Steps

1. ⭐ Star the repository if it helped you!
2. 🐛 Report issues: [GitHub Issues](https://github.com/metricasboss/otto/issues)
3. 🤝 Contribute new patterns
4. 📖 Read full docs: [README.md](README.md)

---

**🛡️ OTTO is protecting your code!**

*Named in honor of Otto - Protecting data like family*
