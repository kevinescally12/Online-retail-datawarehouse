"""Importa los módulos funcionales de Streamlit sin copiarlos ni modificarlos."""
from pathlib import Path
import sys

PORTAL = Path(__file__).resolve().parent
DASHBOARD = PORTAL.parent
PROJECT = DASHBOARD.parent
EVIDENCE = PROJECT / "06_Pruebas_y_Evidencias"
sys.path.insert(0, str(DASHBOARD))

from config import Settings, load_settings
from connection import CubeClient, CubeError
from queries import Catalog, Filters, KPI, BASE, GROUPS, load_catalog, totals, grouped
from presentation import number, flat_rows, csv_bytes
from charts import product_ranking, product_descriptions
