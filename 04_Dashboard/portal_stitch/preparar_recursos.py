"""Verifica el recurso Plotly strict local; no descarga ni ejecuta software."""
import hashlib
from importlib.metadata import distribution
import json
import re
from pathlib import Path
from plotly.offline import get_plotlyjs

root = Path(__file__).resolve().parent
vendor = root / "static/vendor"
vendor.mkdir(parents=True, exist_ok=True)
expected = re.search(r"plotly.js v([0-9.]+)", get_plotlyjs()[:1000])[1]
asset = vendor / "plotly.min.js"
if not asset.is_file() or f"v{expected}" not in asset.read_text(encoding="utf-8")[:1000]:
    raise RuntimeError(f"Falta Plotly strict compatible. Conservar el recurso local de versión {expected} incluido en la entrega.")
dist = distribution("plotly")
for file in dist.files:
    if str(file).endswith("LICENSE.txt"):
        (vendor / "PLOTLY-LICENSE.txt").write_bytes(Path(dist.locate_file(file)).read_bytes())
        break
assets = [{"archivo": p.name, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
          for p in vendor.iterdir() if p.is_file()]
(root / "recursos.json").write_text(json.dumps(assets, indent=2), encoding="utf-8")
print(json.dumps(assets, indent=2))
