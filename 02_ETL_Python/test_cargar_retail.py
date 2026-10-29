"""Pruebas locales: Excel sintético y conexión simulada. Nunca usa un SQL Server."""
from collections import Counter
from contextlib import redirect_stderr
from datetime import datetime
from decimal import Decimal
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import openpyxl
import cargar_retail as etl


class ConexionSimulada:
    def __init__(self, existentes=(), falla_lote=None, conteo_incorrecto=False):
        self.rows = list(existentes)
        self.iniciales = list(existentes)
        self.falla_lote = falla_lote
        self.conteo_incorrecto = conteo_incorrecto
        self.lotes = []
        self.commit_realizado = self.rollback_realizado = False
        self.closed = self.cursor_closed = False
        self.sql = ""

    def cursor(self):
        return self

    def execute(self, sql):
        self.sql = sql
        return self

    def fetchone(self):
        return (len(self.rows),)

    def fetchall(self):
        if "sys.columns" in self.sql:
            return etl.ESQUEMA
        counts = Counter(r[0] for r in self.rows)
        if self.conteo_incorrecto:
            counts[etl.HOJAS[0]] += 1
        return list(counts.items())

    def executemany(self, sql, rows):
        self.lotes.append(list(rows))
        if len(self.lotes) == self.falla_lote:
            raise RuntimeError("Fallo de inserción simulado")
        self.rows.extend(rows)

    def commit(self):
        self.commit_realizado = True

    def rollback(self):
        self.rollback_realizado = True
        self.rows = list(self.iniciales)

    def close(self):
        if self.cursor_closed:
            self.closed = True
        else:
            self.cursor_closed = True


