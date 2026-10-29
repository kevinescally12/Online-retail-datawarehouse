"""ADOMD.NET vía pythonnet/netfx, probado en CPython 3.12 x64.

Una conexión por consulta; sin SQL relacional ni conexiones globales compartidas.
"""
from decimal import Decimal
from pathlib import Path
from threading import Lock
from config import Settings

_lock = Lock()
_api = None


class CubeError(RuntimeError):
    pass


def runtime(settings: Settings):
    global _api
    with _lock:
        if _api is None:
            if not Path(settings.dll).is_file():
                raise CubeError("No se encontró ADOMD.NET. Revise ADOMD_DLL en .env.")
            from pythonnet import load
            load("netfx")
            import clr
            clr.AddReference(settings.dll)
            from Microsoft.AnalysisServices.AdomdClient import AdomdConnection
            from System import Array, Int32, Convert
            from System.Data.Common import DbConnectionStringBuilder
            from System.Globalization import CultureInfo
            _api = (AdomdConnection, Array, Int32, Convert, CultureInfo.InvariantCulture, DbConnectionStringBuilder)
        return _api


def numeric(value, api):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        raise CubeError("SSAS devolvió Double donde se esperaba Decimal/Int64; no se redondeó.")
    name = str(value.GetType().FullName) if hasattr(value, "GetType") else type(value).__name__
    if name == "System.Decimal":
        return Decimal(api[3].ToString(value, api[4]))
    if name in {"System.Int64", "System.Int32"}:
        return int(value)
    raise CubeError(f"Tipo numérico no previsto: {name}")


class CubeClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _open(self):
        api = runtime(self.settings)
        builder = api[5]()
        builder["Data Source"] = self.settings.server
        builder["Initial Catalog"] = self.settings.database
        builder["Integrated Security"] = "SSPI"
        builder["Connect Timeout"] = "15"
        connection = api[0](builder.ConnectionString)
        try:
            connection.Open()
        except Exception:
            connection.Dispose()
            raise
        return connection, api

    def schema(self):
        """Solo metadatos del cubo real; usa DMV de SSAS, no SQL Server."""
        connection = None
        try:
            connection, api = self._open()
            command = connection.CreateCommand()
            command.CommandText = "SELECT * FROM $SYSTEM.MDSCHEMA_MEASURES WHERE CUBE_NAME = 'Online Retail'"
            reader = command.ExecuteReader()
            rows = []
            try:
                while reader.Read():
                    rows.append({reader.GetName(i): None if reader.IsDBNull(i) else
                                 api[3].ToString(reader.GetValue(i), api[4]) for i in range(reader.FieldCount)})
            finally:
                reader.Close()
            return rows
        except Exception as exc:
            raise CubeError(f"No se pudo leer el catálogo SSAS: {exc}") from exc
        finally:
            if connection is not None:
                connection.Dispose()

    def execute(self, mdx):
        # Esta API no es un editor MDX. Sus llamadas proceden exclusivamente de queries.py.
        if not mdx.lstrip().upper().startswith("SELECT "):
            raise ValueError("Solo se admiten consultas SELECT de lectura.")
        connection = None
        try:
            connection, api = self._open()
            command = connection.CreateCommand()
            command.CommandTimeout = self.settings.timeout
            command.CommandText = mdx
            cells = command.ExecuteCellSet()
            count = cells.Axes[1].Positions.Count if cells.Axes.Count > 1 else 1
            if count > 7000:
                raise CubeError("La consulta supera 7000 agregados; seleccione más filtros.")
            columns = [str(p.Members[0].Caption) for p in cells.Axes[0].Positions]
            rows = []
            for j in range(count):
                members = []
                if cells.Axes.Count > 1:
                    members = [{"unique": str(m.UniqueName), "caption": str(m.Caption)}
                               for m in cells.Axes[1].Positions[j].Members]
                values = {}
                for i, label in enumerate(columns):
                    indexes = api[1][api[2]]([i, j] if cells.Axes.Count > 1 else [i])
                    values[label] = numeric(cells.Cells.get_Item(indexes).Value, api)
                rows.append({"members": members, "values": values})
            return rows
        except CubeError:
            raise
        except Exception as exc:
            raise CubeError(f"La consulta al cubo no terminó: {exc}") from exc
        finally:
            if connection is not None:
                connection.Dispose()
