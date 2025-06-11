# app/dashboards/ap_ameaca_terra_indigena.py
"""
Dashboard – Ameaça Geral em Terras Indígenas
Rota Flask: /ap/ameaca_terra_indigena/
"""

# ───────────────────────── imports ─────────────────────────
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

# ───────────── helpers de download (dribla HTTP-429) ───────
HEADERS = {"User-Agent": "Mozilla/5.0"}


def _download_tmp(url: str, suffix: str) -> str:
    """
    Faz download para um arquivo temporário quando a leitura direta
    (GitHub Raw / CDN) retorna erro HTTP-429.
    """
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(r.content)
    tmp.close()

    return tmp.name


def load_geojson(url: str):
    """Lê GeoJSON da URL ou (fallback) do arquivo temporário."""
    try:
        return gpd.read_file(url)
    except Exception:
        try:
            p = _download_tmp(url, ".geojson")
            gdf = gpd.read_file(p)
            os.unlink(p)
            return gdf
        except Exception:
            return None


def load_parquet(url: str) -> pd.DataFrame | None:
    """Lê Parquet direto da URL (ou buffer em memória)."""
    try:
        return pd.read_parquet(url)
    except Exception:
        try:
            buf = io.BytesIO(requests.get(url, headers=HEADERS, timeout=30).content)
            return pd.read_parquet(buf)
        except Exception:
            return None


# ───────────── URLs (CDN primeiro, GitHub Raw depois) ────────
GEOJSON_URLS = [
    "https://cdn.jsdelivr.net/gh/imazon-cgi/ap@main/"
    "dataset/geojson/AMEACA_GERAL_Terra_indigena.geojson",
    "https://raw.githubusercontent.com/imazon-cgi/ap/main/"
    "dataset/geojson/AMEACA_GERAL_Terra_indigena.geojson",
]

PARQUET_URLS = [
    "https://cdn.jsdelivr.net/gh/imazon-cgi/ap@main/"
    "dataset/csv/AMEACA_GERAL_Terra_indigena.parquet",
    "https://github.com/imazon-cgi/ap/raw/refs/heads/main/"
    "dataset/csv/AMEACA_GERAL_Terra_indigena.parquet",
]

# ───────────── carrega datasets ─────────────────────────────
def load_df(url: str) -> pd.DataFrame:
    return pd.read_parquet(url)


# GeoJSON (região) -------------------------------------------------------------
roi = load_geojson(
    "https://raw.githubusercontent.com/imazon-cgi/ap/main/"
    "dataset/geojson/AMEACA_GERAL_Terra_indigena.geojson"
)

