"""Pruebas acotadas del portal, no una repetición de la suite del cubo."""
from contextlib import redirect_stderr, redirect_stdout
import csv
from dataclasses import replace
from datetime import datetime, date
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.request import urlopen

from server import create_app
from service import Analytics
from shared import PORTAL, DASHBOARD, EVIDENCE, CubeClient, CubeError, load_settings, totals, grouped, flat_rows, BASE
import evidence

class Assets(HTMLParser):
    def __init__(self): super().__init__(); self.urls=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag == 'script' and attrs.get('src'): self.urls.append(attrs['src'])
        if tag == 'link' and attrs.get('rel') == 'stylesheet': self.urls.append(attrs.get('href',''))

COMPARISONS=[]

class PortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analytics = Analytics()
        cls.app = create_app(cls.analytics)
        cls.http = cls.app.test_client()
        cls.catalog = cls.analytics.catalog()
        cls.default = cls.catalog.defaults()

    @classmethod
    def member(cls, dim, label):
        return next(row['unique'] for row in cls.catalog.members[dim] if row['label']==label)

    def compare(self, name, filters, params):
        # Contrato funcional anterior consultado directamente, sin reescribir sus expresiones MDX.
        expected=self.analytics.client.execute(totals(self.catalog,filters))[0]['values']
        response=self.http.get('/api/data',query_string=params)
        self.assertEqual(response.status_code,200)
        payload=response.get_json()
        for key,value in expected.items():
            actual=payload['totals'][key]
            same=(actual is None and value is None) or (actual is not None and value is not None and Decimal(str(actual))==Decimal(str(value)))
            COMPARISONS.append({'caso':name,'medida':key,'anterior':str(value) if value is not None else None,'portal':actual,'tolerancia':'0','estado':'APROBADO' if same else 'DIFERENCIA'})
            self.assertTrue(same,f'{name}: {key}')
        return payload

    def test_real_01_periodo_completo(self):
        payload=self.compare('periodo_completo',self.default,{})
        self.assertEqual(payload['totals']['Conteo operaciones'],1044848)
        self.assertEqual(Decimal(payload['totals']['Importe']),Decimal('18909762.1180'))
        self.assertEqual(payload['figures']['monthly']['layout']['yaxis2']['title']['text'],'Operaciones')
        self.assertEqual(sum(payload['figures']['types']['data'][0]['values']),payload['totals']['Conteo operaciones'])

    def test_real_02_spain_y_ranking_categorico(self):
        spain=self.member('country','Spain')
        payload=self.compare('Spain',replace(self.default,country=spain),{'country':spain})
        figure=payload['figures']['products']
        self.assertEqual(figure['layout']['yaxis']['type'],'category')
        self.assertEqual(figure['data'][0]['orientation'],'h')
        self.assertIn('POST',figure['data'][0]['y'])
        self.assertEqual(len(payload['figures']['countries']['data'][0]['y']),1)
        (EVIDENCE/'portal_spain_respuesta.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

    def test_real_03_filtros_combinados(self):
        uk=self.member('country','United Kingdom')
        product=next(r['unique'] for r in self.catalog.members['product'] if r['label'].startswith('85123A · '))
        typ=self.member('type','Ventas y cargos')
        f=replace(self.default,start=date(2010,12,1),end=date(2010,12,31),country=uk,product=product,operation_type=typ)
        data=self.compare('combinados',f,{'start':'2010-12-01','end':'2010-12-31','country':uk,'product':product,'type':typ})
        self.assertTrue(data['type_fixed'])
        self.assertGreater(data['totals']['Conteo operaciones'],0)

    def test_real_04_tipo_precio_cero_y_calculos_fijos(self):
        typ=self.member('type','Precio cero')
        payload=self.http.get('/api/data',query_string={'type':typ}).get_json()
        self.assertEqual(Decimal(payload['totals']['Importe']),0)
        self.assertEqual(Decimal(payload['totals']['Importe Ventas y cargos']),Decimal('20533741.9180'))
        self.assertTrue(payload['type_fixed'])
        self.assertEqual(payload['totals']['Conteo operaciones'],6024)

    def test_real_05_csv_filtrado_decimal(self):
        spain=self.member('country','Spain')
        response=self.http.get('/api/export.csv',query_string={'country':spain,'group':'Código de producto'})
        self.assertEqual(response.status_code,200)
        self.assertIn('attachment',response.headers['Content-Disposition'])
        rows=list(csv.DictReader(io.StringIO(response.data.decode('utf-8-sig'))))
        expected=flat_rows(self.analytics.client.execute(grouped(self.catalog,replace(self.default,country=spain),'Código de producto')),'Código de producto')
        self.assertEqual(len(rows),len(expected))
        for row,old in zip(rows,expected):
            self.assertEqual(Decimal(row['Importe']),old['Importe'])
            self.assertRegex(row['Importe'],r'^-?\d+\.\d{4}$')
            self.assertEqual(row['Filtro país'],'Spain')
        (EVIDENCE/'portal_exportacion_spain.csv').write_bytes(response.data)

    def test_real_06_resultado_vacio(self):
        unknown=self.member('country','País desconocido')
        response=self.http.get('/api/data',query_string={'country':unknown})
        self.assertEqual(response.status_code,200)
        data=response.get_json()
        self.assertTrue(data['empty'])
        self.assertEqual(data['rows'],[])
        self.assertTrue(all(v is None for v in data['totals'].values()))

    def test_automatizada_07_navegacion_y_recursos_locales(self):
        for page in ('analytics','overview','model','etl','cube','audit'):
            response=self.http.get('/section/'+page)
            self.assertEqual(response.status_code,200,page)
            html=response.data.decode()
            self.assertIn(f'data-section="{page}"',html)
            self.assertIn('aria-current="page"',html)
            parser=Assets();parser.feed(html)
            self.assertTrue(all(url.startswith('/static/') for url in parser.urls))
            self.assertNotIn('cdn.tailwindcss.com',html)
            self.assertNotIn('Copiar Git Repo',html)
            self.assertNotIn('+14.2%',html)
            self.assertNotIn('v14.0 Enterprise',html)
        self.assertTrue('histórica' in self.http.get('/section/audit').data.decode().casefold())
        self.assertEqual(self.http.get('/static/vendor/InterVariable.woff2').mimetype,'font/woff2')

    def test_automatizada_08_descargas_lista_cerrada(self):
        for item in evidence.DOWNLOADS:
            path=evidence.file_for(item)
            if path is not None:
                response=self.http.get('/download/'+item)
                self.assertEqual(response.status_code,200,item)
                self.assertEqual(response.data,path.read_bytes())
        for invalid in ('.env','../server.py','metadatos.json','online_retail_II.xlsx','C:/Windows/win.ini'):
            self.assertEqual(self.http.get('/download/'+invalid).status_code,404)
        self.assertEqual(self.http.get('/static/../server.py').status_code,404)

    def test_automatizada_09_rechazo_mdx_libre_y_miembros(self):
        for params in ({'country':'[Pais].[Pais].&[999999]'}, {'mdx':'SELECT *'}, {'group':'Operaciones individuales'}, {'start':'2020-01-01'}):
            self.assertEqual(self.http.get('/api/data',query_string=params).status_code,400)
        self.assertEqual(self.http.post('/api/data',json={'mdx':'DROP'}).status_code,405)
        self.assertEqual(self.http.get('/api/mdx').status_code,404)
        self.assertEqual(self.http.get('/',headers={'Host':'sitio-ajeno.example'}).status_code,400)
        self.assertEqual(self.http.get('/',environ_base={'REMOTE_ADDR':'192.0.2.5'}).status_code,403)

    def test_mock_10_fallo_no_filtra_rutas_ni_cifras(self):
        with patch.object(self.analytics.client,'execute',side_effect=CubeError(r'ERROR SIMULADO C:\ruta\privada.dll')):
            response=self.http.get('/api/data')
        self.assertEqual(response.status_code,503)
        data=response.get_json()
        self.assertNotIn('totals',data)
        self.assertNotIn('privada',json.dumps(data))
        self.assertIn('reference',data)

    def test_automatizada_11_reglas_responsive_no_es_prueba_visual(self):
        css=(PORTAL/'static/css/portal.css').read_text(encoding='utf-8')
        html=self.http.get('/').data.decode()
        self.assertIn('max-width:575px',css)
        self.assertIn('max-width:991px',css)
        self.assertIn('margin-left:0',css)
        self.assertIn('grid-template-columns:1fr',css)
        self.assertIn('offcanvas-lg offcanvas-start',html)
        self.assertIn('data-bs-target="#sidebar"',html)
        self.assertIn('name="viewport"',html)
        self.assertIn('table-responsive',html)
        self.assertIn("script-src 'self'",self.http.get('/').headers['Content-Security-Policy'])

    def test_real_12_http_servido(self):
        with urlopen('http://127.0.0.1:8502/health',timeout=20) as response:
            payload=json.load(response)
            self.assertEqual(response.status,200)
            self.assertEqual(payload['ssas'],'No consultado por este endpoint')
        with urlopen('http://127.0.0.1:8502/api/data?'+urlencode({'country':self.member('country','Spain')}),timeout=120) as response:
            payload=json.load(response)
            self.assertFalse(payload['empty'])
            self.assertEqual(payload['period']['start'],'2009-12-01')


if __name__ == '__main__':
    with (EVIDENCE/'portal_pruebas.log').open('w',encoding='utf-8') as log, redirect_stderr(log), redirect_stdout(log):
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PortalTests))
    (EVIDENCE/'portal_comparacion_streamlit.json').write_text(json.dumps(COMPARISONS,ensure_ascii=False,indent=2),encoding='utf-8')
    before=list(csv.DictReader((EVIDENCE/'portal_streamlit_antes.csv').open(encoding='utf-8-sig')))
    unchanged={r['Archivo']:hashlib.sha256((DASHBOARD/r['Archivo']).read_bytes()).hexdigest().upper()==r['SHA256'] for r in before}
    report={'fecha':datetime.now().astimezone().isoformat(),'pruebas':result.testsRun,'fallos':len(result.failures),'errores':len(result.errors),
            'comparaciones_indicadores':len(COMPARISONS),'comparaciones_aprobadas':sum(r['estado']=='APROBADO' for r in COMPARISONS),
            'streamlit_original_sin_cambios':all(unchanged.values()),'archivos_originales':unchanged,
            'alcance':'Consultas SSAS reales y endpoints Flask/HTTP; pruebas de recursos y reglas responsive; 1 error simulado explícito.',
            'visual_escritorio':'Pendiente: controlador nativo y host de navegador no disponibles',
            'visual_estrecha':'Pendiente: sin navegador para inspeccionar viewport; reglas CSS verificadas automáticamente',
            'detalles':[text for _,text in result.failures+result.errors]}
    (EVIDENCE/'portal_pruebas.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result.wasSuccessful() and all(unchanged.values()) else 1)
