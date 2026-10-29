"""Excel -> staging. No crea tablas ni carga dimensiones o hechos."""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import logging
import os
from pathlib import Path
import sys

import openpyxl

BASE = Path(__file__).resolve().parent
HOJAS = ("Year 2009-2010", "Year 2010-2011")
ENCABEZADOS = ("Invoice", "StockCode", "Description", "Quantity",
               "InvoiceDate", "Price", "Customer ID", "Country")
INSERT_SQL = """
INSERT INTO staging.OperacionesRetail
(HojaOrigen, NumeroFactura, CodigoProducto, Descripcion, Cantidad,
 FechaFactura, PrecioUnitario, IdCliente, Pais)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""
LOG = logging.getLogger("retail")
CLAVES_ENV = {"RETAIL_EXCEL", "RETAIL_SERVER", "RETAIL_DATABASE", "RETAIL_BATCH_SIZE",
              "RETAIL_ODBC_DRIVER", "RETAIL_TRUST_CERTIFICATE"}
# Estructura verificada en 01_crear_origen.sql; longitudes expresadas en bytes.
ESQUEMA = [
    ("IdCarga", "bigint", 8, 19, 0, False, True),
    ("HojaOrigen", "nvarchar", 60, 0, 0, False, False),
    ("NumeroFactura", "nvarchar", 100, 0, 0, True, False),
    ("CodigoProducto", "nvarchar", 100, 0, 0, True, False),
    ("Descripcion", "nvarchar", 1000, 0, 0, True, False),
    ("Cantidad", "int", 4, 10, 0, True, False),
    ("FechaFactura", "datetime2", 8, 27, 7, True, False),
    ("PrecioUnitario", "decimal", 9, 18, 4, True, False),
    ("IdCliente", "nvarchar", 100, 0, 0, True, False),
    ("Pais", "nvarchar", 200, 0, 0, True, False),
]


def leer_env(ruta: Path) -> dict[str, str]:
    """Formato KEY=VALUE; sin expansión, comandos ni contraseñas."""
    valores = {}
    if not ruta.exists():
        return valores
    for numero, linea in enumerate(ruta.read_text(encoding="utf-8-sig").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        clave, sep, valor = linea.partition("=")
        clave, valor = clave.strip(), valor.strip()
        if not sep or clave not in CLAVES_ENV:
            raise ValueError(f"Configuración no admitida en {ruta.name}, línea {numero}")
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        valores[clave] = valor
    return valores


def configurar(argv=None):
    preliminar = argparse.ArgumentParser(add_help=False)
    preliminar.add_argument("--env", type=Path, default=BASE / ".env")
    pre, _ = preliminar.parse_known_args(argv)
    env = leer_env(pre.env)
    env.update({k: os.environ[k] for k in CLAVES_ENV if k in os.environ})
    p = argparse.ArgumentParser(description=__doc__, parents=[preliminar])
    p.add_argument("--excel", default=env.get("RETAIL_EXCEL", "../01_Base_de_Datos/online_retail_II.xlsx"))
    p.add_argument("--servidor", default=env.get("RETAIL_SERVER", "localhost"))
    p.add_argument("--base-datos", default=env.get("RETAIL_DATABASE", "OnlineRetail_Origen_Replica"))
    p.add_argument("--lote", type=int, default=env.get("RETAIL_BATCH_SIZE", "5000"))
    p.add_argument("--controlador", default=env.get("RETAIL_ODBC_DRIVER", ""))
    p.add_argument("--confiar-certificado", choices=("yes", "no"),
                   default=env.get("RETAIL_TRUST_CERTIFICATE", "yes"))
    modo = p.add_mutually_exclusive_group()
    modo.add_argument("--validar-excel", action="store_true", help="Solo lee Excel (predeterminado)")
    modo.add_argument("--comprobar-conexion", action="store_true", help="Solo SELECT de esquema y conteos")
    modo.add_argument("--cargar", action="store_true", help="Inserta en staging vacío de una réplica")
    p.add_argument("--informe", type=Path, help="Resumen JSON sin filas ni credenciales; debe ser nuevo")
    args = p.parse_args(argv)
    if args.lote <= 0:
        p.error("--lote debe ser mayor que cero")
    if args.confiar_certificado not in ("yes", "no"):
        p.error("RETAIL_TRUST_CERTIFICATE debe ser yes o no")
    for nombre in ("servidor", "base_datos"):
        valor = getattr(args, nombre).strip()
        if not valor:
            p.error(f"{nombre} no puede estar vacío")
        setattr(args, nombre, valor)
    ruta = Path(args.excel).expanduser()
    args.excel = (BASE / ruta).resolve() if not ruta.is_absolute() else ruta.resolve()
    if args.cargar and args.base_datos.casefold() in {"onlineretail_origen", "onlineretail_dw"}:
        p.error("La carga en las bases actuales está bloqueada; use una réplica nueva")
    return args


def como_texto(valor, limite):
    if valor is None:
        return None
    if isinstance(valor, bool):
        raise ValueError("Identificador/texto booleano no admitido")
    if isinstance(valor, float):
        if not Decimal(str(valor)).is_finite():
            raise ValueError("Identificador no finito")
        texto = str(int(valor)) if valor.is_integer() else str(valor)
    else:
        texto = str(valor)
    if len(texto.encode("utf-16-le")) // 2 > limite:
        raise ValueError(f"Texto supera nvarchar({limite}); no se truncará")
    return texto


def numero_decimal(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float, Decimal)):
        raise ValueError("Se esperaba una celda numérica")
    try:
        numero = Decimal(str(valor))
    except InvalidOperation as exc:
        raise ValueError("Número inválido") from exc
    if not numero.is_finite():
        raise ValueError("Número no finito")
    return numero


def cantidad_entera(valor):
    if valor is None:
        return None
    n = numero_decimal(valor)
    if n != n.to_integral_value() or not -(2**31) <= n < 2**31:
        raise ValueError("Cantidad fraccionaria o fuera del rango SQL int")
    return int(n)


def precio_decimal(valor):
    if valor is None:
        return None
    n = numero_decimal(valor)
    if abs(n) >= Decimal("100000000000000") or n != n.quantize(Decimal("0.0001")):
        raise ValueError("Precio no representable en decimal(18,4) sin redondear")
    return n.quantize(Decimal("0.0001"))


def fecha_original(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            raise ValueError("datetime2 no admite zona horaria")
        return valor
    if isinstance(valor, date):
        return datetime.combine(valor, datetime.min.time())
    raise ValueError("Fecha no reconocida como fecha Excel; no se inferirá un formato")


def convertir_fila(hoja, valores):
    factura, producto, descripcion, cantidad, fecha, precio, cliente, pais = valores
    return (hoja, como_texto(factura, 50), como_texto(producto, 50),
            como_texto(descripcion, 500), cantidad_entera(cantidad), fecha_original(fecha),
            precio_decimal(precio), como_texto(cliente, 50), como_texto(pais, 100))


def validar_encabezados(libro):
    for nombre in HOJAS:
        if nombre not in libro.sheetnames:
            raise ValueError(f"Falta hoja obligatoria: {nombre}")
        cabecera = next(libro[nombre].iter_rows(min_row=1, max_row=1, values_only=True), ())
        if tuple(cabecera) != ENCABEZADOS:
            raise ValueError(f"Encabezados u orden incorrectos en {nombre}; se requieren {ENCABEZADOS}")


def procesar_excel(ruta, lote, cursor=None):
    resumen = {}
    with closing(openpyxl.load_workbook(ruta, read_only=True, data_only=False)) as libro:
        validar_encabezados(libro)
        for nombre in HOJAS:
            registros, total, vacias = [], 0, 0
            for numero, celdas in enumerate(libro[nombre].iter_rows(min_row=2), 2):
                valores = tuple(c.value for c in celdas)
                if all(v is None for v in valores):
                    vacias += 1
                    continue
                try:
                    if any(c.data_type == "f" for c in celdas):
                        raise ValueError("Fórmulas no admitidas; se requieren valores fuente")
                    if any(c.data_type == "e" for c in celdas):
                        raise ValueError("Celda con error Excel")
                    registros.append(convertir_fila(nombre, valores))
                except (ValueError, InvalidOperation, OverflowError) as exc:
                    raise ValueError(f"{nombre}, fila {numero}: {exc}") from exc
                total += 1
                if len(registros) == lote:
                    if cursor is not None:
                        cursor.executemany(INSERT_SQL, registros)
                    registros.clear()
                    LOG.info("%s: %s filas procesadas (aún sin confirmar en modo carga)", nombre, total)
            if registros and cursor is not None:
                cursor.executemany(INSERT_SQL, registros)
            resumen[nombre] = {"filas": total, "filas_vacias_omitidas": vacias}
            LOG.info("%s: total=%s, vacías omitidas=%s", nombre, total, vacias)
    return resumen


def conexion_sql(args, lectura=False):
    import pyodbc  # Validar Excel no usa ODBC.
    disponibles = pyodbc.drivers()
    controlador = args.controlador or next((d for d in (
        "ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server") if d in disponibles), "")
    if controlador not in disponibles or not controlador:
        raise RuntimeError("No está disponible el controlador ODBC configurado (requiere 17 o 18)")
    def odbc(v):
        return "{" + v.replace("}", "}}") + "}"
    cadena = (f"DRIVER={odbc(controlador)};SERVER={odbc(args.servidor)};"
              f"DATABASE={odbc(args.base_datos)};Trusted_Connection=yes;Encrypt=yes;"
              f"TrustServerCertificate={args.confiar_certificado};"
              + ("ApplicationIntent=ReadOnly;" if lectura else ""))
    return pyodbc.connect(cadena, autocommit=False, timeout=15)


def verificar_esquema(cursor):
    cursor.execute("""
    SELECT c.name,t.name,c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity
    FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id
    WHERE c.object_id=OBJECT_ID(N'staging.OperacionesRetail') ORDER BY c.column_id
    """)
    if [tuple(r) for r in cursor.fetchall()] != ESQUEMA:
        raise RuntimeError("Esquema de staging diferente del verificado; revise 01_crear_origen.sql")


def cargar(args):
    if not args.excel.is_file():
        raise FileNotFoundError(f"No se encontró el Excel: {args.excel}")
    with closing(openpyxl.load_workbook(args.excel, read_only=True, data_only=False)) as libro:
        validar_encabezados(libro)
    with closing(conexion_sql(args)) as cn:
        with closing(cn.cursor()) as cursor:
            try:
                cursor.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 15000;")
                verificar_esquema(cursor)
                cursor.execute("SELECT COUNT_BIG(*) FROM staging.OperacionesRetail WITH (TABLOCKX,HOLDLOCK)")
                if cursor.fetchone()[0] != 0:
                    raise RuntimeError("staging ya contiene registros; carga detenida sin insertar")
                cursor.fast_executemany = True
                resumen = procesar_excel(args.excel, args.lote, cursor)
                cursor.execute("SELECT HojaOrigen,COUNT_BIG(*) FROM staging.OperacionesRetail GROUP BY HojaOrigen")
                actuales = {r[0]: r[1] for r in cursor.fetchall()}
                esperados = {h: r["filas"] for h, r in resumen.items() if r["filas"]}
                if actuales != esperados:
                    raise RuntimeError("Conteos por hoja distintos; se revierte toda la carga")
                cn.commit()
                LOG.info("COMMIT confirmado: %s filas", sum(r["filas"] for r in resumen.values()))
                return resumen
            except BaseException:
                cn.rollback()
                LOG.error("ROLLBACK solicitado; no se conserva la carga parcial de esta transacción")
                raise


def comprobar_conexion(args):
    with closing(conexion_sql(args, lectura=True)) as cn:
        with closing(cn.cursor()) as cursor:
            verificar_esquema(cursor)
            cursor.execute("SELECT HojaOrigen,COUNT_BIG(*) FROM staging.OperacionesRetail GROUP BY HojaOrigen")
            return {r[0]: {"filas": r[1]} for r in cursor.fetchall()}


def sha256(ruta):
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = configurar(argv)
    modo = "cargar" if args.cargar else "comprobar_conexion" if args.comprobar_conexion else "validar_excel"
    informe = {"fecha": datetime.now().astimezone().isoformat(), "modo": modo,
               "servidor": args.servidor, "base_datos": args.base_datos,
               "python": sys.version.split()[0], "openpyxl": openpyxl.__version__}
    codigo, reservado = 0, False
    try:
        if args.informe:
            salida = args.informe.resolve()
            if salida == args.excel or salida.suffix.lower() != ".json":
                raise ValueError("--informe debe ser un archivo .json distinto del Excel")
            with salida.open("x", encoding="utf-8") as f:
                reservado = True
                json.dump({"estado": "INICIADO", **informe}, f, ensure_ascii=False)
        if args.comprobar_conexion:
            informe["conteos"] = comprobar_conexion(args)
        else:
            informe["excel_sha256"] = sha256(args.excel)
            informe["conteos"] = cargar(args) if args.cargar else procesar_excel(args.excel, args.lote)
        informe["estado"] = "COMMIT_CONFIRMADO" if args.cargar else "APROBADO_SIN_CARGA"
    except (Exception, KeyboardInterrupt) as exc:
        LOG.error("%s: %s", type(exc).__name__, exc)
        informe["estado"] = "ERROR"
        informe["error"] = f"{type(exc).__name__}: {exc}"
        codigo = 1
    if reservado:
        try:
            salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            LOG.error("No se pudo guardar el informe; estado de la operación: %s", informe["estado"])
            return 1
    LOG.info("Estado final: %s", informe["estado"])
    return codigo


if __name__ == "__main__":
    sys.exit(main())
