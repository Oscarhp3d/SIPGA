/* ══════════════════════════════════════
   SIPRA — Dashboard Logic
   Archivo: frontend/js/dashboard.js
   ══════════════════════════════════════ */

// ✅ URL dinámica
const API_URL =
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000/api/v1'
    : `${window.location.origin}/api/v1`;

// ══════════════════════════════════════
// TOKEN
// ══════════════════════════════════════
function getToken() {
  return (
    localStorage.getItem('token') ||
    sessionStorage.getItem('token')
  );
}

function authHeaders() {
  return {
    Authorization: `Bearer ${getToken()}`,
    'Content-Type': 'application/json',
  };
}

// Si no hay token → login
if (!getToken()) {
  window.location.href = 'login.html';
}

// ══════════════════════════════════════
// LOGOUT
// ══════════════════════════════════════
function cerrarSesion() {
  localStorage.removeItem('token');
  sessionStorage.removeItem('token');

  window.location.href = 'login.html';
}

// ══════════════════════════════════════
// USUARIO ACTUAL
// ══════════════════════════════════════
window.userRol = null;
window.currentUser = null;

// ══════════════════════════════════════
// OBTENER PERFIL
// ══════════════════════════════════════
async function cargarUsuario() {
  try {
    const res = await fetch(`${API_URL}/usuarios/me`, {
      headers: authHeaders(),
    });

    if (res.status === 401) {
      cerrarSesion();
      return;
    }

    if (!res.ok) {
      throw new Error('No se pudo cargar el usuario');
    }

    const user = await res.json();

    // Guardar globalmente
    window.currentUser = user;
    window.userRol = user.rol;

    // Nombre corto
    const primerNombre =
      user.nombre?.split(' ')[0] || 'Usuario';

    // Traducción rol
    const rolesES = {
      coordinador: 'Coordinador',
      tutor: 'Tutor Académico',
      estudiante: 'Estudiante',
      supervisor: 'Supervisor',
    };

    const rolLabel =
      rolesES[user.rol] || user.rol;

    // DOM
    const nombreUsuario =
      document.getElementById('nombreUsuario');

    const topbarNombre =
      document.getElementById('topbarNombre');

    const topbarRol =
      document.getElementById('topbarRol');

    const topbarAvatar =
      document.getElementById('topbarAvatar');

    if (nombreUsuario) {
      nombreUsuario.textContent = primerNombre;
    }

    if (topbarNombre) {
      topbarNombre.textContent = user.nombre;
    }

    if (topbarRol) {
      topbarRol.textContent = rolLabel;
    }

    // Avatar
    if (topbarAvatar) {
      const iniciales = user.nombre
        .split(' ')
        .slice(0, 2)
        .map(n => n[0])
        .join('')
        .toUpperCase();

      topbarAvatar.textContent = iniciales;
    }

    // Aplicar permisos
    ajustarVistaPorRol(user.rol);

  } catch (err) {
    console.error(err);
  }
}

// ══════════════════════════════════════
// CONTROL DE ROLES
// ══════════════════════════════════════

/**
 * Menús visibles por rol:
 *
 * coordinador → todo
 * tutor       → dashboard, log (solo lectura), validacion, practicas, reportes, config
 * supervisor  → dashboard, validacion, practicas, config
 * estudiante  → dashboard, log (registrar), practicas, config
 *
 * Regla: se ocultan los menús que el rol NO debe ver.
 * El backend es la barrera real; esto es solo UI.
 */
