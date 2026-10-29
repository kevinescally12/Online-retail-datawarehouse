"""Focused read-only QA: real SSAS, Flask routes, source invariants; no browser."""
import csv
import hashlib
import io
import json
import re
from datetime import datetime
from pathlib import Path
from server import create_app
from shared import totals

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '06_Pruebas_y_Evidencias'
results = []
def check(name, assertion, **details):
    results.append(dict(prueba=name, estado='APROBADO' if assertion else 'FALLO', **details))

app = create_app()
client = app.test_client()
analytics = app.extensions['analytics']
args = dict(start='2010-04-03', end='2010-04-09', group='Mes', metric='Importe')
cat, filters, _, _ = analytics.filters(args)
check('Backend interpreta 3 a 9 de abril, no marzo/septiembre',
      (filters.start.year,filters.start.month,filters.start.day)==(2010,4,3) and
      (filters.end.year,filters.end.month,filters.end.day)==(2010,4,9), inicio=str(filters.start), fin=str(filters.end))
mdx = totals(cat, filters)
check('MDX existente recibe las siete fechas de abril sin intercambio',
      all(f'.&[201004{day:02d}]' in mdx for day in range(3,10)) and '.&[20100304]' not in mdx, mdx=mdx)
response = client.get('/api/data', query_string=args)
payload = response.get_json()
check('Consulta real SSAS: periodo aplicado coincide con ISO enviado', response.status_code==200 and
      payload.get('period')==dict(start=args['start'],end=args['end']), http=response.status_code,
      periodo=payload.get('period'), totales=payload.get('totals'))
(OUT/'portal_presentacion_respuesta_real.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
response = client.get('/api/export.csv',query_string=args)
data = response.data
(OUT/'portal_presentacion_exportacion_real.csv').write_bytes(data)
rows = list(csv.reader(io.StringIO(data.decode('utf-8-sig')),delimiter=','))
header = next((i for i,row in enumerate(rows) if 'Importe' in row),None)
values = [] if header is None else [r[rows[header].index('Importe')] for r in rows[header+1:] if len(r)==len(rows[header])]
check('CSV real mantiene cuatro decimales', response.status_code==200 and bool(values) and
      all(re.fullmatch(r'-?\d+[.,]\d{4}',v) for v in values), importes=values)
html=client.get('/section/analytics').get_data(as_text=True)
check('Una navegación lateral y alternativa móvil accesible',html.count('aria-label="Secciones"')==1 and
      'class="tabbar"' not in html and 'aria-controls="sidebar"' in html and 'aria-label="Abrir navegación"' in html)
check('Formato y fechas legibles asociados a ambos controles',all(s in html for s in
      ['AAAA-MM-DD (año-mes-día)','date-format-hint start-readable','date-format-hint end-readable']))
css=(Path(__file__).parent/'static/css/portal.css').read_text(encoding='utf-8')
check('Estático: barra opaca, apilamiento y separación adaptable',
      'z-index:1030;background:#fff;isolation:isolate' in css and
      'padding:calc(var(--topbar-height) + 16px)' in css and 'rgba(255,255,255,.97)' not in css and
      '@media(max-width:575px)' in css and '@media(max-width:991px)' in css)
before=json.loads((OUT/'portal_presentacion_antes.json').read_text(encoding='utf-8-sig'))
for row in before:
    actual=hashlib.sha256((ROOT/row['Archivo']).read_bytes()).hexdigest().upper()
    check('Sin cambios: '+row['Archivo'],actual==row['SHA256'],sha256=actual)
report=dict(fecha=datetime.now().astimezone().isoformat(),alcance='SSAS real y cliente Flask; revisión estática CSS/HTML. Sin navegador, sin mocks.',
            aprobadas=sum(r['estado']=='APROBADO' for r in results),total=len(results),resultados=results,
            observacion_fuera_de_alcance={'intervalo':args,'importe_tarjeta':payload.get('totals',{}).get('Importe'),
              'importe_filas_mensuales_csv':values,'nota':'La fila mensual real no coincide con la tarjeta del intervalo parcial. La recepción ISO y las fechas MDX son correctas. No se alteraron consultas; requiere investigación separada del cruce Mes/Fecha en SSAS.'})
(OUT/'portal_presentacion_pruebas.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(any(r['estado']=='FALLO' for r in results))
