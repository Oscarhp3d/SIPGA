const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:' || !window.location.hostname
  ? 'http://127.0.0.1:8000/api/v1'
  : `${window.location.origin}/api/v1`;


const emailInput = document.getElementById('email');
const passInput  = document.getElementById('password');
const btnLogin   = document.getElementById('btnLogin');
const togglePass = document.getElementById('togglePass');
const eyeIcon    = document.getElementById('eyeIcon');
const rememberMe = document.getElementById('remember');
const errorMsg   = document.getElementById('errorMsg');


togglePass.addEventListener('click', () => {
  const isPassword = passInput.type === 'password';
  passInput.type = isPassword ? 'text' : 'password';

  eyeIcon.innerHTML = isPassword
    ? `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
       <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
       <line x1="1" y1="1" x2="23" y2="23"/>`
    : `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
       <circle cx="12" cy="12" r="3"/>`;
});


function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.add('show');
}

function hideError() {
  errorMsg.classList.remove('show');
}


function validate() {
  if (!emailInput.value.trim()) {
    showError('Por favor ingresa tu correo o usuario.');
    emailInput.focus();
    return false;
  }
  if (!passInput.value) {
    showError('Por favor ingresa tu contraseña.');
    passInput.focus();
    return false;
  }
  return true;
}


function getToken() {
  return localStorage.getItem('token') || sessionStorage.getItem('token');
}


function getAuthHeaders() {
  const token = getToken();
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}


async function handleLogin() {
  hideError();
  if (!validate()) return;

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


    const storage = rememberMe.checked ? localStorage : sessionStorage;
    storage.setItem('token', data.access_token);

    
    window.location.href = 'dashboard.html';

  } catch (err) {
    showError(err.message || 'Correo o contraseña incorrectos. Intenta de nuevo.');
  } finally {
    btnLogin.classList.remove('loading');
    btnLogin.textContent = 'Iniciar Sesión';
  }
}


btnLogin.addEventListener('click', handleLogin);

[emailInput, passInput].forEach(input => {
  input.addEventListener('keydown', e => { if (e.key === 'Enter') handleLogin(); });
  input.addEventListener('input', hideError);
});