/* ══════════════════════════════════════
   SIPRA — Dashboard Logic
   Archivo: frontend/js/dashboard.js
   ══════════════════════════════════════ */

const API_URL = 'http://127.0.0.1:8000/api/v1';

// ══════════════════════════════════════
// UTILIDADES DE TOKEN
// ══════════════════════════════════════
function getToken() {
  return localStorage.getItem('token') || sessionStorage.getItem('token');
}

function authHeaders() {
  return {
    'Authorization': `Bearer ${getToken()}`,
    'Content-Type': 'application/json',
  };
}

// Si no hay token, redirigir al login
if (!getToken()) {
  window.location.href = 'login.html';
}

// ══════════════════════════════════════
// OBTENER PERFIL DEL USUARIO
// ══════════════════════════════════════
async function cargarUsuario() {
  try {
    const res = await fetch(`${API_URL}/usuarios/me`, { headers: authHeaders() });

    if (res.status === 401) {
      // Token expirado
      localStorage.removeItem('token');
      sessionStorage.removeItem('token');
      window.location.href = 'login.html';
      return;
    }

    const user = await res.json();

    // Nombre — mostrar solo el primer nombre
    const primerNombre = user.nombre?.split(' ')[0] || 'Usuario';

    // Rol legible en español
    const rolesES = {
      coordinador: 'Coordinador',
      tutor:       'Tutor Académico',
      estudiante:  'Estudiante',
      supervisor:  'Supervisor',
    };
    const rolLabel = rolesES[user.rol] || user.rol;

    // Actualizar saludo
    document.getElementById('nombreUsuario').textContent = primerNombre;

    // Topbar
    document.getElementById('topbarNombre').textContent = user.nombre;
    document.getElementById('topbarRol').textContent    = rolLabel;

    // Avatar — iniciales
    const iniciales = user.nombre
      .split(' ')
      .slice(0, 2)
      .map(n => n[0])
      .join('')
      .toUpperCase();
    document.getElementById('topbarAvatar').textContent = iniciales;

    // Mostrar u ocultar secciones según rol
    ajustarVistaPorRol(user.rol);

  } catch (err) {
    console.error('Error cargando usuario:', err);
  }
}

// ══════════════════════════════════════
// AJUSTAR VISTA SEGÚN ROL
// ══════════════════════════════════════
function ajustarVistaPorRol(rol) {
  // El menú "Usuarios" solo lo ven coordinadores y tutores
  const menuUsuarios = document.querySelector('[data-page="usuarios"]');
  if (menuUsuarios && !['coordinador', 'tutor'].includes(rol)) {
    menuUsuarios.style.display = 'none';
  }
}

// ══════════════════════════════════════
// CARGAR KPIs
// ══════════════════════════════════════
async function cargarKPIs() {
  try {
    // Pasantías (lista de usuarios para tener un conteo real)
    const resPasantias = await fetch(`${API_URL}/usuarios/`, { headers: authHeaders() });

    if (resPasantias.ok) {
      const usuarios = await resPasantias.json();
      const estudiantes = usuarios.filter(u => u.rol === 'estudiante');
      document.getElementById('kpiPasantias').textContent =
        estudiantes.length.toLocaleString('es-CO');
    } else {
      document.getElementById('kpiPasantias').textContent = 'N/A';
    }

    // Horas loggeadas hoy — placeholder dinámico basado en hora actual
    const ahora = new Date();
    const horasSimuladas = (ahora.getHours() * 38 + ahora.getMinutes() * 2).toLocaleString('es-CO');
    document.getElementById('kpiHoras').textContent = horasSimuladas + 'h';

    // Validaciones pendientes
    document.getElementById('kpiValidaciones').textContent = '—';

  } catch (err) {
    console.error('Error cargando KPIs:', err);
    document.getElementById('kpiPasantias').textContent   = 'N/A';
    document.getElementById('kpiHoras').textContent       = 'N/A';
    document.getElementById('kpiValidaciones').textContent = 'N/A';
  }
}

