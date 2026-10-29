"""Dashboard local: todas las cifras proceden de MDX/SSAS."""
from datetime import datetime
import logging

import pandas as pd
import plotly.express as px
import streamlit as st

from config import load_settings
from connection import CubeClient, CubeError
from queries import load_catalog, Filters, totals, grouped, GROUPS
from presentation import number, flat_rows, csv_bytes
from charts import product_ranking, product_descriptions

st.set_page_config(page_title="Online Retail · Análisis de operaciones", page_icon="◈", layout="wide")
st.markdown("""<style>
[data-testid="stMetricValue"] {font-size:clamp(1.05rem,1.65vw,1.65rem);white-space:normal;}
</style>""", unsafe_allow_html=True)


@st.cache_data(ttl=120, show_spinner=False)
def get_catalog(settings):
    return load_catalog(CubeClient(settings))


@st.cache_data(ttl=30, show_spinner=False)
def query(settings, mdx):
    return CubeClient(settings).execute(mdx), datetime.now().astimezone().isoformat(timespec="seconds")


def clear_filters():
    for key in ("period", "country", "product", "operation_type"):
        st.session_state.pop(key, None)


def chart(rows, group, title, horizontal=False, descriptions=None):
    st.subheader(title)
    if not rows:
        st.info("No hay datos agregados para esta selección.")
        return
    if group == "Código de producto":
        fig = product_ranking(rows, descriptions or {})
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
        return
    # Solo la geometría del gráfico usa float. Indicadores, tabla y CSV mantienen Decimal.
    frame = pd.DataFrame([{group: r[group], "Importe": float(r["Importe"]) if r["Importe"] is not None else None,
                           "Importe exacto": number(r["Importe"], True),
                           "Categoría": r.get("Categoría", "")} for r in rows])
    if horizontal:
        fig = px.bar(frame, x="Importe", y=group, orientation="h", custom_data=["Importe exacto", "Categoría"],
                     color_discrete_sequence=["#087f8c"])
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_traces(hovertemplate="%{y}<br>Importe: %{customdata[0]}<br>%{customdata[1]}<extra></extra>")
    else:
        fig = px.line(frame, x=group, y="Importe", markers=True, custom_data=["Importe exacto"],
                      color_discrete_sequence=["#087f8c"])
        fig.update_traces(hovertemplate="%{x}<br>Importe: %{customdata[0]}<extra></extra>")
    fig.update_layout(height=340, margin=dict(l=5, r=15, t=10, b=10),
                      xaxis_title="Importe con signo · unidades monetarias" if horizontal else group,
                      yaxis_title=group if horizontal else "Importe con signo · unidades monetarias",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})


