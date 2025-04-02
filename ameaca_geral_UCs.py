# Ajustes realizados conforme solicitado pelo usuário

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Output, Input, State, callback_context
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import geopandas as gpd
import io
import unidecode

# Inicializa a aplicação Dash com tema Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css'])
server = app.server

# Função para carregar dados GeoJSON
def load_geojson(url):
    try:
        return gpd.read_file(url)
    except Exception as e:
        print(f"Erro ao carregar {url}: {e}")
        return None

# Função para carregar arquivo Parquet
def load_df(url):
    return pd.read_parquet(url)

# Carregamento dos dados
roi = load_geojson("https://raw.githubusercontent.com/imazon-cgi/ap/main/dataset/geojson/AMEACA_GERAL_UCs.geojson")
roi['NOME'] = roi['NOME'].str.upper().apply(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
roi = roi.sort_values(by='RANK')

df = load_df('https://github.com/imazon-cgi/ap/raw/refs/heads/main/dataset/csv/AMEACA_GERAL_UCs.parquet')
df['NOME'] = df['NOME'].str.upper().apply(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)
df = df.sort_values(by='RANK')

# Lista de estados (UF), removendo valores nulos
list_states = sorted(df['UF'].dropna().unique())
state_options = [{'label': state, 'value': state} for state in list_states]

# Definição das opções de filtro
modalidade_options = [
    {'label': 'UC Federal', 'value': 'UC Federal'},
    {'label': 'UC Estadual', 'value': 'UC Estadual'},
]
uso_options = [
    {'label': 'Uso Sustentavel', 'value': 'Uso Sustentavel'},
    {'label': 'Protecao Integral', 'value': 'Protecao Integral'},
]

# Layout da aplicação aprimorado
app.layout = dbc.Container([
    html.Meta(name="viewport", content="width=device-width, initial-scale=1"),
dbc.Row([
    dbc.Col(dbc.Card([
        dbc.CardBody([
            html.H1("Análise de Ameaça de Desmatamento - Amazônia Legal", className="text-center mb-4"),
            dbc.Row([
                dbc.Col(html.Label('Modalidade:', className="fw-bold"), width='auto', className="align-self-center"),
                dbc.Col(dcc.Dropdown(id='modalidade-dropdown', options=modalidade_options, value='UC Federal', clearable=False), width=3),
                dbc.Col(html.Label('Uso:', className="fw-bold"), width='auto', className="align-self-center"),
                dbc.Col(dcc.Dropdown(id='uso-dropdown', options=uso_options, value='Uso Sustentavel', clearable=False), width=3),
                dbc.Col(html.Label('UF:', className="fw-bold"), width='auto', className="align-self-center"),
                dbc.Col(dcc.Dropdown(id='state-dropdown', options=state_options, multi=True, placeholder="Selecione o(s) Estado(s)"), width=3),
                dbc.Col(
                    dbc.Button(
                        [html.I(className="fa fa-filter mr-1"), "Remover Filtros"],
                        id="reset-button", color="primary", className="btn-sm custom-button"
                    ), width="auto", className="d-flex justify-content-end"
                ),
               dbc.Col(
                    dbc.Button(
                        [html.I(className="fa fa-download mr-1"), "Baixar CSV"],
                        id="open-modal-button", color="secondary", className="btn-sm custom-button"
                    ), width="auto", className="d-flex justify-content-end"
                )
            ], justify="end", className='mb-3 align-items-center')
        ])
    ], className="mb-4 title-card"), width=12)
]),
dcc.Download(id="download-dataframe-csv"),
    dbc.Row([
        dbc.Col(dbc.Card([
            dcc.Graph(id='bar-graph')
        ], className="graph-block"), width=12, lg=6),
        dbc.Col(dbc.Card([
            dcc.Graph(id='map-graph')
        ], className="graph-block"), width=12, lg=6)
    ], className='mb-4'),
    dcc.Store(id='selected-states', data=[]),
    dbc.Row([
        dbc.Col(dbc.Card([
            dcc.Graph(id='pie-uso-graph')
        ], className="graph-block"), width=12, lg=6),
        dbc.Col(dbc.Card([
            dcc.Graph(id='pie-unid-graph')
        ], className="graph-block"), width=12, lg=6)
    ], className='mb-4'),
       # Tabela com as 10 áreas protegidas mais afetadas pelo desmatamento
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Top 10 Áreas Protegidas Mais Afetadas"),
            dbc.CardBody([
                dbc.Table(id='top-10-table', bordered=True, hover=True, responsive=True, striped=True)
            ])
        ], className="mb-4"))
    ]),
    dcc.Download(id="download-dataframe-csv"),
  dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Escolha Unidades de Conservação da Amazônia Legal")),
        dbc.ModalBody([
            dcc.Dropdown(
                options=state_options,
                id="state-dropdown-modal",
                placeholder="Selecione o Estado",
                multi=True
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Fechar", id="close-state-modal-button", color="danger")
        ])
    ], id="state-modal", is_open=False),
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Escolha as Unidades de Conservação da Amazônia Legal")),
        dbc.ModalBody([
            dbc.Checklist(
                options=state_options,
                id="state-checklist",
                inline=True
            ),
            html.Hr(),
            html.Div([
                html.Label("Configurações para gerar o CSV"),
                dbc.RadioItems(
                    options=[
                        {'label': 'Ponto', 'value': '.'},
                        {'label': 'Vírgula', 'value': ','},
                    ],
                    value='.',
                    id='decimal-separator',
                    inline=True,
                    className='mb-2'
                ),
                dbc.Checkbox(
                    label="Sem acentuação",
                    id="remove-accents",
                    value=False
                )
            ])
        ]),
        dbc.ModalFooter([
            dbc.Button("Download", id="download-button", className="mr-2", color="success"),
            dbc.Button("Fechar", id="close-modal-button", color="danger")
        ])
    ], id="modal", is_open=False)
], fluid=True)



