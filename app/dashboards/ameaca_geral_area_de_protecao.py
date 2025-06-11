# app/dashboards/ap_ameaca_area_protecao.py
"""
Dashboard Ameaça Geral – Área de Proteção Ambiental (Amazônia Legal)
--------------------------------------------------------------------
Servido pelo Flask em /ap/ameaca_geral_area_de_protecao/
"""

# ─────────────────────────── imports ────────────────────────────
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
)

# ╭───────────────────────────────────────────────────────────────╮
# │ Função que registra o dashboard no Flask                      │
# ╰───────────────────────────────────────────────────────────────╯
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

    # ╭─ utilidades de carga ─────────────────────────────────────╮
    def load_geojson(url: str):
        try:
            return gpd.read_file(url)
        except Exception as exc:
            print(f"Erro ao carregar {url}: {exc}")
            return None

    def load_parquet(url: str) -> pd.DataFrame:
        return pd.read_parquet(url)

    # ╭─ dados ---------------------------------------------------╮
    roi = load_geojson(
        "https://raw.githubusercontent.com/imazon-cgi/ap/main/dataset/geojson/AMEACA_GERAL_Area_de_Protecao.geojson"
    )
    roi["NOME"] = (
        roi["NOME"]
        .str.upper()
        .apply(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
    )
    roi = roi.sort_values(by="RANK")

    df = load_parquet(
        "https://github.com/imazon-cgi/ap/raw/refs/heads/main/dataset/csv/AMEACA_GERAL_Area_de_Protecao.parquet"
    )
    df["NOME"] = (
        df["NOME"]
        .str.upper()
        .apply(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
    )
    df = df.sort_values(by="RANK")

    list_states: List[str] = sorted(df["UF"].dropna().unique())
    state_options = [{"label": s, "value": s} for s in list_states]

    modalidade_options = [
        {"label": "UC Federal", "value": "UC Federal"},
        {"label": "UC Estadual", "value": "UC Estadual"},
    ]
    uso_options = [
        {"label": "Uso Sustentável",   "value": "Uso Sustentavel"},
        {"label": "Proteção Integral", "value": "Protecao Integral"},
    ]

    # ╭─ layout ──────────────────────────────────────────────────╮
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
                                                options=modalidade_options,
                                                multi=True,
                                                placeholder="Selecione a modalidade",
                                                className="filter-dropdown",
                                            ),
                                        ],
                                        xs=12,
                                        sm=6,
                                        md=4,
                                        className="mb-2",
                                    ),
                                    # Uso
                                    dbc.Col(
                                        [
                                            html.Label("Uso:", className="filter-label fw-bold"),
                                            dcc.Dropdown(
                                                id="uso-dropdown",
                                                options=uso_options,
                                                multi=True,
                                                placeholder="Selecione o uso",
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
                                                options=state_options,
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
                        dbc.Card(dcc.Graph(id="bar-graph"), className="graph-block"),
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        dbc.Card(dcc.Graph(id="map-graph"), className="graph-block"),
                        width=12,
                        lg=6,
                    ),
                ],
                className="mb-4",
                style={"border": "none"},
            ),

            dcc.Store(id="selected-states", data=[]),

            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(dcc.Graph(id="pie-uso-graph"), className="graph-block"),
                        width=12,
                        lg=6,
                    ),
                    dbc.Col(
                        dbc.Card(dcc.Graph(id="pie-unid-graph"), className="graph-block"),
                        width=12,
                        lg=6,
                    ),
                ],
                className="mb-4",
                style={"border": "none"},
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
                    )
                )
            ),

            # -------- modal CSV --------
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("Escolha as Áreas de Proteção Ambiental")
                    ),
                    dbc.ModalBody(
                        [
                            dbc.Checklist(
                                options=state_options,
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

    # ╭─ callbacks principais ───────────────────────────────────────────────╮
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
        Filtra dataframe, atualiza gráficos e tabela, controla seleção
        interativa (clique em barra ou mapa).
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

        # --- filtragem ------------------------------------------------------
        dff = df.copy()

        if modalidade:
            modalidade = modalidade if isinstance(modalidade, list) else [modalidade]
            dff = dff[dff["MODALIDADE"].isin(modalidade)]

        if uso:
            uso = uso if isinstance(uso, list) else [uso]
            dff = dff[dff["USO"].isin(uso)]

        if states:
            states = states if isinstance(states, list) else [states]
            dff = dff[dff["UF"].isin(states)]

        if selected_states:
            dff = dff[dff["NOME"].isin(selected_states)]

        # --- top-10 e tabela -----------------------------------------------
        top_10 = dff.nlargest(10, "DESMATAM_1")

        thead = html.Thead(
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
                for _, r in top_10.iterrows()
            ]
        )
        table_component = dbc.Table(
            [thead, tbody],
            bordered=False,
            hover=True,
            responsive=True,
            striped=True,
            style={"border": "none"},
        )

        # --- gráfico de barras ---------------------------------------------
        bar_colors = [
            "green" if nome in selected_states else "DarkSeaGreen"
            for nome in top_10["NOME"]
        ]
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
            yaxis_title="Áreas de Proteção Ambiental",
            bargap=0.1,
            font=dict(size=10),
            
            title={
                "text": "Top 10 Áreas de Proteção Ambiental<br>por Desmatamento",
                "x": 0.5,
                "xanchor": "center",
            }
        )

        # --- mapa -----------------------------------------------------------
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
                font=dict(size=14),
            ),
            margin=dict(r=0, t=50, l=0, b=0),
            mapbox=dict(zoom=3, center=dict(lat=-14, lon=-55), style="open-street-map"),
        )

        # --- pizzas ---------------------------------------------------------
        pie_colors = px.colors.sequential.YlOrRd
        pie_uso_fig = px.pie(
            top_10,
            values="DESMATAM_1",
            names="UF",
            color="MODALIDADE",
            title="Ameaça Desmatamento por Estado e Modalidade",
        )
        pie_uso_fig.update_layout(
            title_x=0.5,
            title_xanchor="center"
        )
        pie_uso_fig.update_traces(textinfo="percent+label", marker=dict(colors=pie_colors))

        pie_unid_fig = px.pie(
            top_10,
            values="DESMATAM_1",
            names="NOME",
            color="UF",
            title="Ameaça Desmatamento por Área de Proteção",
        )
        pie_unid_fig.update_layout(
            title_x=0.5,
            title_xanchor="center"
        )
        pie_unid_fig.update_traces(
            textinfo="percent+label", marker=dict(colors=pie_colors)
        )

        return bar_fig, map_fig, pie_uso_fig, pie_unid_fig, selected_states, table_component

    # ╭─ modal CSV ──────────────────────────────────────────────────────────╮
    @app.callback(
        Output("modal", "is_open"),
        [
            Input("open-modal-button", "n_clicks"),
            Input("close-modal-button", "n_clicks"),
        ],
        State("modal", "is_open"),
    )
    def toggle_modal(n_open, n_close, opened):
        """Abre / fecha o modal de download."""
        return not opened if n_open or n_close else opened

    # ╭─ download CSV ───────────────────────────────────────────────────────╮
    @app.callback(
        Output("download-dataframe-csv", "data"),
        Input("download-button", "n_clicks"),
        State("decimal-separator", "value"),
        State("remove-accents", "value"),
        prevent_initial_call=True,
    )
    def download_csv(n_clicks, decimal_sep, remove_accents):
        """Gera CSV com as opções do modal."""
        if not n_clicks:
            return dash.no_update

        export_df = df.copy()
        if remove_accents:
            export_df = export_df.applymap(
                lambda x: unidecode.unidecode(x) if isinstance(x, str) else x
            )

        return dcc.send_data_frame(
            export_df.to_csv,
            "ameaca_area_protecao.csv",
            sep=decimal_sep,
            index=False,
        )

    # ----------------------------------------------------------------------
    return app