roi["NOME"] = (
    roi["NOME"]
    .str.upper()
    .apply(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
)
roi = roi.sort_values(by="RANK")

# Parquet (métricas) -----------------------------------------------------------
df = load_df(
    "https://github.com/imazon-cgi/ap/raw/refs/heads/main/"
    "dataset/csv/AMEACA_GERAL_Terra_indigena.parquet"
)

df["NOME"] = (
    df["NOME"]
    .str.upper()
    .apply(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
)
df = df.sort_values(by="RANK")

# ───────────── opções de filtros ────────────────────────────
STATE_OPTS = [{"label": s, "value": s} for s in sorted(df["UF"].dropna().unique())]

MODAL_OPTS = [{"label": "Terra Indígena", "value": "Terra Indigena"}]

FASE_OPTS = [
    {"label": "Regularizada",    "value": "Regularizada"},
    {"label": "Declarada",       "value": "Declarada"},
    {"label": "Delimitada",      "value": "Delimitada"},
    {"label": "Em Estudo",       "value": "Em Estudo"},
    {"label": "Homologada",      "value": "Homologada"},
    {"label": "Encaminhada RI",  "value": "Encaminhada RI"},
]

# ╭──────────────────────────────────────────────────────────╮
# │ função pública – registra o dashboard                   │
# ╰──────────────────────────────────────────────────────────╯
def register_ameaca_terra_indigena(flask_server):
    app = dash.Dash(
        __name__,
        server=flask_server,
        url_base_pathname="/ap/ameaca_terra_indigena/",
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css",
        ],
        suppress_callback_exceptions=True,
        title="Ameaça TI – Amazônia",
    )

    # ───────────── layout ────────────────────────────────
    app.layout = dbc.Container(
        [
            html.Meta(name="viewport", content="width=device-width, initial-scale=1"),

            # -------- filtros --------
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            dbc.Row(
                                [
                                    # Modalidade
                                    dbc.Col(
                                        [
                                            html.Label("Modalidade:", className="filter-label fw-bold"),
                                            dcc.Dropdown(
                                                id="modalidade-dropdown",
                                                options=MODAL_OPTS,
                                                value="Terra Indigena",
                                                clearable=False,
                                                className="filter-dropdown",
                                            ),
                                        ],
                                        xs=12,
                                        sm=6,
                                        md=4,
                                        className="mb-2",
                                    ),

                                    # Fase
                                    dbc.Col(
                                        [
                                            html.Label("Fase:", className="filter-label fw-bold"),
                                            dcc.Dropdown(
                                                id="uso-dropdown",
                                                options=FASE_OPTS,
                                                multi=True,
                                                placeholder="Selecione a(s) Fase(s)",
                                                className="filter-dropdown",
                                            ),
                                        ],
                                        xs=12,
                                        sm=6,
                                        md=4,
                                        className="mb-2",
                                    ),

                                    # UF
                                    dbc.Col(
                                        [
                                            html.Label("UF:", className="filter-label fw-bold"),
                                            dcc.Dropdown(
                                                id="state-dropdown",
                                                options=STATE_OPTS,
                                                multi=True,
                                                placeholder="Selecione o(s) Estado(s)",
                                                className="filter-dropdown",
                                            ),
                                        ],
                                        xs=12,
                                        sm=6,
                                        md=4,
                                        className="mb-2",
                                    ),

                                    # Botão reset
                                    dbc.Col(
                                        dbc.Button(
                                            [html.I(className="fa fa-filter me-1"), "Remover Filtros"],
                                            id="reset-button",
                                            color="success",
                                            className="btn-sm w-100",
                                        ),
                                        xs=6,
                                        sm="auto",
                                        className="mb-2",
                                    ),

                                    # Botão CSV
                                    dbc.Col(
                                        dbc.Button(
                                            [html.I(className="fa fa-download me-1"), "Baixar CSV"],
                                            id="open-modal-button",
                                            color="success",
                                            className="btn-sm w-100",
                                        ),
                                        xs=6,
                                        sm="auto",
                                        className="mb-2",
                                    ),
                                ],
                                className="g-2 align-items-end",
                            ),
                            className="filter-card-body",
                        ),
                        className="mb-4",
                        style={"border": "none"},
                    )
                )
            ),

            dcc.Download(id="download-dataframe-csv"),

            # -------- gráficos principais --------
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(dcc.Graph(id="bar-graph"), className="graph-block", style={"border": "none"}),
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        dbc.Card(dcc.Graph(id="map-graph"), className="graph-block", style={"border": "none"}),
                        width=12,
                        lg=6,
                    ),
                ],
                className="mb-4",
            ),

            dcc.Store(id="selected-states", data=[]),

            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(dcc.Graph(id="pie-uso-graph"), className="graph-block", style={"border": "none"}),
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        dbc.Card(dcc.Graph(id="pie-unid-graph"), className="graph-block", style={"border": "none"}),
                        width=12,
                        lg=6,
                    ),
                ],
                className="mb-4",
            ),

            # -------- tabela --------
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Top 10 Áreas Protegidas Mais Afetadas"),
                            dbc.CardBody(
                                dbc.Table(
                                    id="top-10-table",
                                    bordered=False,
                                    hover=True,
                                    responsive=True,
                                    striped=True,
                                    style={"border": "none"},
                                )
                            ),
                        ],
                        className="mb-4",
                        style={"border": "none"},
                    ),
                    width=12,
                )
            ),

            # -------- modal CSV --------
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("Escolha as Unidades de Conservação da Amazônia Legal")
                    ),
                    dbc.ModalBody(
                        [
                            dbc.Checklist(
                                options=STATE_OPTS,
                                id="state-checklist",
                                inline=True,
                            ),
                            html.Hr(),
                            html.Div(
                                [
                                    html.Label("Configurações para gerar o CSV"),
                                    dbc.RadioItems(
                                        options=[
                                            {"label": "Ponto", "value": "."},
                                            {"label": "Vírgula", "value": ","},
                                        ],
                                        value=".",
                                        id="decimal-separator",
                                        inline=True,
                                        className="mb-2",
                                    ),
                                    dbc.Checkbox(
                                        label="Sem acentuação",
                                        id="remove-accents",
                                        value=False,
                                    ),
                                ]
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("Download", id="download-button", color="success"),
                            dbc.Button("Fechar", id="close-modal-button", color="danger"),
                        ]
                    ),
                ],
                id="modal",
                is_open=False,
            ),
        ],
        fluid=True,
    )

    # ───────────── callbacks principais ──────────────────
    @app.callback(
        [
            Output("bar-graph", "figure"),
            Output("map-graph", "figure"),
            Output("pie-uso-graph", "figure"),
            Output("pie-unid-graph", "figure"),
            Output("selected-states", "data"),
            Output("top-10-table", "children"),
        ],
        [
            Input("modalidade-dropdown", "value"),
            Input("uso-dropdown", "value"),
            Input("state-dropdown", "value"),
            Input("reset-button", "n_clicks"),
            Input("bar-graph", "clickData"),
            Input("map-graph", "clickData"),
        ],
        State("selected-states", "data"),
    )
    def update_graphs(
        modalidade,
        uso,
        states,
        reset_clicks,
        bar_click_data,
        map_click_data,
        selected_states,
    ):
        """
        Filtra o dataframe, atualiza gráficos, tabela e controla seleção
        (click em barra ou mapa).
        """
        selected_states = selected_states or []

        # reset
        if reset_clicks:
            selected_states = []

        # clique em barra
        if bar_click_data:
            clicked_name = bar_click_data["points"][0]["y"]
            if clicked_name in selected_states:
                selected_states.remove(clicked_name)
            else:
                selected_states.append(clicked_name)

        # clique no mapa
        if map_click_data:
            clicked_name = map_click_data["points"][0]["location"]
            if clicked_name in selected_states:
                selected_states.remove(clicked_name)
            else:
                selected_states.append(clicked_name)

        # filtra
        dff = df[df["MODALIDADE"] == modalidade]

        if uso:
            uso = uso if isinstance(uso, list) else [uso]
            if "FASE" in dff.columns:
                dff = dff[dff["FASE"].isin(uso)]

        if states:
            states = states if isinstance(states, list) else [states]
            dff = dff[dff["UF"].isin(states)]

        if selected_states:
            dff = dff[dff["NOME"].isin(selected_states)]

        top10 = dff.nlargest(10, "DESMATAM_1")

        # -------- tabela --------
        thead = html.Thead(
            html.Tr(
                [
                    html.Th("Nome"),
                    html.Th("Focos de Calor"),
                    html.Th("Nº CAR"),
                    html.Th("Área CAR"),
                    html.Th("Estradas Não Oficiais"),
                ]
            )
        )

        tbody = html.Tbody(
            [
                html.Tr(
                    [
                        html.Td(r["NOME"]),
                        html.Td(r["FOCOS DE C"]),
                        html.Td(r["N DE CAR"]),
                        html.Td(f"{r['CAR']:.2f} km²"),
                        html.Td(f"{r['ESTRADAS N']:.2f} km"),
                    ]
                )
                for _, r in top10.iterrows()
            ]
        )

        table = dbc.Table(
            [thead, tbody],
            bordered=False,
            hover=True,
            responsive=True,
            striped=True,
            style={"border": "none"},
        )

        # -------- barras --------
        bar_colors = [
            "green" if nome in selected_states else "DarkSeaGreen"
            for nome in top10["NOME"]
        ]

        bar_fig = go.Figure(
            go.Bar(
                y=top10["NOME"],
                x=top10["DESMATAM_1"],
                orientation="h",
                marker_color=bar_colors,
                text=[f"{v:.2f} km²" for v in top10["DESMATAM_1"]],
                textposition="auto",
            )
        )

        bar_fig.update_yaxes(autorange="reversed")

        bar_fig.update_layout(
            xaxis_title="Área (km²)",
            yaxis_title="Unidades de Conservação",
            bargap=0.1,
            font=dict(size=10),
            title=dict(
                text="Top 10 UCs <br> por Desmatamento",
                x=0.5,
                xanchor="center",
            ),
        )

        # -------- mapa --------
        map_fig = px.choropleth_mapbox(
            top10,
            geojson=roi,
            color="DESMATAM_1",
            locations="NOME",
            featureidkey="properties.NOME",
            mapbox_style="carto-positron",
            center=dict(lat=-14, lon=-55),
            color_continuous_scale="YlOrRd",
            zoom=4,
        )

        map_fig.update_layout(
            title=dict(
                text="Mapa de Ameaça de Desmatamento (km²)",
                x=0.5,
                xanchor="center",
                font=dict(size=14),
            ),
            margin=dict(r=0, t=50, l=0, b=0),
            mapbox=dict(
                style="open-street-map",
                zoom=3,
                center=dict(lat=-14, lon=-55),
            ),
        )

        # -------- pizzas --------
        cores = px.colors.sequential.YlOrRd

        pie_uso_fig = px.pie(
            top10,
            values="DESMATAM_1",
            names="UF",
            color="FASE",
            title="Ameaça Desmatamento por Estado e Fase",
        )
        pie_uso_fig.update_layout(
            title_x=0.5,
            title_xanchor="center"
        )
        pie_uso_fig.update_traces(textinfo="percent+label", marker=dict(colors=cores))

        pie_unid_fig = px.pie(
            top10,
            values="DESMATAM_1",
            names="NOME",
            color="FASE",
            title="Ameaça Desmatamento por Terra Indígena",
        )
        pie_unid_fig.update_layout(
            title_x=0.5,
            title_xanchor="center"
        )
        pie_unid_fig.update_traces(textinfo="percent+label", marker=dict(colors=cores))

        return bar_fig, map_fig, pie_uso_fig, pie_unid_fig, selected_states, table

    # ───────────── modal / download ──────────────────────
    @app.callback(
        Output("modal", "is_open"),
        [
            Input("open-modal-button", "n_clicks"),
            Input("close-modal-button", "n_clicks"),
        ],
        State("modal", "is_open"),
    )
    def toggle_modal(n_open, n_close, opened):
        """Abre/fecha o modal CSV."""
        return not opened if n_open or n_close else opened

    @app.callback(
        Output("download-dataframe-csv", "data"),
        Input("download-button", "n_clicks"),
        State("decimal-separator", "value"),
        State("remove-accents", "value"),
        prevent_initial_call=True,
    )
    def download_csv(n_clicks, decimal_separator, remove_accents):
        """Gera o CSV conforme opções do modal."""
        if not n_clicks:
            return dash.no_update

        out = df.copy()

        if remove_accents:
            out = out.applymap(
                lambda x: unidecode.unidecode(x) if isinstance(x, str) else x
            )

        return dcc.send_data_frame(
            out.to_csv,
            "ameaca_ti.csv",
            sep=decimal_separator,
            index=False,
        )

    return app