class PruebasETL(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "retail.xlsx"
        self.fecha = datetime(2010, 12, 1, 14, 20, 30)
        self.fila = ("C0001", "001A", " Texto original ", -2, self.fecha, -1.25, None, " Perú ")
        self.crear_excel()
        self.args = etl.configurar(["--excel", str(self.ruta), "--lote", "1"])

    def crear_excel(self, cabecera=None, formula=False):
        w = openpyxl.Workbook()
        w.remove(w.active)
        for nombre in etl.HOJAS:
            s = w.create_sheet(nombre)
            s.append(cabecera if cabecera and nombre == etl.HOJAS[1] else etl.ENCABEZADOS)
            s.append(self.fila)
            s.append(self.fila)  # Repetición interna que se debe conservar.
        if formula:
            w[etl.HOJAS[1]]["F2"] = "=1+2"
        w.save(self.ruta)
        w.close()

    def test_identificadores_signos_fecha_nulos_y_espacios(self):
        r = etl.convertir_fila(etl.HOJAS[0], self.fila)
        self.assertEqual(r, (etl.HOJAS[0], "C0001", "001A", " Texto original ",
                             -2, self.fecha, Decimal("-1.2500"), None, " Perú "))
        self.assertEqual(etl.como_texto(12345.0, 50), "12345")
        self.assertEqual(etl.como_texto("000123", 50), "000123")

    def test_no_truncar_ni_redondear(self):
        for fn, valor in ((etl.cantidad_entera, 1.5), (etl.cantidad_entera, 2**31),
                          (etl.precio_decimal, 1.00001), (etl.precio_decimal, float("nan")),
                          (etl.fecha_original, "01/12/2010")):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                fn(valor)
        with self.assertRaises(ValueError):
            etl.como_texto("😀" * 26, 50)  # 52 unidades UTF-16.

    def test_solo_excel_sin_conexion_y_sin_filtrar_solapamiento(self):
        with patch.object(etl, "conexion_sql", side_effect=AssertionError("No debe conectar")):
            r = etl.procesar_excel(self.ruta, 3)
        self.assertEqual([r[h]["filas"] for h in etl.HOJAS], [2, 2])

    def test_carga_lotes_y_commit_simulados_conservan_repeticiones(self):
        cn = ConexionSimulada()
        with patch.object(etl, "conexion_sql", return_value=cn):
            etl.cargar(self.args)
        self.assertEqual(len(cn.rows), 4)
        self.assertEqual(len(cn.lotes), 4)
        self.assertTrue(cn.commit_realizado)
        self.assertFalse(cn.rollback_realizado)
        self.assertTrue(cn.closed and cn.cursor_closed)

    def test_staging_no_vacio_impide_inserciones(self):
        cn = ConexionSimulada(existentes=[("existente",)])
        with patch.object(etl, "conexion_sql", return_value=cn), self.assertRaisesRegex(RuntimeError, "ya contiene"):
            etl.cargar(self.args)
        self.assertEqual(cn.lotes, [])
        self.assertEqual(cn.rows, [("existente",)])
        self.assertTrue(cn.rollback_realizado and cn.closed)

    def test_error_despues_del_primer_lote_revierte_todo(self):
        cn = ConexionSimulada(falla_lote=2)
        with patch.object(etl, "conexion_sql", return_value=cn), self.assertRaisesRegex(RuntimeError, "simulado"):
            etl.cargar(self.args)
        self.assertEqual(len(cn.lotes), 2)
        self.assertEqual(cn.rows, [])
        self.assertFalse(cn.commit_realizado)
        self.assertTrue(cn.rollback_realizado and cn.closed)

    def test_conteos_no_coinciden_revierte(self):
        cn = ConexionSimulada(conteo_incorrecto=True)
        with patch.object(etl, "conexion_sql", return_value=cn), self.assertRaisesRegex(RuntimeError, "Conteos"):
            etl.cargar(self.args)
        self.assertEqual(cn.rows, [])
        self.assertTrue(cn.rollback_realizado)

    def test_segunda_cabecera_incorrecta_impide_abrir_conexion(self):
        self.crear_excel(cabecera=("incorrecto",) + etl.ENCABEZADOS[1:])
        with patch.object(etl, "conexion_sql") as conexion, self.assertRaisesRegex(ValueError, "Encabezados"):
            etl.cargar(self.args)
        conexion.assert_not_called()

    def test_formula_rechazada_con_hoja_y_fila(self):
        self.crear_excel(formula=True)
        with self.assertRaisesRegex(ValueError, "Year 2010-2011, fila 2"):
            etl.procesar_excel(self.ruta, 3)

    def test_libro_se_cierra_ante_error(self):
        self.crear_excel(formula=True)
        w = openpyxl.load_workbook(self.ruta, read_only=True)
        with patch.object(etl.openpyxl, "load_workbook", return_value=w), patch.object(w, "close", wraps=w.close) as cerrar:
            with self.assertRaises(ValueError):
                etl.procesar_excel(self.ruta, 3)
            cerrar.assert_called_once()

    def test_configuracion_env_cli_y_ruta_relativa(self):
        ruta_env = Path(self.tmp.name) / ".env"
        ruta_env.write_text("RETAIL_DATABASE=ReplicaEnv\nRETAIL_BATCH_SIZE=7\n", encoding="utf-8")
        with patch.dict(etl.os.environ, {"RETAIL_DATABASE": "ReplicaSistema"}):
            r = etl.configurar(["--env", str(ruta_env), "--base-datos", "ReplicaCLI"])
        self.assertEqual(r.base_datos, "ReplicaCLI")
        self.assertEqual(r.lote, 7)
        self.assertEqual(r.excel, (etl.BASE.parent / "01_Base_de_Datos/online_retail_II.xlsx").resolve())

    def test_bases_actuales_bloqueadas_y_lote_invalido(self):
        for argv in (["--cargar", "--base-datos", "OnlineRetail_Origen"],
                     ["--cargar", "--base-datos", "OnlineRetail_DW"], ["--lote", "0"]):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                etl.configurar(argv)

    def test_informe_existente_no_se_sobrescribe(self):
        p = Path(self.tmp.name) / "informe.json"
        p.write_text("conservar", encoding="utf-8")
        self.assertEqual(etl.main(["--excel", str(self.ruta), "--informe", str(p)]), 1)
        self.assertEqual(p.read_text(encoding="utf-8"), "conservar")


if __name__ == "__main__":
    unittest.main(verbosity=2)