def main():
    st.markdown("**ONLINE RETAIL / EXPLORADOR OLAP**")
    st.title("Operaciones, cargos y cancelaciones")
    st.caption("Fuente exclusiva: Analysis Services local · CuboOnlineRetail · Online Retail · autenticación Windows")
    try:
        settings = load_settings()
        with st.spinner("Conectando al cubo y leyendo sus miembros…"):
            catalog = get_catalog(settings)
        labels = {dim: {r["unique"]: r["label"] for r in rows} for dim, rows in catalog.members.items()}
        with st.sidebar:
            st.header("Filtros")
            st.button("Limpiar filtros", on_click=clear_filters, width="stretch")
            period = st.date_input("Periodo de operaciones", value=(catalog.minimum, catalog.maximum),
                                   min_value=catalog.minimum, max_value=catalog.maximum,
                                   format="DD/MM/YYYY", key="period")
            country = st.selectbox("País", [""] + list(labels["country"]),
                                   format_func=lambda m: labels["country"].get(m, "Todos los países"), key="country")
            product = st.selectbox("Código y descripción de producto", [""] + list(labels["product"]),
                                   format_func=lambda m: labels["product"].get(m, "Todos los códigos"), key="product")
            operation_type = st.selectbox("Tipo de operación", [""] + list(labels["type"]),
                                          format_func=lambda m: labels["type"].get(m, "Todos los tipos"), key="operation_type")
            st.caption("Los filtros seleccionan miembros reales del cubo. Las categorías Por clasificar se conservan.")
            if st.button("Actualizar consultas", width="stretch"):
                get_catalog.clear()
                query.clear()
                st.rerun()
        if len(period) != 2:
            st.info("Seleccione la fecha inicial y la final para consultar.")
            return
        filters = Filters(period[0], period[1], country, product, operation_type)
        catalog.validate(filters)
        st.subheader(f"{period[0]:%d/%m/%Y} — {period[1]:%d/%m/%Y}")
        st.caption("2009 y 2011 son periodos incompletos en la fuente. No interpretar sus totales como años completos.")
        st.info("Ventas y cargos incluye conceptos que no son mercancías. Las cancelaciones ya son negativas: el neto las suma con su signo.")
        if operation_type:
            st.warning("Filtro de tipo activo: operaciones, importe observado, facturas distintas y gráficos respetan ese tipo. "
                       "Las tarjetas de Ventas y cargos, Cancelacion, Neto, Ajustes, Precio cero y Por revisar fijan su propio tipo "
                       "y sustituyen este filtro; conservan fecha, país y producto.")
        with st.spinner("Consultando indicadores agregados en Analysis Services…"):
            result, fetched = query(settings, totals(catalog, filters))
            values = result[0]["values"]
        if all(v is None for v in values.values()):
            st.warning("No hay operaciones para la combinación de filtros seleccionada. Los valores ausentes se muestran con —.")
        elif values["Conteo operaciones"] is None:
            st.warning("No hay operaciones para el tipo seleccionado. Los indicadores que fijan otro tipo pueden conservar valores.")
        metrics = (("Operaciones seleccionadas", "Conteo operaciones", False),
                   ("Importe de Ventas y cargos", "Importe Ventas y cargos", True),
                   ("Importe de cancelaciones", "Importe Cancelacion", True),
                   ("Neto: ventas/cargos + cancelación", "Neto Ventas y cargos mas Cancelacion", True))
        for col, (label, key, money) in zip(st.columns(4), metrics):
            col.metric(label, number(values[key], money), border=True)
        for col, (label, key, money) in zip(st.columns(4), (
                ("Ajustes contables · importe", "Importe Ajuste contable", True),
                ("Por revisar · operaciones", "Operaciones Por revisar", False),
                ("Precio cero · operaciones", "Operaciones Precio cero", False),
                ("Facturas distintas seleccionadas", "Facturas distintas", False))):
            col.metric(label, number(values[key], money), border=True)
        st.caption(f"Importe observado con todos los filtros: {number(values['Importe'], True)} · "
                   f"Cantidad firmada: {number(values['Cantidad firmada'])} · Consulta: {fetched}")
        st.divider()
        with st.spinner("Consultando series y rankings agregados…"):
            monthly = flat_rows(query(settings, grouped(catalog, filters, "Mes"))[0], "Mes")
            countries = flat_rows(query(settings, grouped(catalog, filters, "País", top=10))[0], "País")
            products = flat_rows(query(settings, grouped(catalog, filters, "Código de producto", top=10))[0], "Código de producto")
            types = flat_rows(query(settings, grouped(catalog, filters, "Tipo de operación"))[0], "Tipo de operación")
        left, right = st.columns([1.4, 1])
        with left:
            chart(monthly, "Mes", "Evolución mensual del importe observado")
        with right:
            chart(countries, "País", "Hasta 10 países con mayor importe", True)
        left, right = st.columns(2)
        with left:
            chart(products, "Código de producto", "Códigos · 10 mayores importes con signo", True,
                  descriptions=product_descriptions(catalog.members["product"]))
        with right:
            chart(types, "Tipo de operación", "Importe observado por tipo de operación", True)
        st.caption("Rankings calculados en SSAS por importe firmado, no por valor absoluto. Los cargos y códigos especiales permanecen incluidos.")
        st.divider()
        st.subheader("Detalle agregado y exportación")
        group = st.radio("Agrupar resultado filtrado por", list(GROUPS), horizontal=True, key="detail_group")
        with st.spinner("Leyendo el detalle agregado…"):
            detail, detail_time = query(settings, grouped(catalog, filters, group))
            rows = flat_rows(detail, group)
        display = [{k: number(v, k == "Importe") if k in values else v for k, v in row.items()} for row in rows]
        if rows:
            st.dataframe(pd.DataFrame(display), width="stretch", hide_index=True)
        else:
            st.info("Sin filas agregadas para exportar con estos filtros.")
        metadata = {"Fuente": "SSAS / CuboOnlineRetail / Online Retail", "Desde": str(filters.start), "Hasta": str(filters.end),
                    "Filtro país": labels["country"].get(country, "Todos"),
                    "Filtro producto": labels["product"].get(product, "Todos"),
                    "Filtro tipo": labels["type"].get(operation_type, "Todos"), "Consulta": detail_time}
        export = csv_bytes(rows, group, metadata)
        st.download_button("Descargar resultado filtrado (CSV)", export, "online_retail_agregado.csv", "text/csv",
                           key="export_csv", disabled=not rows)
        st.caption(f"{len(rows):,} filas agregadas · CSV UTF-8 con importe decimal de cuatro posiciones. "
                   "No sumar facturas distintas entre filas para obtener el total.")
        with st.expander("Definiciones, procedencia y límites"):
            st.markdown("""
**Toda la información procede del cubo mediante MDX.** No se consulta SQL relacional ni se descargan operaciones individuales.

- **Operaciones:** Count de OperacionKey; **cantidad firmada:** suma de cantidades conservando el signo.
- **Ventas y cargos:** importe del tipo 1. **Cancelacion:** importe del tipo 2, ya negativo.
- **Neto definido:** tipo 1 + tipo 2; excluye ajustes contables, precio cero y Por revisar.
- **Ajustes contables:** importe del tipo 3. **Precio cero:** conteo del tipo 4. **Por revisar:** conteo del tipo 5.
- **Facturas distintas:** DistinctCount calculado por el cubo para el contexto completo. Nunca se suman conteos parciales.
- Las medidas por tipo fijo **reemplazan el filtro Tipo de operación** de la misma jerarquía; las otras dimensiones se conservan.
- SIN_IDENTIFICAR representa cliente desconocido. No se muestra como cliente identificado ni se infiere una categoría para Por clasificar.
- MOLAP refleja el último procesamiento, no cambios posteriores del DW. Consultas en caché hasta 30 segundos; catálogo hasta 120.
- Indicadores, tabla y CSV conservan Decimal; la geometría del gráfico usa float únicamente para dibujar. La moneda no está documentada.
""")
    except (CubeError, ValueError, OSError) as exc:
        logging.exception("Fallo de consulta o configuración del dashboard")
        st.error("No fue posible consultar Analysis Services. Revise el servicio local, el procesamiento del cubo y la ruta ADOMD. "
                 "No se sustituyeron los datos por SQL ni por valores de ejemplo.")
        with st.expander("Detalle del error"):
            st.code(str(exc))


main()
