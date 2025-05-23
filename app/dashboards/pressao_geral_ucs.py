# app/dashboards/ap_pressao_ucs.py
"""
Dashboard – Pressão Geral em Unidades de Conservação
Rota Flask: /ap/pressao_ucs/
"""

# ─────────────────────────── imports ────────────────────────────
from __future__ import annotations

import io
import os
import tempfile
import requests

import dash
import dash_bootstrap_components as dbc
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import unidecode
from dash import html, dcc, Input, Output, State

# ───────────────────── helpers de download ──────────────────────
HEADERS = {"User-Agent": "Mozilla/5.0"}

def _tmp_from_url(url: str, suffix: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    f.write(r.content); f.close()
    return f.name

def load_geojson(url: str):
    try:
        return gpd.read_file(url)
    except Exception:
        try:
            p = _tmp_from_url(url, ".geojson")
            gdf = gpd.read_file(p); os.unlink(p); return gdf
        except Exception:
            return None

def load_parquet(url: str) -> pd.DataFrame | None:
    try:
        return pd.read_parquet(url)
    except Exception:
        try:
            buf = io.BytesIO(requests.get(url, headers=HEADERS, timeout=30).content)
            return pd.read_parquet(buf)
        except Exception:
            return None

# ───────────────────── URLs fontes ──────────────────────────────
GEOJSON_URLS = [
    "https://cdn.jsdelivr.net/gh/imazon-cgi/ap@main/"
    "dataset/geojson/PRESSAO_GERAL_UCs.geojson",
    "https://raw.githubusercontent.com/imazon-cgi/ap/main/"
    "dataset/geojson/PRESSAO_GERAL_UCs.geojson",
]
PARQUET_URLS = [
    "https://cdn.jsdelivr.net/gh/imazon-cgi/ap@main/"
    "dataset/csv/PRESSAO_GERAL_UCs.parquet",
    "https://github.com/imazon-cgi/ap/raw/refs/heads/main/"
    "dataset/csv/PRESSAO_GERAL_UCs.parquet",
]

# ───────────────────── carrega datasets ─────────────────────────

def load_df(url):
    return pd.read_parquet(url)

# Carregamento dos dados
roi = load_geojson("https://raw.githubusercontent.com/imazon-cgi/ap/main/dataset/geojson/PRESSAO_GERAL_UCs.geojson")
roi['NOME'] = roi['NOME'].str.upper().apply(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
roi = roi.sort_values(by='RANK')

df = load_df('https://github.com/imazon-cgi/ap/raw/refs/heads/main/dataset/csv/PRESSAO_GERAL_UCs.parquet')
df['NOME'] = df['NOME'].str.upper().apply(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
df = df.sort_values(by='RANK')

# normaliza texto
roi["NOME"] = roi["NOME"].str.upper().map(
    lambda x: unidecode.unidecode(x) if isinstance(x, str) else x
)
roi = roi.sort_values("RANK")

df["NOME"] = df["NOME"].str.upper().map(
    lambda x: unidecode.unidecode(x) if isinstance(x, str) else x
)
df = df.sort_values("RANK")

# ───────────────────── listas de filtros ────────────────────────
STATE_OPTS = [{"label": s, "value": s} for s in sorted(df["UF"].dropna().unique())]
MODAL_OPTS = [{"label": "UC Federal", "value": "UC Federal"},
              {"label": "UC Estadual", "value": "UC Estadual"}]
USO_OPTS   = [{"label": "Uso Sustentável",   "value": "Uso Sustentavel"},
              {"label": "Proteção Integral", "value": "Protecao Integral"}]

# ╭───────────────────────────────────────────────────────────────╮
# │ Função pública – registra o dashboard                         │
# ╰───────────────────────────────────────────────────────────────╯
def register_pressao_ucs(flask_server):
    dash_app = dash.Dash(
        __name__,
        server=flask_server,
        url_base_pathname="/ap/pressao_ucs/",
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css",
        ],
        suppress_callback_exceptions=True,
        title="Pressão UCs – Amazônia",
    )

    # ───────────────── layout ────────────────────────────────
    dash_app.layout = dbc.Container(
        [
            html.Meta(name="viewport", content="width=device-width, initial-scale=1"),

            # -------- filtros --------
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H1("Análise de Pressão de Desmatamento - Amazônia Legal",
                                        className="text-center mb-4"),
                                dbc.Row(
                                    [
                                        dbc.Col(html.Label("Modalidade:", className="fw-bold"), width="auto"),
                                        dbc.Col(dcc.Dropdown(id="modalidade", options=MODAL_OPTS,
                                                             value="UC Federal", clearable=False), width=3),

                                        dbc.Col(html.Label("Uso:", className="fw-bold"), width="auto"),
                                        dbc.Col(dcc.Dropdown(id="uso", options=USO_OPTS,
                                                             value="Uso Sustentavel", clearable=False), width=3),

                                        dbc.Col(html.Label("UF:", className="fw-bold"), width="auto"),
                                        dbc.Col(dcc.Dropdown(id="uf", options=STATE_OPTS,
                                                             multi=True, placeholder="Selecione"), width=3),

                                        dbc.Col(dbc.Button([html.I(className="fa fa-filter mr-1"),
                                                            "Remover Filtros"],
                                                           id="reset", color="primary",
                                                           className="btn-sm"), width="auto"),

                                        dbc.Col(dbc.Button([html.I(className="fa fa-download mr-1"),
                                                            "Baixar CSV"],
                                                           id="open-modal", color="secondary",
                                                           className="btn-sm"), width="auto"),
                                    ],
                                    justify="end",
                                    className="mb-3 align-items-center",
                                ),
                            ]
                        ),
                        className="mb-4",
                    )
                )
            ),
            dcc.Download(id="download-csv"),

            # -------- gráficos principais --------
            dbc.Row(
                [
                    dbc.Col(dbc.Card(dcc.Graph(id="bar"),  className="graph-block"), width=12, lg=6),
                    dbc.Col(dbc.Card(dcc.Graph(id="map"),  className="graph-block"), width=12, lg=6),
                ],
                className="mb-4",
            ),
            dcc.Store(id="selecionados", data=[]),

            dbc.Row(
                [
                    dbc.Col(dbc.Card(dcc.Graph(id="pie-uso"), className="graph-block"), width=12, lg=6),
                    dbc.Col(dbc.Card(dcc.Graph(id="pie-uc"),  className="graph-block"), width=12, lg=6),
                ],
                className="mb-4",
            ),

            # -------- tabela --------
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Top 10 Áreas Protegidas Mais Afetadas"),
                            dbc.CardBody(dbc.Table(id="top10", bordered=True,
                                                   hover=True, responsive=True, striped=True)),
                        ],
                        className="mb-4",
                    )
                )
            ),

            # -------- modal CSV --------
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Unidades de Conservação – baixar CSV")),
                    dbc.ModalBody(
                        [
                            dbc.Checklist(options=STATE_OPTS, id="uf-check", inline=True),
                            html.Hr(),
                            html.Label("Configurações CSV"),
                            dbc.RadioItems(options=[{"label": "Ponto", "value": "."},
                                                    {"label": "Vírgula", "value": ","}],
                                           value=".", id="sep", inline=True),
                            dbc.Checkbox(label="Sem acentuação", id="no-acc", value=False),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("Download", id="dwn-btn", color="success"),
                            dbc.Button("Fechar", id="close-modal", color="danger"),
                        ]
                    ),
                ],
                id="modal",
                is_open=False,
            ),
        ],
        fluid=True,
    )

    # ───────────────── callbacks ───────────────────────────
    @dash_app.callback(
        [
            Output("bar", "figure"),
            Output("map", "figure"),
            Output("pie-uso", "figure"),
            Output("pie-uc", "figure"),
            Output("selecionados", "data"),
            Output("top10", "children"),
        ],
        [
            Input("modalidade", "value"),
            Input("uso", "value"),
            Input("uf", "value"),
            Input("reset", "n_clicks"),
            Input("bar", "clickData"),
            Input("map", "clickData"),
        ],
        State("selecionados", "data"),
    )
    def atualizar(modalidade, uso, uf, reset, bar_click, map_click, selecionados):
        selecionados = selecionados or []
        if reset:
            selecionados = []

        for click in (bar_click, map_click):
            if click:
                nome = click["points"][0].get("y") or click["points"][0].get("location")
                if nome:
                    selecionados = (
                        [n for n in selecionados if n != nome]
                        if nome in selecionados else selecionados + [nome]
                    )

        dff = df[(df["MODALIDADE"] == modalidade) & (df["USO"] == uso)]
        if uf:
            dff = dff[dff["UF"].isin(uf)]
        if selecionados:
            dff = dff[dff["NOME"].isin(selecionados)]

        top10 = dff.nlargest(10, "DESMATAM_1")

        # tabela
        thead = html.Thead(html.Tr([
            html.Th("Nome"), html.Th("Focos de Calor"), html.Th("Nº CAR"),
            html.Th("Área CAR"), html.Th("Estradas Não Oficiais")
        ]))
        tbody = html.Tbody([
            html.Tr([
                html.Td(r["NOME"]),
                html.Td(r["FOCOS DE C"]),
                html.Td(r["N DE CAR"]),
                html.Td(f"{r['CAR']:.2f} km²"),
                html.Td(f"{r['ESTRADAS N']:.2f} km"),
            ]) for _, r in top10.iterrows()
        ])
        tabela = dbc.Table([thead, tbody], bordered=True, hover=True,
                           responsive=True, striped=True)

        # barras
        bar = go.Figure(
            go.Bar(
                y=top10["NOME"], x=top10["DESMATAM_1"], orientation="h",
                marker_color=["green" if n in selecionados else "DarkSeaGreen"
                              for n in top10["NOME"]],
                text=[f"{v:.2f} km²" for v in top10["DESMATAM_1"]],
                textposition="auto",
            )
        )
        bar.update_yaxes(autorange="reversed")
        bar.update_layout(
            xaxis_title="Área (km²)", yaxis_title="Unidades de Conservação",
            bargap=0.1, font=dict(size=10),
            title=dict(text="Top 10 UCs por Desmatamento", x=0.5, xanchor="center"),
        )

        # mapa
        mapa = px.choropleth_mapbox(
            top10, geojson=roi, color="DESMATAM_1",
            locations="NOME", featureidkey="properties.NOME",
            mapbox_style="carto-positron",
            center=dict(lat=-14, lon=-55),
            color_continuous_scale="YlOrRd",
            zoom=4,
        )
        mapa.update_layout(
            title=dict(text="Mapa de Pressão de Desmatamento (km²)",
                       x=0.5, xanchor="center", font=dict(size=14)),
            margin=dict(r=0, t=50, l=0, b=0),
            mapbox=dict(style="open-street-map", zoom=3,
                        center=dict(lat=-14, lon=-55)),
        )

        # pizzas
        cores = px.colors.sequential.YlOrRd
        pie_uso = px.pie(top10, values="DESMATAM_1", names="UF",
                         color="CATEGORIA",
                         title="Pressão Desmatamento por Estado de Uso e Categoria")
        pie_uso.update_traces(textinfo="percent+label", marker=dict(colors=cores))

        pie_uc = px.pie(top10, values="DESMATAM_1", names="NOME",
                        color="USO", title="Pressão Desmatamento por Unidade de Conservação")
        pie_uc.update_traces(textinfo="percent+label", marker=dict(colors=cores))

        return bar, mapa, pie_uso, pie_uc, selecionados, tabela

    # -------- modal e download --------
    @dash_app.callback(
        Output("modal", "is_open"),
        [Input("open-modal", "n_clicks"), Input("close-modal", "n_clicks")],
        State("modal", "is_open"),
    )
    def modal_toggle(n_open, n_close, opened):
        return not opened if n_open or n_close else opened

    @dash_app.callback(
        Output("download-csv", "data"),
        Input("dwn-btn", "n_clicks"),
        State("sep", "value"), State("no-acc", "value"),
        prevent_initial_call=True,
    )
    def download_csv(n, sep, no_acc):
        if not n:
            return dash.no_update
        out = df.copy()
        if no_acc:
            out = out.applymap(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
        return dcc.send_data_frame(out.to_csv, "pressao_ucs.csv",
                                   sep=sep, index=False)

    return dash_app

