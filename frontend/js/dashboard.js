const API_URL =
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000/api/v1'
    : `${window.location.origin}/api/v1`;


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

if (!getToken()) {
  window.location.href = 'login.html';
}


function cerrarSesion() {
  localStorage.removeItem('token');
  sessionStorage.removeItem('token');

  window.location.href = 'login.html';
}


window.userRol = null;
window.currentUser = null;


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


    window.currentUser = user;
    window.userRol = user.rol;

  
    const primerNombre =
      user.nombre?.split(' ')[0] || 'Usuario';


    const rolesES = {
      coordinador: 'Coordinador',
      tutor: 'Tutor Académico',
      estudiante: 'Estudiante',
      supervisor: 'Supervisor',
    };

    const rolLabel =
      rolesES[user.rol] || user.rol;


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


    if (topbarAvatar) {
      const iniciales = user.nombre
        .split(' ')
        .slice(0, 2)
        .map(n => n[0])
        .join('')
        .toUpperCase();

      topbarAvatar.textContent = iniciales;
    }


    ajustarVistaPorRol(user.rol);

  } catch (err) {
    console.error(err);
  }
}


function ajustarVistaPorRol(rol) {

  const ocultarMenu = (page) => {
    const el = document.querySelector(`[data-page="${page}"]`);
    if (el) el.style.display = 'none';
  };

  const ocultarEl = (id) => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  };


  if (rol === 'coordinador') {

    return;
  }


  if (rol === 'tutor') {
    ocultarMenu('usuarios');
    ocultarMenu('empresas');

    ocultarKPIsAdmin();
    return;
  }

 
  if (rol === 'supervisor') {
    ocultarMenu('usuarios');
    ocultarMenu('empresas');
    ocultarMenu('reportes');
    ocultarMenu('log');

    ocultarKPIsAdmin();
    return;
  }


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


async function cargarKPIs() {
  try {
    const rol = window.userRol;

    // KPI Pasantías activas: solo coordinador/tutor
    const resUsuarios = await fetch(`${API_URL}/usuarios/`, { headers: authHeaders() });
    if (resUsuarios.ok) {
      const usuarios = await resUsuarios.json();
      const estudiantes = usuarios.filter(u => u.rol === 'estudiante');
      const el = document.getElementById('kpiPasantias');
      if (el) el.textContent = estudiantes.length.toLocaleString('es-CO');
    }

    // KPI Horas acumuladas: datos reales según el rol
    const kpiHoras = document.getElementById('kpiHoras');
    if (kpiHoras) {
      if (rol === 'coordinador') {
        const resDash = await fetch(`${API_URL}/coordinador/dashboard`, { headers: authHeaders() });
        if (resDash.ok) {
          // El dashboard del coordinador no devuelve horas totales directamente;
          // se muestra la cantidad de prácticas activas como referencia
          const dash = await resDash.json();
          kpiHoras.textContent = dash.total_practicas_activas + ' activas';
        }
      } else if (rol === 'tutor') {
        const resDash = await fetch(`${API_URL}/tutor/dashboard`, { headers: authHeaders() });
        if (resDash.ok) {
          const dash = await resDash.json();
          kpiHoras.textContent = (dash.total_horas_validadas || 0).toLocaleString('es-CO') + 'h';
        }
      } else if (rol === 'estudiante') {
        const resDash = await fetch(`${API_URL}/estudiante/dashboard`, { headers: authHeaders() });
        if (resDash.ok) {
          const dash = await resDash.json();
          kpiHoras.textContent = (dash.horas_acumuladas || 0).toLocaleString('es-CO') + 'h';
        }
      }
    }

  } catch (err) {
    console.error(err);
  }
}


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


