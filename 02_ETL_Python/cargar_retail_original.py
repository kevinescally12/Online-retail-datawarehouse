from pathlib import Path
from decimal import Decimal
import sys

import openpyxl
import pyodbc


ARCHIVO_EXCEL = Path(__file__).parent / "online_retail_II.xlsx"
TAMANO_LOTE = 5000

HOJAS = [
    "Year 2009-2010",
    "Year 2010-2011",
]


def como_texto(valor):
    """Conserva identificadores numéricos o alfanuméricos como texto."""
    if valor is None:
        return None

    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))

    return str(valor)


def cargar_lote(cursor, registros):
    cursor.executemany(
        """
        INSERT INTO staging.OperacionesRetail (
            HojaOrigen,
            NumeroFactura,
            CodigoProducto,
            Descripcion,
            Cantidad,
            FechaFactura,
            PrecioUnitario,
            IdCliente,
            Pais
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        registros,
    )


def main():
    if not ARCHIVO_EXCEL.exists():
        raise FileNotFoundError(
            f"No se encontró el Excel en: {ARCHIVO_EXCEL}"
        )

    controladores = pyodbc.drivers()
    controlador = next(
        (
            nombre
            for nombre in (
                "ODBC Driver 18 for SQL Server",
                "ODBC Driver 17 for SQL Server",
            )
            if nombre in controladores
        ),
        None,
    )

    if controlador is None:
        raise RuntimeError(
            "No se encontró ODBC Driver 17 o 18 para SQL Server. "
            f"Controladores disponibles: {controladores}"
        )

    conexion = pyodbc.connect(
        f"DRIVER={{{controlador}}};"
        "SERVER=localhost;"
        "DATABASE=OnlineRetail_Origen;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;",
        autocommit=False,
    )

    libro = None

    try:
        cursor = conexion.cursor()

        cursor.execute(
            "SELECT COUNT_BIG(*) FROM staging.OperacionesRetail"
        )
        filas_existentes = cursor.fetchone()[0]

        if filas_existentes > 0:
            raise RuntimeError(
                "La tabla staging.OperacionesRetail ya contiene "
                f"{filas_existentes:,} filas. Se detuvo la carga "
                "para evitar duplicados."
            )

        libro = openpyxl.load_workbook(
            ARCHIVO_EXCEL,
            read_only=True,
            data_only=True,
        )

        for nombre_hoja in HOJAS:
            if nombre_hoja not in libro.sheetnames:
                raise ValueError(
                    f"No se encontró la hoja: {nombre_hoja}. "
                    f"Hojas disponibles: {libro.sheetnames}"
                )

        cursor.fast_executemany = True
        total_general = 0

        for nombre_hoja in HOJAS:
            hoja = libro[nombre_hoja]
            registros = []
            total_hoja = 0

            print(f"\nProcesando: {nombre_hoja}", flush=True)

            for fila in hoja.iter_rows(
                min_row=2,
                max_col=8,
                values_only=True,
            ):
                if all(valor is None for valor in fila):
                    continue

                factura, producto, descripcion, cantidad, fecha, precio, cliente, pais = fila

                registros.append(
                    (
                        nombre_hoja,
                        como_texto(factura),
                        como_texto(producto),
                        como_texto(descripcion),
                        int(cantidad) if cantidad is not None else None,
                        fecha,
                        Decimal(str(precio)) if precio is not None else None,
                        como_texto(cliente),
                        como_texto(pais),
                    )
                )

                if len(registros) >= TAMANO_LOTE:
                    cargar_lote(cursor, registros)
                    total_hoja += len(registros)
                    registros.clear()

                    print(
                        f"  Filas procesadas: {total_hoja:,}",
                        flush=True,
                    )

            if registros:
                cargar_lote(cursor, registros)
                total_hoja += len(registros)

            total_general += total_hoja
            print(
                f"  Total de la hoja: {total_hoja:,}",
                flush=True,
            )

        conexion.commit()
        print(
            f"\nCarga completada. Total: {total_general:,} filas.",
            flush=True,
        )

    except Exception:
        conexion.rollback()
        raise

    finally:
        if libro is not None:
            libro.close()
        conexion.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nError: {error}", file=sys.stderr)
        sys.exit(1)