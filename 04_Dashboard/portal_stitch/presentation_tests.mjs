// Unit tests only: no browser, no simulated chart results.
import {strict as assert} from 'node:assert';
import {writeFile} from 'node:fs/promises';
import {dateLabel, filterParams, clearedValues, exactNumber} from './static/js/ui_helpers.js';
const results = [];
function test(name, fn) {try {fn();results.push({prueba:name,estado:'APROBADO'});} catch(e) {results.push({prueba:name,estado:'FALLO',error:e.message});}}
test('Periodo completo con meses escritos',()=>assert.equal(`${dateLabel('2009-12-01')} — ${dateLabel('2011-12-09')}`,'1 dic 2009 — 9 dic 2011'));
test('Día y mes ambiguos se distinguen',()=>{assert.equal(dateLabel('2010-04-03'),'3 abr 2010');assert.equal(dateLabel('2010-03-04'),'4 mar 2010');});
test('Fecha bisiesta sin conversión de zona horaria',()=>assert.equal(dateLabel('2012-02-29'),'29 feb 2012'));
test('Los doce meses escritos',()=>['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'].forEach((m,i)=>assert.equal(dateLabel(`2010-${String(i+1).padStart(2,'0')}-01`),`1 ${m} 2010`)));
test('Entrada vacía se identifica como pendiente',()=>assert.equal(dateLabel(''),'Fecha pendiente'));
test('URL enviada conserva fechas ISO sin intercambio',()=>{const p=filterParams({start:'2010-04-03',end:'2010-04-09'},new Map());const u=new URL('http://localhost/api/data?'+p);assert.equal(u.searchParams.get('start'),'2010-04-03');assert.equal(u.searchParams.get('end'),'2010-04-09');});
test('Limpieza conserva extremos ISO',()=>{const v=clearedValues({minimum:'2009-12-01',maximum:'2011-12-09'});assert.equal(v.start,'2009-12-01');assert.equal(v.end,'2011-12-09');});
test('Cuatro decimales conservados al presentar',()=>assert.equal(exactNumber('-1465677.2300',4),'-1 465 677,2300'));
const report={fecha:new Date().toISOString(),alcance:'Pruebas unitarias JavaScript; no revisión visual',aprobadas:results.filter(r=>r.estado==='APROBADO').length,total:results.length,resultados:results};
await writeFile(new URL('../../06_Pruebas_y_Evidencias/portal_presentacion_js.json',import.meta.url),JSON.stringify(report,null,2));
export default report;
