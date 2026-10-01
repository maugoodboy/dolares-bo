// ==========================================
// 1. CONFIGURACIÓN DE ENTIDADES
// ==========================================
const entidades = [
  { id: 'oficial', nombre: 'Banco Central de Bolivia (BCB)', color: '#002B49', domain: 'https://www.bcb.gob.bo/', iniciales: 'BCB' },
  { id: 'banco_union', nombre: 'Banco Unión', color: '#003A70', domain: 'https://www.bancounion.com.bo', iniciales: 'BU' },
  { id: 'bnb', nombre: 'Banco Nacional de Bolivia (BNB)', color: '#00853F', domain: 'https://www.bnb.com.bo/PortalBNB/Principal/BancaPersonas', iniciales: 'BNB' },
  { id: 'bmsc', nombre: 'Banco Mercantil Santa Cruz (BMSC)', color: '#F37021', domain: 'https://www.bmsc.com.bo/', iniciales: 'BMSC' },
  { id: 'bisa', nombre: 'Banco BISA', color: '#D97706', domain: 'https://www.bisa.com/home', iniciales: 'BIS' },
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

let datosCargados = []; // Memoria de datos obtenidos
let tipoOperacionLollipop = 'venta';

// ==========================================
// 2. NAVEGACIÓN ENTRE PESTAÑAS
// ==========================================
function cambiarPagina(idPagina, btn) {
  document.querySelectorAll('.page-section').forEach(sec => sec.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

  document.getElementById(`pag-${idPagina}`).classList.add('active');
  btn.classList.add('active');

  if (idPagina === 'lollipop') {
    renderizarLollipop();
  }
}

// ==========================================
// 3. LECTURA Y PROCESAMIENTO DE CSV
// ==========================================
function formatearFechaYHora(timestampStr) {
  if (!timestampStr) return { fecha: '—', hora: '—' };
  const str = timestampStr.trim();
  const partes = str.split(' ');
  if (partes.length >= 2) {
    return { fecha: partes[0], hora: partes[1].substring(0, 5) };
  }
  if (str.includes('T')) {
    const subPartes = str.split('T');
    return {
      fecha: subPartes[0],
      hora: (subPartes[1] || '').substring(0, 5) || '—'
    };
  }
  return { fecha: str, hora: '—' };
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

// ==========================================
// 4. CARGA DE TABLA DE DATOS
// ==========================================
async function cargarTabla() {
  const cuerpo = document.getElementById('cotizaciones-cuerpo');
  cuerpo.innerHTML = '';
  datosCargados = [];

  const promesas = entidades.map(async (banco) => {
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

    const [compra, venta] = await Promise.all([
      leerUltimaFila(`./${banco.id}/compra.csv`),
      leerUltimaFila(`./${banco.id}/venta.csv`)
    ]);

    const elCompra = document.getElementById(`c-${banco.id}`);
    const elVenta = document.getElementById(`v-${banco.id}`);
    const elFecha = document.getElementById(`f-${banco.id}`);
    const elHora = document.getElementById(`h-${banco.id}`);

    const valorCompraNum = parseFloat(String(compra.valor).trim().replace(',', '.'));
    const valorVentaNum = parseFloat(String(venta.valor).trim().replace(',', '.'));

    if (banco.id === 'oficial' || banco.id === 'ganadero') {
      elCompra.textContent = '—';
    } else {
      elCompra.textContent = !isNaN(valorCompraNum) ? valorCompraNum.toFixed(2) : (compra.valor !== '-' ? compra.valor : '—');
    }

    elVenta.textContent = !isNaN(valorVentaNum) ? valorVentaNum.toFixed(2) : (venta.valor !== '-' ? venta.valor : '—');
    elFecha.textContent = venta.fecha !== '—' ? venta.fecha : compra.fecha;
    elHora.textContent = venta.hora !== '—' ? venta.hora : compra.hora;

    // Guardar los datos para usarlos en el gráfico Lollipop
    datosCargados.push({
      banco,
      logoUrl,
      compra: !isNaN(valorCompraNum) && banco.id !== 'ganadero' ? valorCompraNum : null,
      venta: !isNaN(valorVentaNum) ? valorVentaNum : null,
      fecha: venta.fecha !== '—' ? venta.fecha : compra.fecha
    });
  });

  await Promise.all(promesas);
}

// ==========================================
// 5. CONTROL Y RENDERIZADO DEL GRÁFICO LOLLIPOP
// ==========================================
function setTipoOperacionLollipop(tipo) {
  tipoOperacionLollipop = tipo;
  document.getElementById('btn-lol-compra').classList.toggle('active', tipo === 'compra');
  document.getElementById('btn-lol-venta').classList.toggle('active', tipo === 'venta');
  document.getElementById('lollipop-titulo').textContent = `Cotizaciones de ${tipo} por entidad`;
  renderizarLollipop();
}

function renderizarLollipop() {
  const contenedor = document.getElementById('lollipop-chart-container');
  const spanFecha = document.getElementById('lollipop-fecha');
  if (!contenedor) return;

  contenedor.innerHTML = '';

  // Filtrar entidades que tengan cotización válida (excluyendo el BCB del ranking comercial)
  const items = datosCargados
    .filter(item => item.banco.id !== 'oficial' && item[tipoOperacionLollipop] !== null && !isNaN(item[tipoOperacionLollipop]))
    .map(item => ({
      banco: item.banco,
      logoUrl: item.logoUrl,
      valor: item[tipoOperacionLollipop],
      fecha: item.fecha
    }));

  if (!items.length) {
    contenedor.innerHTML = '<div class="lollipop-empty">No hay datos disponibles para esta operación.</div>';
    return;
  }

  // Ordenar de menor a mayor cotización
  items.sort((a, b) => a.valor - b.valor);

  if (spanFecha) {
    spanFecha.textContent = items[0].fecha || '';
  }

  const minVal = items[0].valor;
  const maxVal = items[items.length - 1].valor;
  const midVal = (minVal + maxVal) / 2;
  const margen = (maxVal - minVal) === 0 ? 1 : (maxVal - minVal);

  // Actualizar solo las marcas numéricas de referencia (mínimo, medio, máximo)
  const elMin = document.getElementById('scale-min');
  const elMid = document.getElementById('scale-mid');
  const elMax = document.getElementById('scale-max');

  if (elMin) elMin.textContent = `${minVal.toFixed(2)} Bs`;
  if (elMid) elMid.textContent = `${midVal.toFixed(2)} Bs`;
  if (elMax) elMax.textContent = `${maxVal.toFixed(2)} Bs`;

  items.forEach(item => {
    // Cálculo porcentual del punto (entre 6% y 95%)
    const pct = 6 + ((item.valor - minVal) / margen) * 88;

    const row = document.createElement('div');
    row.className = 'lollipop-row';
    row.innerHTML = `
      <div class="lollipop-val" style="color: ${item.banco.color};">${item.valor.toFixed(2)}</div>
      <a href="${item.banco.domain}" target="_blank" rel="noopener noreferrer" class="lollipop-logo-wrap" title="Ir a ${item.banco.nombre}">
        <img src="${item.logoUrl}" alt="${item.banco.nombre}" class="lollipop-logo"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-flex';">
        <span class="lollipop-fallback" style="display:none; background-color:${item.banco.color}">
          ${item.banco.iniciales}
        </span>
      </a>
      <a href="${item.banco.domain}" target="_blank" rel="noopener noreferrer" class="lollipop-name" title="${item.banco.nombre}">
        ${item.banco.nombre}
      </a>
      <div class="lollipop-track">
        <div class="lollipop-line" style="width: ${pct}%; background-color: ${item.banco.color};"></div>
        <div class="lollipop-dot" style="left: ${pct}%; background-color: ${item.banco.color};" data-info="${item.banco.nombre}: ${item.valor.toFixed(2)} Bs"></div>
      </div>
    `;
    contenedor.appendChild(row);
  });
}

// Iniciar cargando la tabla de inmediato
cargarTabla();
