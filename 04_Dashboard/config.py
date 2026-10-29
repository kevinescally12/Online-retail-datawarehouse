"""Configuración local sin credenciales."""
from dataclasses import dataclass
import os
from pathlib import Path
import socket
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
DEFAULT_DLL = r"C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\SSAS\Microsoft.AnalysisServices.AdomdClient.dll"


@dataclass(frozen=True)
class Settings:
    server: str = "localhost"
    database: str = "CuboOnlineRetail"
    dll: str = DEFAULT_DLL
    timeout: int = 60


def load_settings():
    env = {**dotenv_values(ROOT / ".env"), **os.environ}
    server = env.get("SSAS_SERVER", "localhost").strip()
    if server.lower() not in {"localhost", ".", socket.gethostname().lower()}:
        raise ValueError("Esta entrega está restringida al SSAS local; revise SSAS_SERVER.")
    database = env.get("SSAS_DATABASE", "CuboOnlineRetail").strip()
    if database != "CuboOnlineRetail":
        raise ValueError("La base verificada es CuboOnlineRetail; no se cambia de fuente silenciosamente.")
    timeout = int(env.get("SSAS_TIMEOUT", "60"))
    if not 1 <= timeout <= 300:
        raise ValueError("SSAS_TIMEOUT debe estar entre 1 y 300 segundos.")
    return Settings(server, database, env.get("ADOMD_DLL", DEFAULT_DLL), timeout)
