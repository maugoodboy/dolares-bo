// ==========================================
// 1. CONFIGURACIÓN DE ENTIDADES Y COLORES
// ==========================================
const entidades = [
  { id: 'oficial', nombre: 'Banco Central de Bolivia (BCB)', color: '#002B49', domain: 'https://www.bcb.gob.bo/', iniciales: 'BCB' },
  { id: 'banco_union', nombre: 'Banco Unión', color: '#003A70', domain: 'https://www.bancounion.com.bo', iniciales: 'BU' },
  { id: 'bnb', nombre: 'Banco Nacional de Bolivia (BNB)', color: '#00853F', domain: 'https://www.bnb.com.bo/PortalBNB/Principal/BancaPersonas', iniciales: 'BNB' },
  { id: 'bmsc', nombre: 'Banco Mercantil Santa Cruz (BMSC)', color: '#F37021', domain: 'https://www.bmsc.com.bo/', iniciales: 'BMSC' },
  { id: 'bisa', nombre: 'Banco BISA', color: '#FFD100', domain: 'https://www.bisa.com/home', iniciales: 'BIS' },
  { id: 'ganadero', nombre: 'Banco Ganadero', color: '#CC0000', domain: 'https://www.bg.com.bo', iniciales: 'BG' },
  { id: 'bancosol', nombre: 'Banco Sol', color: '#E4007D', domain: 'https://www.bancosol.com.bo', iniciales: 'SOL' },
  { id: 'ecofuturo', nombre: 'Banco Ecofuturo', color: '#689F38', domain: 'https://www.bancoecofuturo.com.bo/', iniciales: 'ECO' },
  { id: 'baneco', nombre: 'Banco Económico', color: '#ED1C24', domain: 'https://www.baneco.com.bo', iniciales: 'BEC' },
  { id: 'bco', nombre: 'Banco de la Comunidad', color: '#1B5E20', domain: 'https://www.bco.com.bo/', iniciales: 'BCO' },
  { id: 'bcp', nombre: 'Banco de Crédito Bolivia (BCP)', color: '#002A61', domain: 'https://www.bcp.com.bo', iniciales: 'BCP' },
  { id: 'prodem', nombre: 'Banco Prodem', color: '#007A33', domain: 'https://www.prodem.bo/Inicio', iniciales: 'PRD' },
  { id: 'fie', nombre: 'Banco FIE', color: '#E2001A', domain: 'https://www.bancofie.com.bo/', iniciales: 'FIE' },
  { id: 'fortaleza', nombre: 'Banco Fortaleza', color: '#004B87', domain: 'https://www.bancofortaleza.com.bo/', iniciales: 'FOR' },
  { id: 'binance', nombre: 'Binance (USDT-P2P)', color: '#F3BA2F', domain: 'https://p2p.binance.com/', iniciales: 'BIN' }
];

let chartIndividual = null;
let chartComparativo = null;
let opIndividual = 'compra';
let rangoIndividual = 0;
let opComparativo = 'compra';
let rangoComparativo = 0;

