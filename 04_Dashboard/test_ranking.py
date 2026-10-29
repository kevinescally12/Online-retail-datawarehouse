"""Pruebas focalizadas de presentación. No modifica SSAS ni genera consultas nuevas."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import unittest
from contextlib import redirect_stderr

from charts import product_ranking, product_descriptions
from config import load_settings
from connection import CubeClient
from presentation import flat_rows
from queries import load_catalog, grouped

ROOT = Path(__file__).resolve().parent
EVID = ROOT.parent / "06_Pruebas_y_Evidencias"


class RankingPresentationTests(unittest.TestCase):
    def test_unit_codigos_texto_ceros_iniciales_y_alfanumericos(self):
        rows = [{"Código de producto": c, "Importe": Decimal(v), "Categoría": "Por clasificar"}
                for c, v in (("00123", "7.5000"), ("85123A", "12.0000"), ("23199", "10.0000"))]
        before = deepcopy(rows)
        description = "Descripción completa · variante " + "larga " * 35
        members = [{"label": f"00123 · {description} · Por clasificar"}]
        lookup = product_descriptions(members)
        fig = product_ranking(rows, lookup)
        self.assertEqual(list(fig.data[0].y), ["85123A", "23199", "00123"])
        self.assertEqual(fig.layout.yaxis.type, "category")
        self.assertEqual(fig.layout.yaxis.autorange, "reversed")
        self.assertEqual(list(fig.layout.yaxis.categoryarray), list(fig.data[0].y))
        self.assertEqual(fig.data[0].orientation, "h")
        self.assertEqual(fig.data[0].customdata[2][1], description)
        self.assertIn("Descripción: %{customdata[1]}", fig.data[0].hovertemplate)
        self.assertEqual(rows, before)

    def test_unit_diez_categorias_tienen_altura_y_orden(self):
        rows = [{"Código de producto": str(i).zfill(5), "Importe": Decimal(i), "Categoría": "Por clasificar"}
                for i in range(10)]
        fig = product_ranking(rows, {})
        self.assertEqual(len(fig.data[0].y), 10)
        self.assertEqual(fig.layout.height, 470)
        self.assertGreater(fig.layout.bargap, 0)
        self.assertEqual(fig.data[0].y[0], "00009")
        self.assertEqual(fig.data[0].y[-1], "00000")

    def test_real_spain_numericos_alfanumericos_y_tooltips(self):
        client = CubeClient(load_settings())
        catalog = load_catalog(client)
        spain = next(r["unique"] for r in catalog.members["country"] if r["label"] == "Spain")
        filters = replace(catalog.defaults(), country=spain)
        result = client.execute(grouped(catalog, filters, "Código de producto", 10))
        rows = flat_rows(result, "Código de producto")
        descriptions = product_descriptions(catalog.members["product"])
        fig = product_ranking(rows, descriptions)
        self.assertEqual(len(fig.data[0].y), len(rows))
        self.assertEqual(fig.layout.yaxis.type, "category")
        self.assertTrue(any(code.isdigit() for code in fig.data[0].y))
        alpha = [code for code in fig.data[0].y if any(c.isalpha() for c in code)]
        if not alpha:
            product = next(r["unique"] for r in catalog.members["product"] if r["label"].startswith("85123A · "))
            extra = flat_rows(client.execute(grouped(catalog, replace(filters, product=product), "Código de producto", 10)), "Código de producto")
            self.assertTrue(extra)
            extra_fig = product_ranking(extra, descriptions)
            self.assertIn("85123A", extra_fig.data[0].y)
        for custom in fig.data[0].customdata:
            self.assertNotEqual(custom[1], "Descripción no disponible en el catálogo")
        (EVID / "dashboard_ranking_spain_figura.json").write_text(fig.to_json(), encoding="utf-8")
        (EVID / "dashboard_ranking_spain_datos.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def test_apptest_spain_titulo_eje_y_datos_reales(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        client = CubeClient(load_settings())
        catalog = load_catalog(client)
        spain = next(r["unique"] for r in catalog.members["country"] if r["label"] == "Spain")
        at.selectbox(key="country").set_value(spain).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        figures = [json.loads(e.proto.spec) for e in at.get("plotly_chart")]
        product = figures[2]
        country = figures[1]
        self.assertEqual(product["layout"]["yaxis"]["type"], "category")
        self.assertEqual(product["data"][0]["orientation"], "h")
        self.assertEqual(len(country["data"][0]["y"]), 1)
        headers = [element.value for element in at.subheader]
        self.assertIn("Hasta 10 países con mayor importe", headers)
        (EVID / "dashboard_ranking_apptest_spain.json").write_text(json.dumps({
            "pais": "Spain", "titulos": headers,
            "eje_productos": product["layout"]["yaxis"],
            "barras_productos": len(product["data"][0]["y"]),
            "barras_paises": len(country["data"][0]["y"]),
            "excepciones": len(at.exception), "errores": len(at.error)
        }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    log = EVID / "dashboard_ranking_pruebas.log"
    with log.open("w", encoding="utf-8") as f, redirect_stderr(f):
        result = unittest.TextTestRunner(stream=f, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RankingPresentationTests))
    before = json.loads((EVID / "dashboard_ranking_archivos_antes.json").read_text(encoding="utf-8-sig"))
    unchanged = {Path(r["Path"]).name: hashlib.sha256(Path(r["Path"]).read_bytes()).hexdigest().upper() == r["Hash"] for r in before}
    summary = {"fecha": datetime.now().astimezone().isoformat(), "pruebas": result.testsRun,
               "fallos": len(result.failures), "errores": len(result.errors),
               "archivos_conexion_consultas_config_sin_cambios": unchanged,
               "alcance": "2 pruebas unitarias con casos sintéticos; 1 MDX real Spain; 1 AppTest con SSAS real. Sin revisión visual.",
               "detalles": [text for _, text in result.failures + result.errors]}
    (EVID / "dashboard_ranking_pruebas.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.wasSuccessful() and all(unchanged.values()) else 1)
