#!/bin/bash

# OTTO Demo Script
# Run this to record a GIF demonstration

clear

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║           OTTO - Privacy Guardian Demo                      ║"
echo "║           Catching LGPD violations in real-time              ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
sleep 2

echo "📝 Developer writes code with Claude..."
echo ""
sleep 1

echo "// AI-generated user tracking"
sleep 0.5
echo "async function trackUserLogin(user) {"
sleep 0.5
echo "  console.log('User login:', user);"
sleep 0.5
echo "  "
sleep 0.5
echo "  analytics.track('login', {"
sleep 0.5
echo "    email: user.email,"
sleep 0.5
echo "    cpf: user.cpf,"
sleep 0.5
echo "    location: user.address"
sleep 0.5
echo "  });"
sleep 0.5
echo "}"
sleep 1

echo ""
echo "🔍 OTTO scanning code before commit..."
echo ""
sleep 2

cat << 'EOF'

🛡️ OTTO - LGPD Privacy Analysis

❌ VIOLATIONS FOUND: 2

📁 File: trackUserLogin.js

1. 🚨 User Logging
   Line: 3
   Severity: CRITICAL

   Issue: Possível exposição de dados pessoais em logs
   Legal basis: LGPD Art. 46 (Segurança)
   Fine risk: Até R$ 50 milhões

   FIX: console.log('User ID:', user.id)

2. 🚨 Tracking Without Consent
   Line: 5
   Severity: CRITICAL

   Issue: Tracking sem verificação de consentimento
   Legal basis: LGPD Art. 7º I
   Fine risk: Até R$ 50 milhões

   FIX: if (user.hasConsent('analytics')) { ... }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY:
   • 2 critical violations
   • Risk: R$ 100 million

🛡️ OTTO blocked commit - fix violations first
EOF

sleep 3

echo ""
echo ""
echo "✅ Developer fixes code with OTTO suggestions..."
echo ""
sleep 1

echo "// OTTO-corrected code"
sleep 0.5
echo "async function trackUserLogin(user) {"
sleep 0.5
echo "  console.log('User ID:', user.id); // ✅ No PII"
sleep 0.5
echo "  "
sleep 0.5
echo "  if (user.hasConsent('analytics')) { // ✅ Consent"
sleep 0.5
echo "    analytics.track('login', {"
sleep 0.5
echo "      userId: hash(user.id) // ✅ Anonymized"
sleep 0.5
echo "    });"
sleep 0.5
echo "  }"
sleep 0.5
echo "}"
sleep 2

echo ""
echo "🔍 OTTO re-scanning..."
sleep 1
echo ""

cat << 'EOF'
🛡️ OTTO - LGPD Privacy Analysis

✅ No violations detected.
   Code complies with LGPD.

💾 Safe to commit!

🛡️ OTTO protected your users today.
EOF

sleep 2

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║  🎉 R$ 100 MILLION IN FINES AVOIDED                         ║"
echo "║                                                              ║"
echo "║  OTTO: Safety net for AI-generated code                     ║"
echo "║  github.com/metricasboss/otto                               ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

sleep 3
