"""Comprobación focalizada final de páginas/descargas, sin repetir la suite del cubo."""
from contextlib import redirect_stderr
from datetime import datetime
import hashlib
import json
import unittest
from shared import EVIDENCE, DASHBOARD
from test_portal import PortalTests

names = ('test_automatizada_07_navegacion_y_recursos_locales',
         'test_automatizada_08_descargas_lista_cerrada',
         'test_automatizada_11_reglas_responsive_no_es_prueba_visual')
with (EVIDENCE/'portal_revision_final.log').open('w',encoding='utf-8') as log, redirect_stderr(log):
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.TestSuite(PortalTests(name) for name in names))
report={'fecha':datetime.now().astimezone().isoformat(),'pruebas':result.testsRun,'fallos':len(result.failures),'errores':len(result.errors),
        'alcance':'Páginas, fechas legibles, diccionario del portal, descargas y marcado responsive; no prueba visual ni nuevas conciliaciones del cubo.'}
(EVIDENCE/'portal_revision_final.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
