import {exactNumber, dateLabel, filterParams, clearedValues} from './ui_helpers.js';
const $ = id => document.getElementById(id);
let options, productMap = new Map(), metric = 'Importe', busy = false;
const form = $('filters');
const chartIds = ['monthly', 'products', 'countries', 'types'];

function disableControls(disabled) {
  form.querySelectorAll('input,select,button').forEach(element => element.disabled = disabled);
  $('group').disabled = disabled;
  document.querySelectorAll('[data-metric]').forEach(button => button.disabled = disabled);
}

function message(error) {
  $('analytics-results').hidden = true;
  $('load-state').classList.add('d-none');
  $('error-state').classList.remove('d-none');
  $('error-message').textContent = error.message || 'No se pudo consultar el cubo.';
  $('connection-status').textContent = 'Consulta no completada';
  $('connection-status').className = 'status-neutral';
  $('sidebar-status').textContent = 'Sin comprobación actual correcta';
  $('export').classList.add('disabled');
  $('export').setAttribute('aria-disabled', 'true');
}
async function jsonFetch(url, signal) {
  const response = await fetch(url, {headers: {'Accept': 'application/json'}, signal});
  const payload = await response.json();
  if (!response.ok) throw new Error((payload.error || 'La consulta no terminó.') + (payload.reference ? ` Referencia: ${payload.reference}.` : ''));
  return payload;
}
function addOptions(id, rows, initial) {
  const select = $(id);
  select.replaceChildren(new Option(initial, ''));
  rows.forEach(row => select.add(new Option(row.label, row.unique)));
}
function readValues() {
  return {start: $('start').value, end: $('end').value, country: $('country').value,
    type: $('type').value, productLabel: $('product-label').value, group: $('group').value, metric};
}
function updateDateHints() {
  for (const id of ['start', 'end']) $(id + '-readable').textContent = dateLabel($(id).value);
}
function setValues(values) {
  ['start', 'end', 'country', 'type', 'group'].forEach(id => $(id).value = values[id]);
  $('product-label').value = values.productLabel;
  metric = values.metric;
  updateDateHints();
  document.querySelectorAll('[data-metric]').forEach(button => {
    const active = button.dataset.metric === metric;
    button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active));
  });
}
function table(payload) {
  const columns = [payload.group, ...(payload.group === 'Código de producto' ? ['Categoría'] : []),
    'Importe', 'Cantidad firmada', 'Conteo operaciones', 'Facturas distintas'];
  const thead = $('detail-table').querySelector('thead');
  const tbody = $('detail-table').querySelector('tbody');
  thead.replaceChildren(); tbody.replaceChildren();
  const header = document.createElement('tr');
  columns.forEach(column => {const th = document.createElement('th'); th.scope = 'col'; th.textContent = column === 'Importe' ? 'Importe (GBP)' : column; header.append(th);});
  thead.append(header);
  payload.rows.forEach(row => {
    const tr = document.createElement('tr');
    columns.forEach((column, index) => {
      const td = document.createElement('td');
      td.textContent = index < (payload.group === 'Código de producto' ? 2 : 1) ? String(row[column] ?? '') : exactNumber(row[column], column === 'Importe' ? 4 : 0);
      tr.append(td);
    }); tbody.append(tr);
  });
  $('detail-count').textContent = `${payload.rows.length} filas agregadas. Las facturas distintas no se suman entre filas. CSV con cuatro decimales.`;
}
function hasData(figure) {
  return figure.data.some(trace => (trace.values || trace.y || []).some(value => value !== null && value !== undefined));
}
async function loadData() {
  if (!options || busy) return;
  let params;
  try {params = filterParams(readValues(), productMap);} catch(error) {message(error); return;}
  busy = true; disableControls(true);
  $('analytics-results').hidden = true; $('error-state').classList.add('d-none');
  $('load-state').classList.remove('d-none'); $('load-state').querySelector('span').textContent = 'Consultando resultados agregados en Analysis Services…';
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 300000);
  try {
    const payload = await jsonFetch('/api/data?' + params.toString(), controller.signal);
    $('analytics-results').hidden = false;
    $('type-warning').hidden = !payload.type_fixed;
    $('empty-state').hidden = !(payload.empty || payload.selected_type_empty);
    $('empty-state').textContent = payload.empty ? 'No hay operaciones para esta combinación. Los valores ausentes se muestran con —.' : 'No hay operaciones del tipo seleccionado. Las tarjetas que fijan otro tipo pueden conservar valores reales.';
    document.querySelectorAll('[data-kpi]').forEach(element => element.textContent = payload.display[element.dataset.kpi] ?? '—');
    $('hero-volume').textContent = `${payload.display['Conteo operaciones']} operaciones en la selección actual.`;
    $('period-title').textContent = `Periodo aplicado: ${dateLabel(payload.period.start)} — ${dateLabel(payload.period.end)}`;
    const stamp = new Intl.DateTimeFormat('es-PE', {dateStyle: 'short', timeStyle: 'medium', timeZone: 'America/Lima'}).format(new Date(payload.checked_at));
    $('query-date').textContent = 'Consulta actual: ' + stamp;
    $('connection-status').textContent = '✓ Consulta SSAS correcta · ' + stamp;
    $('connection-status').className = 'status-current';
    $('sidebar-status').textContent = 'Consulta correcta · ' + stamp;
    $('member-counts').textContent = `${payload.counts.dates} fechas · ${payload.counts.products} miembros de producto · ${payload.counts.country_members} miembros de país (incluye especiales)`;
    $('monthly-title').textContent = payload.metric === 'Importe' ? 'Importe observado y operaciones por mes' : payload.metric === 'Cantidad firmada' ? 'Cantidad firmada y operaciones por mes' : 'Operaciones por mes';
    for (const key of chartIds) {
      const node = $('chart-' + key), figure = payload.figures[key], present = hasData(figure);
      node.hidden = !present; node.parentElement.querySelector('.chart-empty').hidden = present;
      if (present) await Plotly.react(node, figure.data, figure.layout, {responsive: true, displaylogo: false, displayModeBar: false});
      else Plotly.purge(node);
    }
    table(payload);
    const enabled = payload.rows.length > 0;
    $('export').classList.toggle('disabled', !enabled); $('export').setAttribute('aria-disabled', String(!enabled));
    $('export').href = '/api/export.csv?' + params.toString();
  } catch(error) {message(error.name === 'AbortError' ? new Error('La consulta excedió el tiempo disponible. Ajuste filtros o reintente.') : error);}
  finally {busy = false; disableControls(false); $('load-state').classList.add('d-none'); clearTimeout(timeout);}
}
async function initialize() {
  disableControls(true);
  $('error-state').classList.add('d-none'); $('load-state').classList.remove('d-none');
  try {
    options = await jsonFetch('/api/options');
    addOptions('country', options.country, 'Todos los miembros'); addOptions('type', options.type, 'Todos los tipos');
    const datalist = $('products'); datalist.replaceChildren(); productMap = new Map();
    options.product.forEach(row => {productMap.set(row.label, row.unique); const option = document.createElement('option'); option.value = row.label; datalist.append(option);});
    for (const id of ['start', 'end']) {$(id).min = options.minimum; $(id).max = options.maximum;}
    setValues(clearedValues(options)); disableControls(false); await loadData();
  } catch(error) {message(error); disableControls(false);}
}
form.addEventListener('submit', event => {event.preventDefault(); loadData();});
form.addEventListener('input', () => {updateDateHints(); $('export').classList.add('disabled'); $('export').setAttribute('aria-disabled', 'true');});
$('clear').addEventListener('click', () => {if(options && !busy) {setValues(clearedValues(options)); loadData();}});
$('retry').addEventListener('click', initialize);
$('group').addEventListener('change', loadData);
document.querySelectorAll('[data-metric]').forEach(button => button.addEventListener('click', () => {
  if (busy) return;
  metric = button.dataset.metric;
  document.querySelectorAll('[data-metric]').forEach(b => {b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button));});
  loadData();
}));
window.addEventListener('resize', () => {for(const key of chartIds) {const el = $('chart-'+key); if(el && !el.hidden && el.data) Plotly.Plots.resize(el);}});
initialize();
