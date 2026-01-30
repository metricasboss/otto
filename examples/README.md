# 🧪 OTTO Example Files

## ⚠️ SECURITY NOTICE

**These files contain INTENTIONALLY INSECURE code for demonstration purposes.**

All API keys, passwords, and sensitive data in this directory are:
- ✅ **FAKE** - Not real credentials
- ✅ **For testing only** - Demonstrate what OTTO detects
- ✅ **Safe** - No actual secrets are exposed

## Files

### `unsafe_code.js`
Contains **intentionally bad code** that violates LGPD/GDPR:
- Hardcoded fake API keys
- Fake passwords in plaintext
- Fake personal data (CPF)
- Examples of what **NOT** to do

**Purpose**: Show what OTTO detects and prevents.

### `safe_code.js`
Contains **secure, compliant code**:
- Proper environment variables
- Password hashing
- Consent verification
- Data minimization
- Examples of what **TO** do

**Purpose**: Show the corrected version of unsafe patterns.

## GitHub Security Scanning

If GitHub flags secrets in these files:
- ✅ It's working correctly
- ✅ The secrets are fake
- ✅ Files are marked with `pragma: allowlist secret`
- ✅ Configured in `.gitleaksignore` and `.gitguardian.yaml`

## For Contributors

When adding new example violations:
1. Use obviously fake data (e.g., `FAKE_`, `EXAMPLE_`, `TEST_`)
2. Add comment: `// pragma: allowlist secret`
3. Document in this README
4. Never use real credentials

---

**🛡️ OTTO** - These examples help developers learn privacy compliance.