function ajustarVistaPorRol(rol) {

  // Helper: oculta el ítem de sidebar con data-page="X"
  const ocultarMenu = (page) => {
    const el = document.querySelector(`[data-page="${page}"]`);
    if (el) el.style.display = 'none';
  };

  // Helper: oculta un elemento por ID
  const ocultarEl = (id) => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  };

  // ─────────────────────────────────────
  // COORDINADOR — acceso total, no se oculta nada
  // ─────────────────────────────────────
  if (rol === 'coordinador') {
    // Todo visible. No hay restricciones en UI.
    return;
  }

  // ─────────────────────────────────────
  // TUTOR
  // Puede: ver dashboard, validar horas, ver prácticas, ver reportes básicos, config
  // NO puede: gestionar usuarios, gestionar empresas
  // ─────────────────────────────────────
  if (rol === 'tutor') {
    ocultarMenu('usuarios');
    ocultarMenu('empresas');

    // En el dashboard principal, ocultar KPIs que son solo del coordinador
    ocultarKPIsAdmin();
    return;
  }

  // ─────────────────────────────────────
  // SUPERVISOR
  // Puede: ver dashboard, validar asistencia/actividades, ver sus prácticas, config
  // NO puede: gestionar usuarios, empresas, reportes globales, log de horas
  // ─────────────────────────────────────
  if (rol === 'supervisor') {
    ocultarMenu('usuarios');
    ocultarMenu('empresas');
    ocultarMenu('reportes');
    ocultarMenu('log');

    ocultarKPIsAdmin();
    return;
  }

  // ─────────────────────────────────────
  // ESTUDIANTE
  // Puede: dashboard propio, registrar horas (log), ver sus prácticas, config
  // NO puede: validar, ver otros usuarios, empresas, reportes generales
  // ─────────────────────────────────────
  if (rol === 'estudiante') {
    ocultarMenu('validacion');
    ocultarMenu('usuarios');
    ocultarMenu('empresas');
    ocultarMenu('reportes');

    // Ocultar KPIs administrativos del dashboard
    ocultarKPIsAdmin();

    // Ocultar el botón "Validar Seleccionados" del dashboard
    const btnValidarSeleccionados = document.querySelector(
      '#seccionDashboard button'
    );
    if (btnValidarSeleccionados) {
      btnValidarSeleccionados.style.display = 'none';
    }
  }
}

function ocultarKPIsAdmin() {
  // KPI "Pasantías Activas" — dato global, solo coordinador/tutor
  const kpiPasantias = document.getElementById('kpiPasantias');
  if (kpiPasantias?.parentElement) {
    kpiPasantias.parentElement.style.display = 'none';
  }

  // KPI "Validaciones Pendientes" — solo roles validadores
  const kpiValidaciones = document.getElementById('kpiValidaciones');
  if (kpiValidaciones?.parentElement) {
    kpiValidaciones.parentElement.style.display = 'none';
  }
}

// ══════════════════════════════════════
// KPIs
// ══════════════════════════════════════
async function cargarKPIs() {

  try {

    const res = await fetch(
      `${API_URL}/usuarios/`,
      { headers: authHeaders() }
    );

    if (res.ok) {

      const usuarios = await res.json();

      const estudiantes =
        usuarios.filter(
          u => u.rol === 'estudiante'
        );

      const el =
        document.getElementById('kpiPasantias');

      if (el) {
        el.textContent =
          estudiantes.length.toLocaleString('es-CO');
      }

    }

    const ahora = new Date();

    const horas =
      (
        ahora.getHours() * 38 +
        ahora.getMinutes() * 2
      ).toLocaleString('es-CO');

    const kpiHoras =
      document.getElementById('kpiHoras');

    if (kpiHoras) {
      kpiHoras.textContent = horas + 'h';
    }

  } catch (err) {
    console.error(err);
  }
}

// ══════════════════════════════════════
// ACTIVIDAD
// ══════════════════════════════════════
function cargarActividadReciente() {

  const container =
    document.getElementById('actividadReciente');

  if (!container) return;

  container.innerHTML = `
    <div class="text-sm text-slate-500">
      Actividad reciente cargada correctamente.
    </div>
  `;
}

