// OTTO Test File - Safe Code Examples
// This file shows LGPD/GDPR compliant code

// ✅ SAFE 1: No hardcoded sensitive data
const adminId = process.env.ADMIN_ID;

// ✅ SAFE 2: Sanitized logging
function loginUser(user) {
  console.log('User ID logged in:', user.id); // Only non-sensitive ID

  // ✅ SAFE 3: Tracking with consent check
  if (user.hasConsent('analytics')) {
    analytics.track('login', {
      userId: hashUserId(user.id) // Pseudonymized
    });
  }

  return true;
}

// ✅ SAFE 4: Data minimization (specific fields)
async function getUsers() {
  const users = await db.query(
    'SELECT id, name, email FROM users'
  );
  return users;
}

// ✅ SAFE 5: Encrypted secrets
const config = {
  admin_password_hash: await bcrypt.hash(password, 10),
  api_key: process.env.API_KEY
};

// ✅ SAFE 6: Cookie with consent
function setCookie(userId) {
  if (cookieConsent.hasConsent('functional')) {
    document.cookie = `user_id=${userId}; max-age=31536000; Secure; SameSite=Strict`;
  }
}

// ✅ SAFE 7: Prepared statement (prevents SQL injection)
function findUser(email) {
  return db.query('SELECT id, name FROM users WHERE email = ?', [email]);
}

// ✅ SAFE 8: Only tokens in sessionStorage
function storeSession(token) {
  sessionStorage.setItem('auth_token', token);
}

// ✅ SAFE 9: Data sharing with consent and minimization
async function syncUserData(user) {
  if (user.hasConsent('data_sharing')) {
    await fetch('https://external-api.com/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        userId: anonymize(user.id) // Anonymized, no PII
      })
    });
  }
}

// Expected OTTO output: ✅ No violations detected
