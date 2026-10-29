"""Servidor de lectura local. No ofrece endpoints de escritura, ETL o MDX libre."""
from datetime import datetime
import importlib.metadata
import logging
import mimetypes
from uuid import uuid4
from flask import Flask, abort, jsonify, render_template, request, Response, send_file
from shared import CubeError
from service import Analytics
import evidence

NAV = [("overview","Overview y arquitectura","▧"), ("analytics","Gráficos analíticos","▥"), ("model","Modelo dimensional","◇"),
       ("etl","Pipeline ETL","⌘"), ("cube","Cubo SSAS y MDX","⬡"), ("audit","Auditoría y descargas","▤")]
PAGES = {"overview":"overview.html", "analytics":"analytics.html", "model":"model.html", "etl":"etl.html", "cube":"cube.html", "audit":"audit.html"}
mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('text/javascript', '.js')


def create_app(analytics=None):
    app = Flask(__name__)
    app.config.update(TRUSTED_HOSTS=["localhost", "127.0.0.1"], MAX_CONTENT_LENGTH=10000)
    app.extensions["analytics"] = analytics or Analytics()

    @app.template_filter('stamp')
    def stamp(value):
        try: return datetime.fromisoformat(str(value)).strftime('%d/%m/%Y %H:%M %z')
        except (TypeError, ValueError): return value

    @app.before_request
    def local_only():
        if request.remote_addr not in (None, "127.0.0.1", "::1"):
            abort(403)

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob:; connect-src 'self'; worker-src blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        return page("analytics")

    @app.get("/section/<section>")
    def page(section):
        if section not in PAGES:
            abort(404)
        data = {"nav":NAV, "section":section, "audit":evidence.historical(), "downloads":evidence.DOWNLOADS}
        if section == "model": data["model"] = evidence.model()
        if section in ("etl", "overview"): data["etl"] = evidence.etl_documentation()
        if section == "cube": data["cube"] = evidence.cube_documentation()
        if section == "audit": data["download_items"] = [{"id":key,"label":value[1],"available":evidence.file_for(key) is not None} for key,value in evidence.DOWNLOADS.items()]
        return render_template(PAGES[section], **data)

    def failure(exc):
        reference = uuid4().hex[:10]
        app.logger.exception("Fallo de consulta SSAS. Referencia %s", reference)
        return jsonify(error="No fue posible consultar Analysis Services. No se utilizaron datos de ejemplo ni otra fuente.", reference=reference), 503

    @app.get("/api/options")
    def options():
        try: return jsonify(app.extensions["analytics"].options())
        except (CubeError, OSError, ValueError) as exc: return failure(exc)

    @app.get("/api/data")
    def data():
        try: return jsonify(app.extensions["analytics"].data(request.args))
        except ValueError: return jsonify(error="Los filtros no son válidos. Elija miembros del catálogo e intervalo disponible."), 400
        except (CubeError, OSError) as exc: return failure(exc)

    @app.get("/api/export.csv")
    def export():
        try:
            content = app.extensions["analytics"].export(request.args)
            return Response(content, mimetype="text/csv", headers={"Content-Disposition":"attachment; filename=online_retail_filtrado.csv", "Cache-Control":"no-store"})
        except ValueError: return jsonify(error="Los filtros no son válidos."), 400
        except (CubeError, OSError) as exc: return failure(exc)

    @app.get("/download/<item_id>")
    def download(item_id):
        path = evidence.file_for(item_id)
        if path is None: abort(404)
        return send_file(path, as_attachment=True, download_name=path.name)

    @app.get("/health")
    def health():
        return jsonify(http="Disponible", checked_at=datetime.now().astimezone().isoformat(), ssas="No consultado por este endpoint")

    return app