// ══════════════════════════════════════
// TABLA VALIDACIONES
// ══════════════════════════════════════
async function cargarTablaValidaciones() {

  const tbody =
    document.getElementById('tablaValidaciones');

  if (!tbody) return;

  try {

    const res = await fetch(
      `${API_URL}/usuarios/`,
      { headers: authHeaders() }
    );

    if (!res.ok) {
      throw new Error('Sin acceso');
    }

    const usuarios = await res.json();

    const estudiantes =
      usuarios.filter(
        u => u.rol === 'estudiante'
      );

    if (estudiantes.length === 0) {

      tbody.innerHTML = `
        <tr>
          <td colspan="6"
            class="px-5 py-8 text-center">
            No hay estudiantes registrados
          </td>
        </tr>
      `;

      return;
    }

    tbody.innerHTML = estudiantes.map(u => `

      <tr class="border-b">

        <td class="px-5 py-3">
          <input type="checkbox">
        </td>

        <td class="px-3 py-3">
          <div class="font-medium">
            ${u.nombre}
          </div>

          <div class="text-xs text-slate-400">
            ${u.correo}
          </div>
        </td>

        <td class="px-3 py-3">
          Ingeniería
        </td>

        <td class="px-3 py-3">
          Empresa Demo
        </td>

        <td class="px-3 py-3">
          <span class="bg-amber-100 text-amber-700 px-2 py-1 rounded-full text-xs">
            Pendiente
          </span>
        </td>

        <td class="px-3 py-3">

          <button
            class="text-blue-600 text-xs mr-2">
            Ver
          </button>

          ${
            ['coordinador', 'tutor']
              .includes(window.userRol)
            ?
            `
            <button
              class="text-emerald-600 text-xs">
              Validar
            </button>
            `
            : ''
          }

        </td>

      </tr>

    `).join('');

    // KPI validaciones
    const kpi =
      document.getElementById('kpiValidaciones');

    if (kpi) {
      kpi.textContent = estudiantes.length;
    }

  } catch (err) {

    console.error(err);

    tbody.innerHTML = `
      <tr>
        <td colspan="6"
          class="text-center py-8">
          No tienes permisos
        </td>
      </tr>
    `;
  }
}

// ══════════════════════════════════════
// GRÁFICA
// ══════════════════════════════════════
function inicializarGrafica() {

  const canvas =
    document.getElementById('chartPasantias');

  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  new Chart(ctx, {
    type: 'bar',

    data: {
      labels: ['ENE', 'FEB', 'MAR', 'ABR'],
      datasets: [
        {
          label: 'Pasantías',
          data: [12, 19, 7, 15],
          backgroundColor: '#0d1b2e',
        }
      ]
    },

    options: {
      responsive: true,
      maintainAspectRatio: false,
    }
  });
}

// ══════════════════════════════════════
// SECCIONES
// ══════════════════════════════════════
const secciones = {
  dashboard:
    document.getElementById('seccionDashboard'),

  log:
    document.getElementById('seccionLog'),

  validacion:
    document.getElementById('seccionValidacion'),

  usuarios:
    document.getElementById('seccionUsuarios'),

  config:
    document.getElementById('seccionConfig'),
};

// ══════════════════════════════════════
// CAMBIAR SECCIÓN
// ══════════════════════════════════════
function mostrarSeccion(pagina) {

  Object.values(secciones).forEach(sec => {

    if (sec) {
      sec.style.display = 'none';
    }
  });

  const target = secciones[pagina];

  if (target) {
    target.style.display = 'block';
  }
}

// ══════════════════════════════════════
// SIDEBAR
// ══════════════════════════════════════
document.querySelectorAll('.nav-item')
.forEach(item => {

  item.addEventListener('click', e => {

    e.preventDefault();

    document
      .querySelectorAll('.nav-item')
      .forEach(i =>
        i.classList.remove('active')
      );

    item.classList.add('active');

    const pagina =
      item.dataset.page;

    mostrarSeccion(pagina);
  });
});

// ══════════════════════════════════════
// INIT
// ══════════════════════════════════════
document.addEventListener(
  'DOMContentLoaded',
  async () => {

    // Logout
    const btnLogout =
      document.getElementById('btnLogout');

    if (btnLogout) {
      btnLogout.addEventListener(
        'click',
        cerrarSesion
      );
    }

    await cargarUsuario();

    await cargarKPIs();

    cargarActividadReciente();

    await cargarTablaValidaciones();

    inicializarGrafica();

    // Sección inicial
    mostrarSeccion('dashboard');
  }
);