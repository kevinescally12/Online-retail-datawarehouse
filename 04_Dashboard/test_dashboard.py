"""Pruebas etiquetadas: MDX real, AppTest con SSAS real, unitarias y error simulado."""
import csv
from dataclasses import replace
from datetime import date
from decimal import Decimal
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from config import load_settings
from connection import CubeClient, CubeError
from queries import load_catalog, totals, grouped, Filters, KPI, BASE, identifier
from presentation import flat_rows, csv_bytes

ROOT = Path(__file__).resolve().parent
EVID = ROOT.parent / "06_Pruebas_y_Evidencias"


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = CubeClient(load_settings())
        cls.catalog = load_catalog(cls.client)
        cls.default = cls.catalog.defaults()
        cls.baseline = cls.client.execute(totals(cls.catalog, cls.default))[0]["values"]
        cls.real_cases = []

    def member(self, dim, label):
        return next(r["unique"] for r in self.catalog.members[dim] if r["label"] == label)

    def product(self, code):
        return next(r["unique"] for r in self.catalog.members["product"] if r["label"].startswith(code + " · "))

    def record(self, case, filters):
        value = self.client.execute(totals(self.catalog, filters))[0]["values"]
        self.real_cases.append({"caso": case, "filtros": str(filters), "valores": value})
        return value

    def test_real_01_totales_con_referencias_conciliadas(self):
        with (EVID / "olap_resultados_mdx.csv").open(encoding="utf-8-sig") as f:
            old = next(r for r in csv.DictReader(f) if r["Contexto"] == "Total")
        for label, field in zip(BASE, ("Importe", "Cantidad", "Operaciones", "FacturasDistintas")):
            self.assertEqual(self.baseline[label], Decimal(old[field]))
        details = json.loads((EVID / "olap_detalle_mdx.json").read_text(encoding="utf-8-sig"))
        for r in details:
            if r["Consulta"] == "05_calculos.mdx":
                name, value = r["Texto"].split(" = ")
                name = name.removeprefix("[Measures].[").removesuffix("]")
                self.assertEqual(self.baseline[name], Decimal(value))

    def test_real_02_fecha_frente_mes_conciliado(self):
        values = self.record("fecha", replace(self.default, start=date(2010, 12, 1), end=date(2010, 12, 31)))
        with (EVID / "olap_resultados_mdx.csv").open(encoding="utf-8-sig") as f:
            old = next(r for r in csv.DictReader(f) if r["Contexto"] == "Mes" and r["Clave"] == "2010-12")
        for name, field in zip(BASE, ("Importe", "Cantidad", "Operaciones", "FacturasDistintas")):
            self.assertEqual(values[name], Decimal(old[field]))

    def test_real_03_pais_y_ranking_filtrado(self):
        member = self.member("country", "Germany")
        filters = replace(self.default, country=member)
        values = self.record("pais", filters)
        rows = self.client.execute(grouped(self.catalog, filters, "País", 10))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["members"][0]["caption"], "Germany")
        self.assertEqual(rows[0]["values"], {k: values[k] for k in BASE})

    def test_real_04_producto_y_categoria(self):
        filters = replace(self.default, product=self.product("85123A"))
        values = self.record("producto", filters)
        rows = self.client.execute(grouped(self.catalog, filters, "Código de producto", 10))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["members"][0]["caption"], "85123A")
        self.assertEqual(rows[0]["values"], {k: values[k] for k in BASE})
        self.assertIn("Por clasificar", [m["caption"] for m in rows[0]["members"]])

    def test_real_05_tipo_sustituido_solo_en_medidas_fijas(self):
        filters = replace(self.default, operation_type=self.member("type", "Precio cero"))
        values = self.record("tipo_precio_cero", filters)
        self.assertEqual(values["Importe"], Decimal(0))
        self.assertEqual(values["Conteo operaciones"], 6024)
        self.assertEqual(values["Importe Ventas y cargos"], self.baseline["Importe Ventas y cargos"])
        rows = self.client.execute(grouped(self.catalog, filters, "Tipo de operación"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["members"][0]["caption"], "Precio cero")

    def test_real_06_filtros_combinados_y_medidas_por_tipo(self):
        filters = Filters(date(2010, 12, 1), date(2010, 12, 31), self.member("country", "United Kingdom"),
                          self.product("85123A"), self.member("type", "Ventas y cargos"))
        values = self.record("combinados", filters)
        self.assertGreater(values["Conteo operaciones"], 0)
        self.assertLess(values["Conteo operaciones"], self.baseline["Conteo operaciones"])
        rows = self.client.execute(grouped(self.catalog, replace(filters, operation_type=""), "Tipo de operación"))
        per_type = {r["members"][0]["caption"]: r["values"] for r in rows}
        self.assertEqual(values["Importe Ventas y cargos"], per_type["Ventas y cargos"]["Importe"])
        self.assertEqual(values["Importe Cancelacion"], per_type.get("Cancelacion", {}).get("Importe"))
        self.assertEqual(values["Facturas distintas"], per_type["Ventas y cargos"]["Facturas distintas"])

    def test_real_07_vacio_sin_simular_ceros(self):
        filters = replace(self.default, country=self.member("country", "País desconocido"))
        values = self.record("sin_hechos", filters)
        self.assertTrue(all(v is None for v in values.values()))
        self.assertEqual(self.client.execute(grouped(self.catalog, filters, "Mes")), [])

    def test_real_08_exportacion_exacta_filtrada(self):
        filters = replace(self.default, country=self.member("country", "Germany"))
        rows = flat_rows(self.client.execute(grouped(self.catalog, filters, "Mes")), "Mes")
        data = csv_bytes(rows, "Mes", {"Fuente": "SSAS", "Filtro": "Germany"})
        parsed = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
        self.assertEqual(len(parsed), len(rows))
        for source, row in zip(rows, parsed):
            self.assertEqual(Decimal(row["Importe"]), source["Importe"])
            self.assertRegex(row["Importe"], r"^-?\d+\.\d{4}$")
            self.assertEqual(row["Filtro"], "Germany")
        (EVID / "dashboard_exportacion_real.csv").write_bytes(data)

    def test_real_09_no_sumar_facturas_parciales(self):
        rows = self.client.execute(grouped(self.catalog, self.default, "Tipo de operación"))
        partial_sum = sum(r["values"]["Facturas distintas"] for r in rows)
        self.assertNotEqual(partial_sum, self.baseline["Facturas distintas"])
        self.assertEqual(self.baseline["Facturas distintas"], 53628)

    def test_unit_01_rechazo_de_miembros_arbitrarios(self):
        for member in ("[Pais].[Pais].&[999999]", "[Pais].[Pais].&[1]} ON 1 FROM [Otro] --"):
            with self.assertRaises(ValueError):
                totals(self.catalog, replace(self.default, country=member))
        self.assertEqual(identifier("a]b"), "[a]]b]")
        with self.assertRaises(ValueError):
            grouped(self.catalog, self.default, "PrecioUnitario")

    def test_unit_02_fecha_invalida_y_lectura_exclusiva(self):
        with self.assertRaises(ValueError):
            totals(self.catalog, replace(self.default, start=date(2020, 1, 1)))
        with self.assertRaises(ValueError):
            self.client.execute("ALTER CUBE [Online Retail]")

    def test_ui_01_carga_filtrado_y_limpiar_con_ssas_real(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        self.assertEqual(at.metric[0].value, "1 044 848")
        self.assertEqual(len(at.get("plotly_chart")), 4)
        country = self.member("country", "Germany")
        at.selectbox(key="country").set_value(country).run()
        self.assertEqual(len(at.exception), 0)
        self.assertNotEqual(at.metric[0].value, "1 044 848")
        at.selectbox(key="operation_type").set_value(self.member("type", "Precio cero")).run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("Filtro de tipo activo" in w.value for w in at.warning))
        at.button[0].click().run()
        self.assertEqual(at.selectbox(key="country").value, "")
        self.assertEqual(at.selectbox(key="operation_type").value, "")
        self.assertEqual(at.metric[0].value, "1 044 848")
        self.assertTrue(any("Descargar" in e.label for e in at.get("download_button")))
        (EVID / "dashboard_apptest_estado.txt").write_text(str(at), encoding="utf-8")

    def test_ui_02_estado_vacio_con_ssas_real(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        at.selectbox(key="country").set_value(self.member("country", "País desconocido")).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.metric[0].value, "—")
        self.assertTrue(any("No hay operaciones" in w.value for w in at.warning))
        self.assertEqual(len(at.dataframe), 0)
        self.assertTrue(at.get("download_button")[0].disabled)

    def test_ui_03_fecha_producto_y_detalle_con_ssas_real(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        at.date_input(key="period").set_value((date(2010, 12, 1), date(2010, 12, 31)))
        at.selectbox(key="product").set_value(self.product("85123A")).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        self.assertGreater(len(at.dataframe), 0)
        at.radio(key="detail_group").set_value("Código de producto").run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.dataframe[0].value), 1)
        at.selectbox(key="country").set_value(self.member("country", "United Kingdom"))
        at.selectbox(key="operation_type").set_value(self.member("type", "Ventas y cargos")).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        at.button[0].click().run()
        self.assertEqual(at.date_input(key="period").value, (self.catalog.minimum, self.catalog.maximum))
        self.assertEqual(at.selectbox(key="product").value, "")
        self.assertEqual(at.selectbox(key="country").value, "")
        self.assertEqual(at.selectbox(key="operation_type").value, "")
        self.assertEqual(at.metric[0].value, "1 044 848")

    def test_mock_01_error_de_conexion_en_interfaz(self):
        import streamlit as st
        from streamlit.testing.v1 import AppTest
        st.cache_data.clear()
        with patch.object(CubeClient, "schema", side_effect=CubeError("ERROR SIMULADO solo para prueba")):
            at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("No fue posible consultar Analysis Services" in e.value for e in at.error))
        self.assertEqual(len(at.metric), 0)
        st.cache_data.clear()

    @classmethod
    def tearDownClass(cls):
        (EVID / "dashboard_filtros_reales.json").write_text(json.dumps(cls.real_cases, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)
