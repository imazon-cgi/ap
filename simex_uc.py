# Ajustes realizados conforme solicitado pelo usuário

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Output, Input, State, callback_context
import plotly.express as px
import plotly.graph_objects as go
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


df = load_df('https://github.com/imazon-cgi/ap/raw/refs/heads/main/dataset/csv/AMEACA_GERAL_UCs.parquet')
df['NOME'] = df['NOME'].str.upper().apply(lambda x: unidecode.unidecode(x) if isinstance(x, str) else x)


# Converter CRS para projetado para calcular centroides corretamente

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
                dbc.Row([
                    dbc.Col(html.Label('Modalidade:'), width='auto'),
                    dbc.Col(dcc.Dropdown(id='modalidade-dropdown', options=[
                        {'label': 'UC Federal', 'value': 'UC Federal'},
                        {'label': 'UC Estadual', 'value': 'UC Estadual'}
                    ], value='UC Federal', clearable=False), width=4),
                    dbc.Col(html.Label('Uso:'), width='auto'),
                    dbc.Col(dcc.Dropdown(id='uso-dropdown', options=[
                        {'label': 'Uso Sustentável', 'value': 'Uso Sustentavel'},
                        {'label': 'Proteção Integral', 'value': 'Protecao Integral'},
                      
                    ], value='Protecao Integral', clearable=False), width=4)
                ], className='mb-4 align-items-center')
            ])
        ], className="mb-4 title-card"), width=12)
    ]),
    dbc.Row([
        dbc.Col(dbc.Card([
            dcc.Graph(id='bar-graph')
        ], className="graph-block"), width=12, lg=6),
        dbc.Col(dbc.Card([
            dcc.Graph(id='map-graph')
        ], className="graph-block"), width=12, lg=6)
    ], className='mb-4')
], fluid=True)

# Callback para atualização dos gráficos
@app.callback(
    [Output('bar-graph', 'figure'), Output('map-graph', 'figure')],
    [Input('modalidade-dropdown', 'value'), Input('uso-dropdown', 'value')]
)
def update_graphs(modalidade, uso):
    filtered_df = df[df['MODALIDADE'] == modalidade]
    filtered_df = filtered_df[filtered_df['USO'] == uso]
    top_10 = filtered_df.sort_values(by='DESMATAM_1', ascending=False)
    bar_fig = px.bar(top_10, x='NOME', y='DESMATAM_1', title='Top 10 UCs por Desmatamento', text='DESMATAM_1')
    bar_fig.update_traces(texttemplate='%{text:.2s}', textposition='auto')
    bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'}, title='Top 10 UCs - Desmatamento')

    # Geração do gráfico de mapa
    map_fig = px.choropleth_mapbox(
        top_10, geojson=roi, color='DESMATAM_1',
        locations="NOME", featureidkey="properties.NOME",
        mapbox_style="carto-positron",
        center={"lat": -14, "lon": -55},
        color_continuous_scale='YlOrRd',
        zoom=4
    )
    map_fig.update_layout(
        title={'text': f"Mapa de Degradação Ambiental (km²)", 'x': 0.5},
        margin={"r":0, "t":50, "l":0, "b":0},
        mapbox={
            'zoom': 4,
            'center': {"lat": -14, "lon": -55},
            'style': "carto-positron"
        }
    )
    return bar_fig, map_fig

# Executa a aplicação
if __name__ == '__main__':
    app.run_server(debug=True)