# Callback para atualização dos gráficos
@app.callback(
    [Output('bar-graph', 'figure'), Output('map-graph', 'figure'), 
     Output('pie-uso-graph', 'figure'), Output('pie-unid-graph', 'figure'), 
     Output('selected-states', 'data'),Output('top-10-table', 'children')],
    [Input('modalidade-dropdown', 'value'), Input('uso-dropdown', 'value'), Input('state-dropdown', 'value'), 
     Input('reset-button', 'n_clicks'), Input('bar-graph', 'clickData'), Input('map-graph', 'clickData')],
    [State('selected-states', 'data')]
)
def update_graphs(modalidade, uso, states, reset_clicks, bar_click_data, map_click_data, selected_states):
       # Resetar filtros se o botão for clicado
    if reset_clicks:
        selected_states = []

    # Verificar clique no gráfico de barras
    if bar_click_data:
        clicked_name = bar_click_data['points'][0]['y']
        if clicked_name in selected_states:
            selected_states.remove(clicked_name)
        else:
            selected_states.append(clicked_name)

    # Verificar clique no mapa
    if map_click_data:
        clicked_name = map_click_data['points'][0]['location']
        if clicked_name in selected_states:
            selected_states.remove(clicked_name)
        else:
            selected_states.append(clicked_name)

    # Filtragem dos dados
    filtered_df = df[df['MODALIDADE'] == modalidade]
    filtered_df = filtered_df[filtered_df['USO'] == uso]

    if states:
        filtered_df = filtered_df[filtered_df['UF'].isin(states)]

    if selected_states:
        filtered_df = filtered_df[filtered_df['NOME'].isin(selected_states)]

    top_10 = filtered_df.nlargest(10, 'DESMATAM_1')
    
     # Criar tabela com os atributos solicitados
    table_header = [
        html.Thead(html.Tr([
            html.Th("Nome"), html.Th("Focos de Calor"), html.Th("Número de CAR"), html.Th("Área de CAR"), html.Th("Estradas Não Oficiais")
        ]))
    ]

    table_body = []
    for _, row in top_10.iterrows():
        table_body.append(html.Tr([
            html.Td(row['NOME']),
            html.Td(row['FOCOS DE C']),
            html.Td(row['N DE CAR']),
            html.Td(f"{row['CAR']:.2f} km²"),
            html.Td(f"{row['ESTRADAS N']:.2f} km")
        ]))

    table = dbc.Table(table_header + [html.Tbody(table_body)], bordered=True, hover=True, responsive=True, striped=True)


    # Gráfico de barras atualizado
    bar_colors = ['green' if nome in selected_states else 'DarkSeaGreen' for nome in top_10['NOME']]
    bar_fig = go.Figure(go.Bar(
        y=top_10['NOME'],
        x=top_10['DESMATAM_1'],
        orientation='h',
        marker_color=bar_colors,
        text=[f"{value:.2f} km²" for value in top_10['DESMATAM_1']],
        textposition='auto'
    ))

    # Inverter a ordem para que o maior valor fique no topo
    bar_fig.update_yaxes(autorange="reversed")

    bar_fig.update_layout(
        xaxis_title='Área (km²)',
        yaxis_title='Unidades de Conservação',
        bargap=0.1,
        font=dict(size=10),
        title={
            'text': f'Top 10 UCs por Desmatamento',
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )

    # Gráfico de mapa
    map_fig = px.choropleth_mapbox(
        top_10, geojson=roi, color='DESMATAM_1',
        locations="NOME", featureidkey="properties.NOME",
        mapbox_style="carto-positron",
        center={"lat": -14, "lon": -55},
        color_continuous_scale='YlOrRd',
        zoom=4
    )
    
    map_fig.update_layout(
        title={
            'text': f"Mapa de Ameaça de Desmatamento (km²)",
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 14}
        },
        margin={"r":0, "t":50, "l":0, "b":0},
        mapbox={
            'zoom': 3,
            'center': {"lat": -14, "lon": -55},
            'style': "open-street-map"
        }
    )

     # Gráfico de pizza - USO
    pie_colors = px.colors.sequential.YlOrRd
    pie_uso_fig = px.pie(top_10, values='DESMATAM_1', names='UF', color='CATEGORIA', title='Ameaça Desmatamento por Estado de Uso e Categoria')
    pie_uso_fig.update_traces(textinfo='percent+label', marker=dict(colors=pie_colors))

    # Gráfico de pizza - Unidade de Conservação
    pie_unid_fig = px.pie(top_10, values='DESMATAM_1', names='NOME', color='USO', title='Ameaça Desmatamento por Unidade de Conservação')
    pie_unid_fig.update_traces(textinfo='percent+label', marker=dict(colors=pie_colors))
    
    return bar_fig, map_fig, pie_uso_fig, pie_unid_fig, selected_states,table

# Callback para abrir e fechar o modal
@app.callback(
    Output("modal", "is_open"),
    [Input("open-modal-button", "n_clicks"), Input("close-modal-button", "n_clicks")],
    [State("modal", "is_open")]
)
def toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

# Callback para baixar o CSV
@app.callback(
    Output("download-dataframe-csv", "data"),
    [Input("download-button", "n_clicks")],
    [State("decimal-separator", "value"), State("remove-accents", "value")]
)
def download_csv(n_clicks, decimal_separator, remove_accents):
    if n_clicks is None:
        return dash.no_update

    filtered_df = df.copy()
    if remove_accents:
        filtered_df = filtered_df.applymap(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)

    csv_buffer = io.StringIO()
    filtered_df.to_csv(csv_buffer, index=False, sep=decimal_separator)
    csv_buffer.seek(0)

    return dcc.send_data_frame(filtered_df.to_csv, "desmatamento_ucs.csv", sep=decimal_separator)

# Executa a aplicação
if __name__ == '__main__':
    app.run_server(debug=True)