async function cargarTablaValidaciones() {
  const tbody = document.getElementById('tablaValidaciones');
  if (!tbody) return;

  const rol = window.userRol;

  // Solo tutor, supervisor y coordinador ven seguimientos pendientes de validación
  if (!['coordinador', 'tutor', 'supervisor'].includes(rol)) {
    tbody.innerHTML = `<tr><td colspan="6" class="px-5 py-8 text-center text-slate-400">No aplica para tu rol</td></tr>`;
    return;
  }

  try {
    // Elegir el endpoint de pendientes según el rol
    let endpointPendientes;
    if (rol === 'tutor') endpointPendientes = `${API_URL}/tutor/pendientes`;
    else if (rol === 'supervisor') endpointPendientes = `${API_URL}/supervisor/pendientes`;
    else endpointPendientes = `${API_URL}/coordinador/dashboard`;  // coordinador usa dashboard

    let seguimientos = [];

    if (rol === 'coordinador') {
      // Para el coordinador, mostrar todos los seguimientos pendientes globales
      // obtenidos desde el dashboard
      const resDash = await fetch(endpointPendientes, { headers: authHeaders() });
      if (resDash.ok) {
        const dash = await resDash.json();
        const kpi = document.getElementById('kpiValidaciones');
        if (kpi) kpi.textContent = dash.seguimientos_pendientes;
      }
      // Cargar practicas para listar seguimientos
      const resPracticas = await fetch(`${API_URL}/practicas/`, { headers: authHeaders() });
      if (resPracticas.ok) {
        const practicas = await resPracticas.json();
        for (const p of practicas.slice(0, 20)) {
          const resSeg = await fetch(`${API_URL}/seguimientos/practica/${p.id}`, { headers: authHeaders() });
          if (resSeg.ok) {
            const segs = await resSeg.json();
            seguimientos.push(...segs.filter(s => s.estado === 'enviado').map(s => ({ ...s, _practica: p })));
          }
        }
      }
    } else {
      const res = await fetch(endpointPendientes, { headers: authHeaders() });
      if (!res.ok) throw new Error('Sin acceso');
      seguimientos = await res.json();
      const kpi = document.getElementById('kpiValidaciones');
      if (kpi) kpi.textContent = seguimientos.length;
    }

    if (seguimientos.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="px-5 py-8 text-center text-slate-400">No hay seguimientos pendientes de validación</td></tr>`;
      return;
    }

    const coloresEstado = {
      enviado:  'bg-amber-100 text-amber-700',
      aprobado: 'bg-green-100 text-green-700',
      rechazado:'bg-red-100 text-red-700',
      borrador: 'bg-slate-100 text-slate-600',
    };

    tbody.innerHTML = seguimientos.map(s => {
      const practica = s._practica || null;
      const estudianteNombre = practica?.estudiante?.nombre || 'Estudiante';
      const empresaNombre   = practica?.empresa?.nombre   || 'Empresa';
      const estadoLabel = s.estado.charAt(0).toUpperCase() + s.estado.slice(1);
      const colorClase  = coloresEstado[s.estado] || 'bg-slate-100 text-slate-600';
      const fecha = s.fecha_actividad ? new Date(s.fecha_actividad).toLocaleDateString('es-CO') : '—';

      return `
      <tr class="border-b hover:bg-slate-50 transition-colors">
        <td class="px-5 py-3"><input type="checkbox" data-id="${s.id}"></td>
        <td class="px-3 py-3">
          <div class="font-medium">${estudianteNombre}</div>
          <div class="text-xs text-slate-400">${fecha} · ${s.horas_realizadas}h</div>
        </td>
        <td class="px-3 py-3 text-sm">${s.descripcion.slice(0, 50)}${s.descripcion.length > 50 ? '…' : ''}</td>
        <td class="px-3 py-3 text-sm">${empresaNombre}</td>
        <td class="px-3 py-3">
          <span class="${colorClase} px-2 py-1 rounded-full text-xs">${estadoLabel}</span>
        </td>
        <td class="px-3 py-3 flex gap-2">
          <button class="text-blue-600 text-xs hover:underline" onclick="verSeguimiento('${s.id}')">Ver</button>
          ${['coordinador','tutor'].includes(rol) ? `
          <button class="text-emerald-600 text-xs hover:underline" onclick="aprobarSeguimiento('${s.id}')">Aprobar</button>
          <button class="text-red-500 text-xs hover:underline"     onclick="rechazarSeguimiento('${s.id}')">Rechazar</button>
          ` : ''}
        </td>
      </tr>`;
    }).join('');

  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-slate-400">No tienes permisos para ver esta sección</td></tr>`;
  }
}

// Acciones de validación desde la tabla
async function aprobarSeguimiento(id) {
  await _validarSeguimiento(id, 'aprobado');
}
async function rechazarSeguimiento(id) {
  await _validarSeguimiento(id, 'rechazado');
}
async function verSeguimiento(id) {
  alert('Seguimiento ID: ' + id);
}
async function _validarSeguimiento(id, estado) {
  try {
    const res = await fetch(`${API_URL}/seguimientos/${id}/validar`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify({ estado }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert('Error: ' + (err.detail || 'No se pudo validar'));
      return;
    }
    await cargarTablaValidaciones();
    await cargarKPIs();
  } catch (e) {
    console.error(e);
  }
}


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


document.addEventListener(
  'DOMContentLoaded',
  async () => {


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

    mostrarSeccion('dashboard');
  }
);