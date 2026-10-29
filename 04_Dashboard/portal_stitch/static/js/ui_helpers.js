export function exactNumber(value, decimals = 0) {
  if (value === null || value === undefined || value === '') return '—';
  const text = String(value);
  if (!/^-?\d+(\.\d+)?$/.test(text)) throw new Error('Formato numérico no previsto.');
  const sign = text.startsWith('-') ? '-' : '';
  const [whole, fraction = ''] = text.replace(/^-/, '').split('.');
  return sign + whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + (decimals ? ',' + fraction.padEnd(decimals, '0') : '');
}
export function dateLabel(iso) {
  // Split the ISO calendar date directly: no timezone or locale conversion.
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso));
  if (!match) return 'Fecha pendiente';
  const months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  return `${Number(match[3])} ${months[Number(match[2]) - 1]} ${match[1]}`;
}
export function filterParams(values, productMap) {
  const label = values.productLabel || '';
  if (label && !productMap.has(label)) throw new Error('Seleccione un código de producto del catálogo.');
  const params = new URLSearchParams({start: values.start, end: values.end, country: values.country || '',
    product: label ? productMap.get(label) : '', type: values.type || '', group: values.group || 'Mes', metric: values.metric || 'Importe'});
  if (!values.start || !values.end || values.start > values.end) throw new Error('Revise el intervalo de fechas.');
  return params;
}
export function clearedValues(options) {
  return {start: options.minimum, end: options.maximum, country: '', productLabel: '', type: '', group: 'Mes', metric: 'Importe'};
}
