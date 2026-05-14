// ═══════════════════════════════════════════════════════════════
//  SIPRA · dashboard.js
//  Carga datos reales desde la API y los renderiza en el dashboard
// ═══════════════════════════════════════════════════════════════

const API_URL =
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000/api/v1'
    : `${window.location.origin}/api/v1`;

// ── Auth ──────────────────────────────────────────────────────
function getToken() {
  return localStorage.getItem('token') || sessionStorage.getItem('token');
}
function authHeaders() {
  return { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' };
}
if (!getToken()) window.location.href = 'login.html';

function cerrarSesion() {
  localStorage.removeItem('token');
  sessionStorage.removeItem('token');
  window.location.href = 'login.html';
}

// ── Estado global ────────────────────────────────────────────
window.userRol = null;
window.currentUser = null;
let chartInstance = null;

// ── Cargar usuario ───────────────────────────────────────────
async function cargarUsuario() {
  try {
    const res = await fetch(`${API_URL}/usuarios/me`, { headers: authHeaders() });
    if (res.status === 401) { cerrarSesion(); return; }
    if (!res.ok) throw new Error('No se pudo cargar el usuario');

    const user = await res.json();
    window.currentUser = user;
    window.userRol = user.rol;

    const primerNombre = user.nombre?.split(' ')[0] || 'Usuario';
    const rolesES = { coordinador: 'Coordinador', tutor: 'Tutor Académico', estudiante: 'Estudiante', supervisor: 'Supervisor' };
    const rolLabel = rolesES[user.rol] || user.rol;

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('nombreUsuario', primerNombre);
    set('topbarNombre', user.nombre);
    set('topbarRol', rolLabel);

    const avatar = document.getElementById('topbarAvatar');
    if (avatar) {
      avatar.textContent = user.nombre.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase();
    }

    ajustarVistaPorRol(user.rol);
  } catch (err) { console.error('cargarUsuario:', err); }
}

function ajustarVistaPorRol(rol) {
  const ocultar = (sel) => { const el = document.querySelector(sel); if (el) el.style.display = 'none'; };

  if (rol === 'tutor') {
    ocultar('[data-page="usuarios"]');
    ocultar('[data-page="empresas"]');
    ocultarKPIsAdmin();
  } else if (rol === 'supervisor') {
    ocultar('[data-page="usuarios"]');
    ocultar('[data-page="empresas"]');
    ocultar('[data-page="reportes"]');
    ocultar('[data-page="log"]');
    ocultarKPIsAdmin();
  } else if (rol === 'estudiante') {
    ocultar('[data-page="validacion"]');
    ocultar('[data-page="usuarios"]');
    ocultar('[data-page="empresas"]');
    ocultar('[data-page="reportes"]');
    ocultarKPIsAdmin();
  }
}

function ocultarKPIsAdmin() {
  ['kpiPasantias', 'kpiValidaciones'].forEach(id => {
    const el = document.getElementById(id);
    if (el?.parentElement) el.parentElement.style.display = 'none';
  });
}

// ── KPIs reales ──────────────────────────────────────────────
async function cargarKPIs() {
  const rol = window.userRol;

  // ── KPIs coordinador/tutor: vienen del endpoint /dashboard/resumen
  if (['coordinador', 'tutor'].includes(rol)) {
    try {
      const res = await fetch(`${API_URL}/dashboard/resumen`, { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();

        const kpiPas = document.getElementById('kpiPasantias');
        if (kpiPas) kpiPas.textContent = data.pasantias_activas.toLocaleString('es-CO');

        const kpiHoras = document.getElementById('kpiHoras');
        if (kpiHoras) kpiHoras.textContent = `${data.horas_hoy.toLocaleString('es-CO')}h`;

        const kpiVal = document.getElementById('kpiValidaciones');
        if (kpiVal) kpiVal.textContent = data.validaciones_pendientes.toLocaleString('es-CO');
      }
    } catch (err) { console.error('cargarKPIs (coordinador):', err); }
    return;
  }

  // ── KPI horas para estudiante
  if (rol === 'estudiante') {
    try {
      const res = await fetch(`${API_URL}/estudiante/dashboard`, { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        const kpiHoras = document.getElementById('kpiHoras');
        if (kpiHoras) kpiHoras.textContent = `${(data.horas_acumuladas || 0).toLocaleString('es-CO')}h`;
      }
    } catch (err) { console.error('cargarKPIs (estudiante):', err); }
  }
}

// ── Gráfica de progreso (datos reales) ───────────────────────
async function inicializarGrafica() {
  const canvas = document.getElementById('chartPasantias');
  if (!canvas) return;

  // Destruir instancia anterior si existe
  if (chartInstance) { chartInstance.destroy(); chartInstance = null; }

  // Mostrar skeleton mientras carga
  canvas.style.opacity = '0.4';

  try {
    const res = await fetch(`${API_URL}/dashboard/progreso-pasantias`, { headers: authHeaders() });
    if (!res.ok) throw new Error('Sin datos de progreso');

    const { labels, datasets } = await res.json();
    canvas.style.opacity = '1';

    chartInstance = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: datasets.length > 1,
            position: 'bottom',
            labels: { font: { size: 11 }, boxWidth: 12 },
          },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${ctx.raw} pasantía${ctx.raw !== 1 ? 's' : ''}`,
            },
          },
        },
        scales: {
          x: { stacked: datasets.length > 1, grid: { display: false } },
          y: { stacked: datasets.length > 1, beginAtZero: true, ticks: { stepSize: 1, precision: 0 } },
        },
      },
    });
  } catch (err) {
    console.warn('Gráfica: usando datos de muestra —', err.message);
    canvas.style.opacity = '1';
    // Fallback con datos vacíos visualmente correctos
    chartInstance = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
        datasets: [{ label: 'Sin datos', data: [0,0,0,0,0,0], backgroundColor: '#cbd5e1' }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
      },
    });
  }
}

// ── Actividad reciente (datos reales) ────────────────────────
async function cargarActividadReciente() {
  const container = document.getElementById('actividadReciente');
  if (!container) return;

  const rol = window.userRol;
  if (!['coordinador', 'tutor'].includes(rol)) {
    container.innerHTML = '<div class="text-sm text-slate-400 text-center py-4">No disponible para tu rol</div>';
    return;
  }

  container.innerHTML = '<div class="text-sm text-slate-400 text-center py-4">Cargando…</div>';

  try {
    const res = await fetch(`${API_URL}/dashboard/actividad-reciente`, { headers: authHeaders() });
    if (!res.ok) throw new Error('Sin actividad');
    const actividades = await res.json();

    if (!actividades.length) {
      container.innerHTML = '<div class="text-sm text-slate-400 text-center py-4">Sin actividad reciente</div>';
      return;
    }

    const colores = {
      borrador:  'bg-slate-100 text-slate-600',
      enviado:   'bg-amber-100 text-amber-700',
      aprobado:  'bg-green-100 text-green-700',
      rechazado: 'bg-red-100 text-red-700',
    };

    const formatFecha = (iso) => {
      if (!iso) return '—';
      const d = new Date(iso);
      return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
    };

    container.innerHTML = actividades.map(a => `
      <div class="flex items-start gap-3 py-2 border-b last:border-0">
        <span class="${colores[a.estado] || 'bg-slate-100 text-slate-600'} text-xs px-2 py-0.5 rounded-full whitespace-nowrap mt-0.5">
          ${a.estado.charAt(0).toUpperCase() + a.estado.slice(1)}
        </span>
        <div class="flex-1 min-w-0">
          <p class="text-sm text-slate-700 leading-snug">${a.descripcion}</p>
          <p class="text-xs text-slate-400 mt-0.5">${a.empresa} · ${a.horas}h · ${formatFecha(a.fecha)}</p>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('cargarActividadReciente:', err);
    container.innerHTML = '<div class="text-sm text-slate-400 text-center py-4">No se pudo cargar la actividad</div>';
  }
}

// ── Tabla de validaciones ─────────────────────────────────────
async function cargarTablaValidaciones() {
  const tbody = document.getElementById('tablaValidaciones');
  if (!tbody) return;

  const rol = window.userRol;
  if (!['coordinador', 'tutor', 'supervisor'].includes(rol)) {
    tbody.innerHTML = `<tr><td colspan="6" class="px-5 py-8 text-center text-slate-400">No aplica para tu rol</td></tr>`;
    return;
  }

  try {
    let seguimientos = [];

    if (rol === 'coordinador') {
      const resPracticas = await fetch(`${API_URL}/practicas/`, { headers: authHeaders() });
      if (resPracticas.ok) {
        const practicas = await resPracticas.json();
        for (const p of practicas.slice(0, 15)) {
          const resSeg = await fetch(`${API_URL}/seguimientos/practica/${p.id}`, { headers: authHeaders() });
          if (resSeg.ok) {
            const segs = await resSeg.json();
            seguimientos.push(...segs.filter(s => s.estado === 'enviado').map(s => ({ ...s, _practica: p })));
          }
        }
      }
    } else {
      const ep = rol === 'tutor' ? `${API_URL}/tutor/pendientes` : `${API_URL}/supervisor/pendientes`;
      const res = await fetch(ep, { headers: authHeaders() });
      if (!res.ok) throw new Error('Sin acceso');
      seguimientos = await res.json();
    }

    const kpiVal = document.getElementById('kpiValidaciones');
    if (kpiVal) kpiVal.textContent = seguimientos.length.toLocaleString('es-CO');

    if (!seguimientos.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="px-5 py-8 text-center text-slate-400">No hay seguimientos pendientes</td></tr>`;
      return;
    }

    const colores = { enviado: 'bg-amber-100 text-amber-700', aprobado: 'bg-green-100 text-green-700', rechazado: 'bg-red-100 text-red-700', borrador: 'bg-slate-100 text-slate-600' };

    tbody.innerHTML = seguimientos.map(s => {
      const p = s._practica || null;
      const estudiante = p?.estudiante?.nombre || 'Estudiante';
      const empresa = p?.empresa?.nombre || 'Empresa';
      const fecha = s.fecha_actividad ? new Date(s.fecha_actividad).toLocaleDateString('es-CO') : '—';
      const colorClase = colores[s.estado] || 'bg-slate-100 text-slate-600';
      const estadoLabel = s.estado.charAt(0).toUpperCase() + s.estado.slice(1);

      return `
      <tr class="border-b hover:bg-slate-50 transition-colors">
        <td class="px-5 py-3"><input type="checkbox" data-id="${s.id}"></td>
        <td class="px-3 py-3">
          <div class="font-medium">${estudiante}</div>
          <div class="text-xs text-slate-400">${fecha} · ${s.horas_realizadas}h</div>
        </td>
        <td class="px-3 py-3 text-sm">${s.descripcion.slice(0, 50)}${s.descripcion.length > 50 ? '…' : ''}</td>
        <td class="px-3 py-3 text-sm">${empresa}</td>
        <td class="px-3 py-3">
          <span class="${colorClase} px-2 py-1 rounded-full text-xs">${estadoLabel}</span>
        </td>
        <td class="px-3 py-3 flex gap-2">
          <button class="text-blue-600 text-xs hover:underline" onclick="verSeguimiento('${s.id}')">Ver</button>
          ${['coordinador', 'tutor'].includes(rol) ? `
          <button class="text-emerald-600 text-xs hover:underline" onclick="aprobarSeguimiento('${s.id}')">Aprobar</button>
          <button class="text-red-500 text-xs hover:underline" onclick="rechazarSeguimiento('${s.id}')">Rechazar</button>` : ''}
        </td>
      </tr>`;
    }).join('');
  } catch (err) {
    console.error('cargarTablaValidaciones:', err);
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-slate-400">No tienes permisos para ver esta sección</td></tr>`;
  }
}

async function aprobarSeguimiento(id)  { await _validarSeguimiento(id, 'aprobado'); }
async function rechazarSeguimiento(id) { await _validarSeguimiento(id, 'rechazado'); }
async function verSeguimiento(id)      { alert('Seguimiento ID: ' + id); }

async function _validarSeguimiento(id, estado) {
  try {
    const res = await fetch(`${API_URL}/seguimientos/${id}/validar`, {
      method: 'PATCH', headers: authHeaders(), body: JSON.stringify({ estado }),
    });
    if (!res.ok) { const err = await res.json().catch(() => ({})); alert('Error: ' + (err.detail || 'No se pudo validar')); return; }
    await cargarTablaValidaciones();
    await cargarKPIs();
  } catch (e) { console.error(e); }
}

// ── Navegación ────────────────────────────────────────────────
const secciones = {
  dashboard:  document.getElementById('seccionDashboard'),
  log:        document.getElementById('seccionLog'),
  validacion: document.getElementById('seccionValidacion'),
  usuarios:   document.getElementById('seccionUsuarios'),
  config:     document.getElementById('seccionConfig'),
};

function mostrarSeccion(pagina) {
  Object.values(secciones).forEach(sec => { if (sec) sec.style.display = 'none'; });
  const target = secciones[pagina];
  if (target) target.style.display = 'block';
}

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    mostrarSeccion(item.dataset.page);
  });
});

// ── Bootstrap ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  const btnLogout = document.getElementById('btnLogout');
  if (btnLogout) btnLogout.addEventListener('click', cerrarSesion);

  await cargarUsuario();
  await cargarKPIs();
  await cargarActividadReciente();
  await cargarTablaValidaciones();
  await inicializarGrafica();
  mostrarSeccion('dashboard');
});