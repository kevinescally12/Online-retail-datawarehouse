"""Configuración propia del portal; nunca modifica el entorno de Streamlit."""
from dataclasses import replace
import os
import socket
from dotenv import dotenv_values
from shared import PORTAL, load_settings


def settings():
    base = load_settings()
    values = {**dotenv_values(PORTAL / ".env"), **os.environ}
    server = values.get("SSAS_SERVER", base.server)
    database = values.get("SSAS_DATABASE", base.database)
    if server.lower() not in {"localhost", ".", socket.gethostname().lower()} or database != "CuboOnlineRetail":
        raise ValueError("Esta entrega solo consulta el cubo local verificado.")
    timeout = int(values.get("SSAS_TIMEOUT", str(base.timeout)))
    if not 1 <= timeout <= 300:
        raise ValueError("Tiempo de consulta fuera de rango.")
    return replace(base, server=server, database=database, dll=values.get("ADOMD_DLL", base.dll), timeout=timeout)


def port():
    value = int({**dotenv_values(PORTAL / ".env"), **os.environ}.get("PORTAL_PORT", "8502"))
    if not 1024 <= value <= 65535:
        raise ValueError("PORTAL_PORT debe estar entre 1024 y 65535.")
    return value
