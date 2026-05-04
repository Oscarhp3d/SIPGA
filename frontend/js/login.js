/* ══════════════════════════════════════
   SIPRA — Login Logic
   ══════════════════════════════════════ */

const API_URL = 'http://127.0.0.1:8000/api/v1';

// ── Referencias al DOM ──
const emailInput  = document.getElementById('email');
const passInput   = document.getElementById('password');
const btnLogin    = document.getElementById('btnLogin');
const togglePass  = document.getElementById('togglePass');
const eyeIcon     = document.getElementById('eyeIcon');
const rememberMe  = document.getElementById('remember');
const errorMsg    = document.getElementById('errorMsg');

// ══════════════════════════════════════
// MOSTRAR / OCULTAR CONTRASEÑA
// ══════════════════════════════════════
togglePass.addEventListener('click', () => {
  const isPassword = passInput.type === 'password';
  passInput.type = isPassword ? 'text' : 'password';

  eyeIcon.innerHTML = isPassword
    ? /* ojo tachado */`
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
        <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
        <line x1="1" y1="1" x2="23" y2="23"/>`
    : /* ojo abierto */`
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
        <circle cx="12" cy="12" r="3"/>`;
});

// ══════════════════════════════════════
// MOSTRAR / OCULTAR ERROR
// ══════════════════════════════════════
function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.add('show');
}

function hideError() {
  errorMsg.classList.remove('show');
}

// ══════════════════════════════════════
// VALIDACIÓN BÁSICA
// ══════════════════════════════════════
function validate() {
  const email    = emailInput.value.trim();
  const password = passInput.value;

  if (!email) {
    showError('Por favor ingresa tu correo o usuario.');
    emailInput.focus();
    return false;
  }

  if (!password) {
    showError('Por favor ingresa tu contraseña.');
    passInput.focus();
    return false;
  }

  return true;
}

// ══════════════════════════════════════
// INICIO DE SESIÓN
// ══════════════════════════════════════
async function handleLogin() {
  hideError();

  if (!validate()) return;

  // Estado de carga
  btnLogin.classList.add('loading');
  btnLogin.textContent = 'Verificando...';

  try {
    const formData = new FormData();
    formData.append('username', emailInput.value.trim());
    formData.append('password', passInput.value);

    const res = await fetch(`${API_URL}/auth/token`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Credenciales incorrectas');
    }

    const data = await res.json();

    // Guardar token según checkbox
    const storage = rememberMe.checked ? localStorage : sessionStorage;
    storage.setItem('token', data.access_token);

    // Redirigir al dashboard
    window.location.href = 'dashboard.html';

  } catch (err) {
    showError(err.message || 'Correo o contraseña incorrectos. Intenta de nuevo.');
  } finally {
    btnLogin.classList.remove('loading');
    btnLogin.textContent = 'Iniciar Sesión';
  }
}

// ══════════════════════════════════════
// EVENTOS
// ══════════════════════════════════════

// Botón login
btnLogin.addEventListener('click', handleLogin);

// Enter en cualquier campo dispara el login
[emailInput, passInput].forEach(input => {
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') handleLogin();
  });
});

// Limpiar error al escribir
[emailInput, passInput].forEach(input => {
  input.addEventListener('input', hideError);
});