// ==========================================
// 2. NAVEGACIÓN ENTRE PESTAÑAS
// ==========================================
function cambiarPagina(idPagina, btn) {
  document.querySelectorAll('.page-section').forEach(sec => sec.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

  document.getElementById(`pag-${idPagina}`).classList.add('active');
  btn.classList.add('active');

  if (idPagina === 'historico' && !chartIndividual) {
    inicializarGraficoIndividual();
  } else if (idPagina === 'comparativo') {
    if (!chartComparativo) {
      inicializarGraficoComparativo();
    } else {
      actualizarGraficoComparativo();
    }
  }
}

// ==========================================
// 3. LECTURA Y PROCESAMIENTO DE CSV
// ==========================================
function formatearFechaYHora(timestampStr) {
  if (!timestampStr) return { fecha: '—', hora: '—' };
  const partes = timestampStr.trim().split(' ');
  if (partes.length >= 2) {
    return { fecha: partes[0], hora: partes[1].substring(0, 5) };
  }
  return { fecha: timestampStr, hora: '—' };
}

async function leerUltimaFila(rutaCsv) {
  try {
    const res = await fetch(rutaCsv + '?t=' + Date.now());
    if (!res.ok) return { valor: '—', fecha: '—', hora: '—' };

    const texto = await res.text();
    const filas = texto.trim().split('\n').filter(l => l.trim() !== '');
    if (filas.length <= 1) return { valor: '—', fecha: '—', hora: '—' };

    const indiceColumna = rutaCsv.includes('binance') ? 3 : 1;
    const columnas = filas[filas.length - 1].split(',');

    const { fecha, hora } = formatearFechaYHora(columnas[0] ? columnas[0].trim() : '');
    const valor = columnas[indiceColumna] ? columnas[indiceColumna].trim() : '—';

    return { valor, fecha, hora };
  } catch (e) {
    return { valor: '—', fecha: '—', hora: '—' };
  }
}

async function leerTodoElCsv(rutaCsv) {
  try {
    const res = await fetch(rutaCsv + '?t=' + Date.now());
    if (!res.ok) return [];

    const texto = await res.text();
    const filas = texto.trim().split('\n').filter(l => l.trim() !== '');
    if (filas.length <= 1) return [];

    const indiceColumna = rutaCsv.includes('binance') ? 3 : 1;
    const datos = [];

    for (let i = 1; i < filas.length; i++) {
      const col = filas[i].split(',');
      if (col.length > indiceColumna) {
        const dateObj = new Date(col[0].trim().replace(' ', 'T'));
        const valor = parseFloat(col[indiceColumna]);
        if (!isNaN(dateObj) && !isNaN(valor)) {
          datos.push({ x: dateObj, y: valor });
        }
      }
    }
    return datos;
  } catch (e) {
    return [];
  }
}

function aplicarFiltroRango(datos, rango) {
  if (rango === 0 || !datos.length) return datos;
  const limite = new Date();
  limite.setDate(limite.getDate() - rango);
  return datos.filter(d => d.x >= limite);
}

// ==========================================
// 4. CARGA DE TABLA DE COTIZACIONES
// ==========================================
async function cargarTabla() {
  const cuerpo = document.getElementById('cotizaciones-cuerpo');
  cuerpo.innerHTML = '';

  for (const banco of entidades) {
    const logoUrl = `https://www.google.com/s2/favicons?domain=${banco.domain}&sz=128`;
    const fila = document.createElement('tr');
    fila.innerHTML = `
      <td class="col-logo">
        <a href="${banco.domain}" target="_blank" rel="noopener noreferrer" class="logo-link" title="${banco.nombre}">
          <img src="${logoUrl}" alt="${banco.nombre}" class="entity-logo"
               onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-flex';">
          <span class="entity-logo-fallback" style="display: none; background-color: ${banco.color};">
            ${banco.iniciales}
          </span>
        </a>
      </td>
      <td class="bank-name">${banco.nombre}</td>
      <td class="num rate" id="c-${banco.id}">...</td>
      <td class="num rate" id="v-${banco.id}">...</td>
      <td class="num date-col" id="f-${banco.id}">...</td>
      <td class="num date-col" id="h-${banco.id}">...</td>
    `;
    cuerpo.appendChild(fila);

    Promise.all([
      leerUltimaFila(`./${banco.id}/compra.csv`),
      leerUltimaFila(`./${banco.id}/venta.csv`)
    ]).then(([compra, venta]) => {
      const elCompra = document.getElementById(`c-${banco.id}`);
      const elVenta = document.getElementById(`v-${banco.id}`);
      const elFecha = document.getElementById(`f-${banco.id}`);
      const elHora = document.getElementById(`h-${banco.id}`);

      // Fortaleza y Fie muestran "-" en compra y venta
      if (banco.id === 'fortaleza' || banco.id === 'fie') {
        elCompra.textContent = '-';
        elVenta.textContent = '-';
      } else {
        if (banco.id === 'oficial' || banco.id === 'ganadero') {
          elCompra.textContent = '—';
        } else {
          elCompra.textContent = compra.valor !== '-' ? compra.valor : '—';
        }
        elVenta.textContent = venta.valor !== '-' ? venta.valor : '—';
      }

      elFecha.textContent = venta.fecha !== '—' ? venta.fecha : compra.fecha;
      elHora.textContent = venta.hora !== '—' ? venta.hora : compra.hora;
    });
  }
}

// ==========================================
// 5. GRÁFICO INDIVIDUAL
// ==========================================
function popularSelectBancos() {
  const select = document.getElementById('select-banco');
  select.innerHTML = '';
  entidades.forEach(e => {
    const opt = document.createElement('option');
    opt.value = e.id;
    opt.textContent = e.nombre;
    select.appendChild(opt);
  });
  select.value = 'binance';
}

function inicializarGraficoIndividual() {
  popularSelectBancos();
  const ctx = document.getElementById('canvasHistorico').getContext('2d');

  chartIndividual = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [{
        label: 'Cotización (Bs)',
        data: [],
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.08)',
        borderWidth: 2,
        pointRadius: 0,
        fill: true,
        tension: 0.2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: 'time',
          time: { unit: 'day', displayFormats: { day: 'dd/MM' } },
          grid: { color: 'rgba(226, 232, 240, 0.6)' }
        },
        y: {
          min: 6,
          grid: { color: 'rgba(226, 232, 240, 0.6)' },
          ticks: { font: { family: 'Inter', size: 11 } }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` Bs. ${ctx.parsed.y.toFixed(2)}`
          }
        }
      }
    }
  });

  actualizarGraficoIndividual();
}

