// OTTO.ai Test File - Unsafe Code Examples
// This file contains intentional privacy violations for testing

// ❌ VIOLATION 1: CPF hardcoded
const adminCPF = "123.456.789-00";

// ❌ VIOLATION 2: User data in logs
function loginUser(user) {
  console.log('User logged in:', user); // Exposes all user data

  // ❌ VIOLATION 3: Tracking without consent
  analytics.track('login', {
    email: user.email,
    cpf: user.cpf,
    phone: user.phone
  });

  return true;
}

// ❌ VIOLATION 4: SELECT * violates minimization
async function getUsers() {
  const users = await db.query('SELECT * FROM users');
  return users;
}

// ❌ VIOLATION 5: Password in plaintext
const config = {
  admin_password: "admin123",
  api_key: "FAKE_API_KEY_EXAMPLE_DO_NOT_USE_123456"
};

// ❌ VIOLATION 6: Cookie without consent
function setCookie(userId) {
  document.cookie = `user_id=${userId}; max-age=31536000`;
}

// ❌ VIOLATION 7: SQL injection risk
function findUser(email) {
  return db.query(`SELECT * FROM users WHERE email = '${email}'`);
}

// ❌ VIOLATION 8: Sensitive data in localStorage
function storeUser(user) {
  localStorage.setItem('user', JSON.stringify(user));
}

// ❌ VIOLATION 9: External data sharing
async function syncUserData(user) {
  await fetch('https://external-api.com/users', {
    method: 'POST',
    body: JSON.stringify({
      email: user.email,
      cpf: user.cpf,
      address: user.address
    })
  });
}

// Expected OTTO.ai output: 9+ critical violations detected
