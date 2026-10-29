"""Arranque local sin depurador, recargas de datos ni publicación."""
import logging
from waitress import serve
from server import create_app
from portal_config import port

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    chosen = port()
    print(f"Portal local: http://127.0.0.1:{chosen}", flush=True)
    serve(create_app(), host="127.0.0.1", port=chosen, threads=4)