async function actualizarGraficoIndividual() {
  if (!chartIndividual) return;
  const bancoId = document.getElementById('select-banco').value;
  const bancoObj = entidades.find(e => e.id === bancoId);

  const ruta = bancoId === 'oficial' ? './oficial/compra.csv' : `./${bancoId}/${opIndividual}.csv`;
  let datos = await leerTodoElCsv(ruta);
  datos = aplicarFiltroRango(datos, rangoIndividual);

  chartIndividual.data.datasets[0].data = datos;
  chartIndividual.data.datasets[0].borderColor = bancoObj ? bancoObj.color : '#2563eb';
  chartIndividual.update();
}

function setTipoOperacionInd(tipo) {
  opIndividual = tipo;
  document.getElementById('btn-ind-compra').classList.toggle('active', tipo === 'compra');
  document.getElementById('btn-ind-venta').classList.toggle('active', tipo === 'venta');
  actualizarGraficoIndividual();
}

function setRangoInd(rango, btn) {
  rangoIndividual = rango;
  document.querySelectorAll('.btn-rango-ind').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  actualizarGraficoIndividual();
}

// ==========================================
// 6. GRÁFICO COMPARATIVO
// ==========================================
function inicializarGraficoComparativo() {
  const ctx = document.getElementById('canvasComparativo').getContext('2d');

  chartComparativo = new Chart(ctx, {
    type: 'line',
    data: { datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: 'time',
          time: { unit: 'day', displayFormats: { day: 'dd/MM' } },
          grid: { color: 'rgba(226, 232, 240, 0.6)' }
        },
        y: {
          min: 6,
          grid: { color: 'rgba(226, 232, 240, 0.6)' },
          ticks: { font: { family: 'Inter', size: 11 } }
        }
      },
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, font: { family: 'Inter', size: 11 } } }
      }
    }
  });

  actualizarGraficoComparativo();
}

async function actualizarGraficoComparativo() {
  if (!chartComparativo) return;

  const promesas = entidades.map(async (entidad) => {
    const ruta = entidad.id === 'oficial' ? './oficial/compra.csv' : `./${entidad.id}/${opComparativo}.csv`;
    let datos = await leerTodoElCsv(ruta);
    datos = aplicarFiltroRango(datos, rangoComparativo);

    return {
      label: entidad.nombre,
      data: datos,
      borderColor: entidad.color,
      backgroundColor: 'transparent',
      borderWidth: entidad.id === 'oficial' ? 3 : 1.8,
      pointRadius: 0,
      tension: 0.1
    };
  });

  chartComparativo.data.datasets = await Promise.all(promesas);
  chartComparativo.update();
}

function setTipoOperacionComp(tipo) {
  opComparativo = tipo;
  document.getElementById('btn-comp-compra').classList.toggle('active', tipo === 'compra');
  document.getElementById('btn-comp-venta').classList.toggle('active', tipo === 'venta');
  actualizarGraficoComparativo();
}

function setRangoComp(rango, btn) {
  rangoComparativo = rango;
  document.querySelectorAll('.btn-rango-comp').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  actualizarGraficoComparativo();
}

// Iniciar cargando la tabla al abrir la página
cargarTabla();
