# app/dashboards/ap_ameaca_area_protecao.py
"""
Dashboard Ameaça Geral – Área de Proteção Ambiental (Amazônia Legal)
--------------------------------------------------------------------
Servido pelo Flask em  /ap/ameaca_geral_area_de_protecao/
"""

from __future__ import annotations

import io
from typing import List, Optional

import dash
import dash_bootstrap_components as dbc
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import unidecode
from dash import (
    dcc,
    html,
    Input,
    Output,
    State,
    callback_context,
)


# ╭──────────────────────────────────────────────────────────────────────────╮
# │ FUNÇÃO QUE REGISTRA O DASH NO FLASK                                      │
# ╰──────────────────────────────────────────────────────────────────────────╯
def register_ameaca_area_protecao(server) -> dash.Dash:
    """Cria o app Dash e o conecta ao objeto *server* (Flask)."""
    external_css = [
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css",
    ]

    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname="/ap/ameaca_geral_area_de_protecao/",
        external_stylesheets=external_css,
        suppress_callback_exceptions=True,
        title="Ameaça Geral – Área de Proteção",
    )

    # ╭─ utilidades de carga ────────────────────────────────────────────────╮
    def load_geojson(url: str):
        try:
            return gpd.read_file(url)
        except Exception as exc:
            print(f"Erro ao carregar {url}: {exc}")
            return None

    def load_parquet(url: str) -> pd.DataFrame:
        return pd.read_parquet(url)

    # ╭─ dados --------------------------------------------------------------╮
    roi = load_geojson(
        "https://raw.githubusercontent.com/imazon-cgi/ap/main/dataset/geojson/AMEACA_GERAL_Area_de_Protecao.geojson"
    )
    roi["NOME"] = (
        roi["NOME"].str.upper().apply(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
    )
    roi = roi.sort_values(by="RANK")

    df = load_parquet(
        "https://github.com/imazon-cgi/ap/raw/refs/heads/main/dataset/csv/AMEACA_GERAL_Area_de_Protecao.parquet"
    )
    df["NOME"] = (
        df["NOME"].str.upper().apply(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
    )
    df = df.sort_values(by="RANK")

    list_states: List[str] = sorted(df["UF"].dropna().unique())
    state_options = [{"label": s, "value": s} for s in list_states]

    modalidade_options = [
        {"label": "UC Federal", "value": "UC Federal"},
        {"label": "UC Estadual", "value": "UC Estadual"},
    ]
    uso_options = [
        {"label": "Uso Sustentavel", "value": "Uso Sustentavel"},
        {"label": "Protecao Integral", "value": "Protecao Integral"},
    ]

    # ╭─ layout (copiado do script original) ────────────────────────────────╮
    app.layout = dbc.Container(
        [
            html.Meta(name="viewport", content="width=device-width, initial-scale=1"),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H1(
                                            "Análise de Ameaça de Desmatamento - Amazônia Legal",
                                            className="text-center mb-4",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    html.Label("Modalidade:", className="fw-bold"),
                                                    width="auto",
                                                    className="align-self-center",
                                                ),
                                                dbc.Col(
                                                    dcc.Dropdown(
                                                        id="modalidade-dropdown",
                                                        options=modalidade_options,
                                                        multi=True,
                                                        placeholder="Selecione a modalidade",
                                                    ),
                                                    width=3,
                                                ),
                                                dbc.Col(
                                                    html.Label("Uso:", className="fw-bold"),
                                                    width="auto",
                                                    className="align-self-center",
                                                ),
                                                dbc.Col(
                                                    dcc.Dropdown(
                                                        id="uso-dropdown",
                                                        options=uso_options,
                                                        multi=True,
                                                        placeholder="Selecione o uso",
                                                    ),
                                                    width=3,
                                                ),
                                                dbc.Col(
                                                    html.Label("UF:", className="fw-bold"),
                                                    width="auto",
                                                    className="align-self-center",
                                                ),
                                                dbc.Col(
                                                    dcc.Dropdown(
                                                        id="state-dropdown",
                                                        options=state_options,
                                                        multi=True,
                                                        placeholder="Selecione o(s) Estado(s)",
                                                    ),
                                                    width=3,
                                                ),
                                                dbc.Col(
                                                    dbc.Button(
                                                        [
                                                            html.I(className="fa fa-filter mr-1"),
                                                            "Remover Filtros",
                                                        ],
                                                        id="reset-button",
                                                        color="primary",
                                                        className="btn-sm custom-button",
                                                    ),
                                                    width="auto",
                                                    className="d-flex justify-content-end",
                                                ),
                                                dbc.Col(
                                                    dbc.Button(
                                                        [
                                                            html.I(className="fa fa-download mr-1"),
                                                            "Baixar CSV",
                                                        ],
                                                        id="open-modal-button",
                                                        color="secondary",
                                                        className="btn-sm custom-button",
                                                    ),
                                                    width="auto",
                                                    className="d-flex justify-content-end",
                                                ),
                                            ],
                                            justify="end",
                                            className="mb-3 align-items-center",
                                        ),
                                    ]
                                )
                            ],
                            className="mb-4 title-card",
                        ),
                        width=12,
                    )
                ]
            ),
            dcc.Download(id="download-dataframe-csv"),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card([dcc.Graph(id="bar-graph")], className="graph-block"),
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        dbc.Card([dcc.Graph(id="map-graph")], className="graph-block"),
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
                        dbc.Card([dcc.Graph(id="pie-uso-graph")], className="graph-block"),
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        dbc.Card([dcc.Graph(id="pie-unid-graph")], className="graph-block"),
                        width=12,
                        lg=6,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Top 10 Áreas Protegidas Mais Afetadas"),
                                dbc.CardBody(
                                    [dbc.Table(id="top-10-table", bordered=True, hover=True, responsive=True, striped=True)]
                                ),
                            ],
                            className="mb-4",
                        )
                    )
                ]
            ),
            # ------------------------ modais (sem alteração) -----------------
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("Escolha Área de Proteção Ambiental da Amazônia Legal")
                    ),
                    dbc.ModalBody(
                        [
                            dcc.Dropdown(
                                options=state_options,
                                id="state-dropdown-modal",
                                placeholder="Selecione o Estado",
                                multi=True,
                            )
                        ]
                    ),
                    dbc.ModalFooter(
                        [dbc.Button("Fechar", id="close-state-modal-button", color="danger")]
                    ),
                ],
                id="state-modal",
                is_open=False,
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("Escolha as Área de Proteção Ambiental da Amazônia Legal")
                    ),
                    dbc.ModalBody(
                        [
                            dbc.Checklist(options=state_options, id="state-checklist", inline=True),
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
                                        label="Sem acentuação", id="remove-accents", value=False
                                    ),
                                ]
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("Download", id="download-button", className="mr-2", color="success"),
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

    # ╭─ callbacks (lógica igual ao original) ───────────────────────────────╮
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
        [State("selected-states", "data")],
    )
    def update_graphs(
        modalidade, uso, states, reset_clicks, bar_click_data, map_click_data, selected_states
    ):
        # ── reset de filtros
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

        # ---------------- filtragem ----------------------------------------
        filtered_df = df.copy()

        if modalidade:
            modalidade = modalidade if isinstance(modalidade, list) else [modalidade]
            filtered_df = filtered_df[filtered_df["MODALIDADE"].isin(modalidade)]

        if uso:
            uso = uso if isinstance(uso, list) else [uso]
            filtered_df = filtered_df[filtered_df["USO"].isin(uso)]

        if states:
            filtered_df = filtered_df[filtered_df["UF"].isin(states)]

        if selected_states:
            filtered_df = filtered_df[filtered_df["NOME"].isin(selected_states)]

        # ---------------- top-10 e tabela ----------------------------------
        top_10 = filtered_df.nlargest(10, "DESMATAM_1")

        table_header = html.Thead(
            html.Tr(
                [
                    html.Th("Nome"),
                    html.Th("Focos de Calor"),
                    html.Th("Número de CAR"),
                    html.Th("Área de CAR"),
                    html.Th("Estradas Não Oficiais"),
                ]
            )
        )
        table_body = [
            html.Tr(
                [
                    html.Td(row["NOME"]),
                    html.Td(row["FOCOS DE C"]),
                    html.Td(row["N DE CAR"]),
                    html.Td(f"{row['CAR']:.2f} km²"),
                    html.Td(f"{row['ESTRADAS N']:.2f} km"),
                ]
            )
            for _, row in top_10.iterrows()
        ]
        table_component = dbc.Table(
            [table_header, html.Tbody(table_body)],
            bordered=True,
            hover=True,
            responsive=True,
            striped=True,
        )

        # ---------------- gráfico de barras --------------------------------
        bar_colors = ["green" if n in selected_states else "DarkSeaGreen" for n in top_10["NOME"]]
        bar_fig = go.Figure(
            go.Bar(
                y=top_10["NOME"],
                x=top_10["DESMATAM_1"],
                orientation="h",
                marker_color=bar_colors,
                text=[f"{v:.2f} km²" for v in top_10["DESMATAM_1"]],
                textposition="auto",
            )
        )
        bar_fig.update_yaxes(autorange="reversed")
        bar_fig.update_layout(
            xaxis_title="Área (km²)",
            yaxis_title="Área de Proteção Ambiental",
            bargap=0.1,
            font=dict(size=10),
            title=dict(
                text="Top 10 Área de Proteção Ambiental por Desmatamento",
                x=0.5,
                xanchor="center",
                yanchor="top",
            ),
        )

        # ---------------- mapa ---------------------------------------------
        map_fig = px.choropleth_mapbox(
            top_10,
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
                yanchor="top",
                font=dict(size=14),
            ),
            margin=dict(r=0, t=50, l=0, b=0),
            mapbox=dict(zoom=3, center=dict(lat=-14, lon=-55), style="open-street-map"),
        )

        # ---------------- pizzas -------------------------------------------
        pie_colors = px.colors.sequential.YlOrRd
        pie_uso_fig = px.pie(
            top_10,
            values="DESMATAM_1",
            names="UF",
            color="MODALIDADE",
            title="Ameaça Desmatamento por Estado de Uso e Categoria",
        )
        pie_uso_fig.update_traces(textinfo="percent+label", marker=dict(colors=pie_colors))

        pie_unid_fig = px.pie(
            top_10,
            values="DESMATAM_1",
            names="NOME",
            color="UF",
            title="Ameaça Desmatamento por Terra Indígena",
        )
        pie_unid_fig.update_traces(
            textinfo="none",
            hoverinfo="label+value+percent",
            marker=dict(colors=pie_colors),
        )

        return bar_fig, map_fig, pie_uso_fig, pie_unid_fig, selected_states, table_component

    # ---------- abrir/fechar modal de download -----------------------------
    @app.callback(
        Output("modal", "is_open"),
        [Input("open-modal-button", "n_clicks"), Input("close-modal-button", "n_clicks")],
        [State("modal", "is_open")],
    )
    def toggle_modal(n1, n2, is_open):
        if n1 or n2:
            return not is_open
        return is_open

    # ---------- download CSV ----------------------------------------------
    @app.callback(
        Output("download-dataframe-csv", "data"),
        Input("download-button", "n_clicks"),
        State("decimal-separator", "value"),
        State("remove-accents", "value"),
    )
    def download_csv(n_clicks, decimal_separator, remove_accents):
        if not n_clicks:
            return dash.no_update

        export_df = df.copy()
        if remove_accents:
            export_df = export_df.applymap(
                lambda x: unidecode.unidecode(x) if isinstance(x, str) else x
            )

        buff = io.StringIO()
        export_df.to_csv(buff, index=False, sep=decimal_separator)
        buff.seek(0)
        return dcc.send_data_frame(export_df.to_csv, "ameaca_area_protecao.csv", sep=decimal_separator)

    # ----------------------------------------------------------------------
    return app