// ══════════════════════════════════════
// CARGAR ACTIVIDAD RECIENTE
// ══════════════════════════════════════
function cargarActividadReciente() {
  // Actividad simulada — puedes conectar al endpoint de logs cuando esté disponible
  const actividades = [
    {
      icon: 'edit',
      color: 'bg-blue-100 text-blue-500',
      texto: '<b>María López</b> editó su log de horas en <i>Proyectos II</i>',
      tiempo: 'Hace 12 minutos',
    },
    {
      icon: 'check',
      color: 'bg-emerald-100 text-emerald-500',
      texto: 'Pasantía finalizada: <b>Jorge Ramírez</b> (Ingeniería)',
      tiempo: 'Hace 45 minutos',
    },
    {
      icon: 'alert',
      color: 'bg-amber-100 text-amber-500',
      texto: 'Nueva validación pendiente en <b>Recursos Humanos</b>',
      tiempo: 'Hace 2 horas',
    },
    {
      icon: 'users',
      color: 'bg-purple-100 text-purple-500',
      texto: '<b>5 alumnos</b> nuevos registrados en el sistema',
      tiempo: 'Hace 4 horas',
    },
  ];

  const iconsSVG = {
    edit:  `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`,
    check: `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    alert: `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    users: `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
  };

  const container = document.getElementById('actividadReciente');
  container.innerHTML = actividades.map(a => `
    <div class="flex items-start gap-3">
      <div class="w-7 h-7 rounded-lg ${a.color} flex items-center justify-center flex-shrink-0 mt-0.5">
        ${iconsSVG[a.icon]}
      </div>
      <div>
        <p class="text-xs text-slate-600 leading-relaxed">${a.texto}</p>
        <p class="text-[10px] text-slate-400 mt-0.5">${a.tiempo}</p>
      </div>
    </div>
  `).join('');
}

// ══════════════════════════════════════
// CARGAR TABLA VALIDACIONES
// ══════════════════════════════════════
async function cargarTablaValidaciones() {
  const tbody = document.getElementById('tablaValidaciones');

  try {
    const res = await fetch(`${API_URL}/usuarios/`, { headers: authHeaders() });

    if (!res.ok) throw new Error('Sin acceso');

    const usuarios = await res.json();
    const estudiantes = usuarios.filter(u => u.rol === 'estudiante').slice(0, 6);

    if (estudiantes.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="px-5 py-8 text-center text-sm text-slate-300">No hay validaciones pendientes</td></tr>`;
      return;
    }

    const estados = ['Pendiente', 'En revisión', 'Enviado'];
    const empresas = ['Tech Solutions S.A.S', 'Bancolombia', 'EPM', 'Grupo Éxito', 'Avianca', 'Nutresa'];
    const facultades = ['Ingeniería', 'Administración', 'Derecho', 'Medicina', 'Psicología'];

    tbody.innerHTML = estudiantes.map((u, i) => {
      const estado = estados[i % estados.length];
      const badgeColor = estado === 'Pendiente'
        ? 'bg-amber-100 text-amber-700'
        : estado === 'En revisión'
        ? 'bg-blue-100 text-blue-700'
        : 'bg-emerald-100 text-emerald-700';

      return `
        <tr class="table-row border-b border-slate-50 transition-colors">
          <td class="px-5 py-3">
            <input type="checkbox" class="w-3.5 h-3.5 accent-slate-800"/>
          </td>
          <td class="px-3 py-3">
            <div class="text-xs font-medium text-slate-700">${u.nombre}</div>
            <div class="text-[10px] text-slate-400">${u.correo}</div>
          </td>
          <td class="px-3 py-3 text-xs text-slate-600">${facultades[i % facultades.length]}</td>
          <td class="px-3 py-3 text-xs text-slate-600">${empresas[i % empresas.length]}</td>
          <td class="px-3 py-3">
            <span class="text-[10px] font-medium px-2 py-0.5 rounded-full ${badgeColor}">${estado}</span>
          </td>
          <td class="px-3 py-3">
            <button class="text-[10px] font-semibold text-blue-600 hover:text-blue-800 transition-colors mr-3">Ver</button>
            <button class="text-[10px] font-semibold text-emerald-600 hover:text-emerald-800 transition-colors">Validar</button>
          </td>
        </tr>
      `;
    }).join('');

    // Actualizar KPI validaciones pendientes
    const pendientes = estudiantes.filter((_, i) => estados[i % estados.length] === 'Pendiente').length;
    document.getElementById('kpiValidaciones').textContent = pendientes;

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="px-5 py-8 text-center text-sm text-slate-300">No tienes permisos para ver esta sección</td></tr>`;
    document.getElementById('kpiValidaciones').textContent = '—';
  }
}

// ══════════════════════════════════════
// GRÁFICA DE BARRAS
// ══════════════════════════════════════
function inicializarGrafica() {
  const ctx = document.getElementById('chartPasantias').getContext('2d');

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN'],
      datasets: [
        {
          label: 'Completadas',
          data: [65, 120, 95, 180, 145, 210],
          backgroundColor: '#0d1b2e',
          borderRadius: 6,
          borderSkipped: false,
        },
        {
          label: 'En progreso',
          data: [40, 80, 60, 110, 95, 130],
          backgroundColor: '#cbd5e1',
          borderRadius: 6,
          borderSkipped: false,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0d1b2e',
          titleFont: { family: 'Syne', size: 11 },
          bodyFont:  { family: 'DM Sans', size: 11 },
          padding: 10,
          cornerRadius: 8,
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { family: 'DM Sans', size: 10 }, color: '#94a3b8' }
        },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: { font: { family: 'DM Sans', size: 10 }, color: '#94a3b8' },
          border: { display: false }
        }
      },
      barPercentage: 0.6,
      categoryPercentage: 0.7,
    }
  });
}

// ══════════════════════════════════════
// NAVEGACIÓN SIDEBAR
// ══════════════════════════════════════
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    // Aquí puedes agregar navegación a otras páginas según data-page
  });
});

// ══════════════════════════════════════
// INICIALIZAR TODO
// ══════════════════════════════════════
document.addEventListener('DOMContentLoaded', async () => {
  await cargarUsuario();
  await cargarKPIs();
  cargarActividadReciente();
  await cargarTablaValidaciones();
  inicializarGrafica();
});
