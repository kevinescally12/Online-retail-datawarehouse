// Pruebas unitarias de JavaScript. No abre navegador ni sustituye datos del cubo.
import {writeFile} from 'node:fs/promises';
import {strict as assert} from 'node:assert';
const helpers = await import(new URL('./static/js/ui_helpers.js', import.meta.url).href);
const results = [];
function test(name, fn) {try {fn(); results.push({prueba:name,estado:'APROBADO'});} catch(error) {results.push({prueba:name,estado:'FALLO',error:error.message});}}
test('Decimal exacto de importes, sin pasar por Number', () => assert.equal(helpers.exactNumber('18909762.118',4),'18 909 762,1180'));
test('Cancelación conserva el signo', () => assert.equal(helpers.exactNumber('-1465677.2300',4),'-1 465 677,2300'));
test('Texto decimal superior al límite entero seguro de JS', () => assert.equal(helpers.exactNumber('9007199254740993.1234',4),'9 007 199 254 740 993,1234'));
test('Ausencia y cero no se confunden', () => {assert.equal(helpers.exactNumber(null,4),'—');assert.equal(helpers.exactNumber('0',4),'0,0000');});
test('Limpieza restaura periodo, cuatro filtros y controles', () => assert.deepEqual(helpers.clearedValues({minimum:'2009-12-01',maximum:'2011-12-09'}),{start:'2009-12-01',end:'2011-12-09',country:'',productLabel:'',type:'',group:'Mes',metric:'Importe'}));
test('Producto exige selección exacta del catálogo', () => assert.throws(() => helpers.filterParams({start:'2010-01-01',end:'2010-02-01',productLabel:'Texto arbitrario'},new Map())));
test('Filtros combinados se codifican sin concatenar MDX', () => {const p=helpers.filterParams({start:'2010-12-01',end:'2010-12-31',country:'[Pais].[Pais].&[6]',type:'[TipoOperacion].[TipoOperacion].&[1]',productLabel:'00123 · Descripción · Por clasificar',group:'Código de producto',metric:'Importe'},new Map([['00123 · Descripción · Por clasificar','[Producto].[Producto].&[9]']]));assert.equal(p.get('product'),'[Producto].[Producto].&[9]');assert.equal(p.get('country'),'[Pais].[Pais].&[6]');});
test('Intervalo invertido se rechaza', () => assert.throws(() => helpers.filterParams({start:'2011-01-01',end:'2010-01-01'},new Map())));
const report = {fecha:new Date().toISOString(),alcance:'8 pruebas unitarias de funciones JavaScript con entradas de prueba; sin navegador ni datos simulados en gráficos',pruebas:results.length,aprobadas:results.filter(r=>r.estado==='APROBADO').length,resultados:results};
await writeFile(new URL('../../06_Pruebas_y_Evidencias/portal_frontend_pruebas.json', import.meta.url),JSON.stringify(report,null,2),'utf8');
export default report;
