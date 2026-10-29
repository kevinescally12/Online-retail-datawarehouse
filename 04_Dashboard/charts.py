"""Presentación categórica del ranking; recibe únicamente agregados ya consultados."""
from html import escape
import plotly.graph_objects as go
from presentation import number


def product_descriptions(product_members):
    """Reutiliza el catálogo existente: código · descripción completa · categoría."""
    descriptions = {}
    for member in product_members:
        code, separator, remainder = member["label"].partition(" · ")
        if separator:
            description, category_separator, _ = remainder.rpartition(" · ")
            descriptions[code] = description if category_separator else remainder
    return descriptions


def product_ranking(rows, descriptions):
    # Ordena por el Decimal original; convertir códigos a int/float perdería su identidad.
    ordered = sorted(rows, key=lambda row: (row["Importe"] is None,
                     -row["Importe"] if row["Importe"] is not None else 0,
                     str(row["Código de producto"])))
    codes = [str(row["Código de producto"]) for row in ordered]
    custom = [[escape(code), escape(descriptions.get(code, "Descripción no disponible en el catálogo")),
               escape(str(row.get("Categoría", ""))), number(row["Importe"], True)]
              for code, row in zip(codes, ordered)]
    fig = go.Figure(go.Bar(
        x=[float(row["Importe"]) if row["Importe"] is not None else None for row in ordered], y=codes,
        orientation="h", marker_color="#087f8c", customdata=custom,
        hovertemplate="Código: %{customdata[0]}<br>Descripción: %{customdata[1]}"
                      "<br>Categoría: %{customdata[2]}<br>Importe: %{customdata[3]}<extra></extra>",
    ))
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=codes,
                     autorange="reversed", tickmode="array", tickvals=codes,
                     ticktext=[escape(code) for code in codes], tickfont_size=12, automargin=True)
    fig.update_xaxes(type="linear", title="Importe con signo · unidades monetarias")
    fig.update_layout(height=max(270, 130 + 34 * len(codes)), bargap=0.24,
                      margin=dict(l=15, r=15, t=10, b=45), yaxis_title="Código de producto",
                      hoverlabel=dict(align="left"), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)")
    return fig
