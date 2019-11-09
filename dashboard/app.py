# Import required libraries
import os
import pickle
import copy
import datetime as dt
import math
import base64

#import requests
import pandas as pd
from flask import Flask
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go

# Multi-dropdown options
from controls import COUNTIES, WELL_STATUSES, WELL_TYPES, WELL_COLORS

# Importaciones de la base de datos
import psycopg2
from sqlalchemy import create_engine, text

# Importaciones de back end
import pandas as pd
import json

# ********** Extracciones de datos de la BD ********** #
POSTGRES_ADDRESS = 'ds4ateam32.cl8xbcsviig5.us-west-2.rds.amazonaws.com'
POSTGRES_PORT = '5432'
POSTGRES_USERNAME = 'DS4ATEAM32'
POSTGRES_PASSWORD = 'DS4ATEAM32'
POSTGRES_DBNAME = 'DS4ATEAM32'
postgres_str = 'postgresql://' + POSTGRES_USERNAME + ':' + POSTGRES_PASSWORD + '@' + POSTGRES_ADDRESS + ':' + POSTGRES_PORT + '/' + POSTGRES_DBNAME
cnx = create_engine(postgres_str)

query = 'SELECT * FROM POBLACION_DEPARTAMENTO_SEXO'

df_col = pd.read_sql_query(query, cnx)

# Cargar geojson de departamentos
with open('departamentos.geojson') as f:
    geojson_departamentos = json.loads(f.read())

# Cargar geojson de municipios
with open('municipios.geojson') as f:
    geojson_municipios = json.loads(f.read())

# Token de acceso a https://www.mapbox.com/
token = 'pk.eyJ1IjoibmV3dXNlcmZvcmV2ZXIiLCJhIjoiY2o2M3d1dTZiMGZobzMzbnp2Z2NiN3lmdyJ9.cQFKe3F3ovbfxTsM9E0ZSQ'

# Diccionario de departamentos y municipios
from geo_dictionaries import dpt_dict, mun_dict

# Pasar relacion nombres y códigos de departamentos a DF
df_nombres = pd.DataFrame.from_dict(dpt_dict, orient='index').reset_index()

# Agregar nombre de departamento a DataFrame con datos
df_col = pd.merge(df_col,df_nombres,left_on=['u_dpto'],right_on=['index'])
df_col = df_col.rename(columns={0:'nombre_departamento'})

# Sumarizar por departamento
df_mapa = df_col.groupby(['u_dpto', 'nombre_departamento']).sum()[['poblacion']].reset_index()

###########################################################################

# Query para extraer la poblacion por municipios
query_municipios = '''
SELECT * FROM POBLACION_DEPARTAMENTO_MUNICIPIO_SEXO
;'''
df_col_municipios = pd.read_sql_query(query_municipios, cnx)

# Pasar relacion nombres y códigos de departamentos a DF
df_nombres_municipios = pd.DataFrame.from_dict(mun_dict, orient='index').reset_index()

# Agregar nombre de departamento a DataFrame con datos
df_col_municipios = pd.merge(df_col_municipios,df_nombres_municipios,left_on=['u_dpto_u_mpio'],right_on=['index'])
df_col_municipios = df_col_municipios.rename(columns={0:'nombre_municipio'})

# Sumarizar por departamento
df_mapa_municipios = df_col_municipios.groupby(['u_dpto_u_mpio', 'nombre_municipio']).sum()[['poblacion']].reset_index()

# Funcion de filtrado por departamento. Recibe un dataframe y devuelve el dataframe filtrado por departamento
def filtrar_departamento(id_departamentos, df):
    dff = df[df['u_dpto'].isin(id_departamentos)].copy()
    return dff


app = dash.Dash(__name__)
server = app.server

# Create controls
county_options = [{'label': str(COUNTIES[county]), 'value': str(county)}
                  for county in COUNTIES]

well_status_options = [{'label': str(WELL_STATUSES[well_status]),
                        'value': str(well_status)}
                       for well_status in WELL_STATUSES]

well_type_options = [{'label': str(WELL_TYPES[well_type]),
                      'value': str(well_type)}
                     for well_type in WELL_TYPES]


# Load data
df = pd.read_csv('data/wellspublic.csv')
df['Date_Well_Completed'] = pd.to_datetime(df['Date_Well_Completed'])
df = df[df['Date_Well_Completed'] > dt.datetime(1960, 1, 1)]

trim = df[['API_WellNo', 'Well_Type', 'Well_Name']]
trim.index = trim['API_WellNo']
dataset = trim.to_dict(orient='index')

points = pickle.load(open("data/points.pkl", "rb"))

test_png = 'team_32.png' # Logo Team_32
test_base64 = base64.b64encode(open(test_png, 'rb').read()).decode('ascii')

# Create app layout
app.layout = html.Div(
    [
        dcc.Store(id='aggregate_data'),
        html.Div(
            [
                html.Div(
                    [
                        html.H2(
                            'Colombia Inequality 🇨🇴',

                        ),
                        html.H4(
                            'Departments',
                        )
                    ],

                    className='eight columns'
                ),
                html.Img(
                    src='data:image/png;base64,{}'.format(test_base64),
                    className='two columns',
                ),
            ],
            id="header",
            className='row',
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.P(
                            'Filter by construction date (or select range in histogram):',
                            className="control_label"
                        ),
                        dcc.RangeSlider(
                            id='year_slider',
                            min=1960,
                            max=2017,
                            value=[1990, 2010],
                            className="dcc_control"
                        ),
                        html.P(
                            'Filter by well status:',
                            className="control_label"
                        ),
                        dcc.RadioItems(
                            id='well_status_selector',
                            options=[
                                {'label': 'All ', 'value': 'all'},
                                {'label': 'Active only ', 'value': 'active'},
                                {'label': 'Customize ', 'value': 'custom'}
                            ],
                            value='active',
                            labelStyle={'display': 'inline-block'},
                            className="dcc_control"
                        ),
                        dcc.Dropdown(
                            id='well_statuses',
                            options=well_status_options,
                            multi=True,
                            value=list(WELL_STATUSES.keys()),
                            className="dcc_control"
                        ),
                        dcc.Checklist(
                            id='lock_selector',
                            options=[
                                {'label': 'Lock camera', 'value': 'locked'}
                            ],
                            value=[],
                            className="dcc_control"
                        ),
                        html.P(
                            'Filter by well type:',
                            className="control_label"
                        ),
                        dcc.RadioItems(
                            id='well_type_selector',
                            options=[
                                {'label': 'All ', 'value': 'all'},
                                {'label': 'Productive only ',
                                    'value': 'productive'},
                                {'label': 'Customize ', 'value': 'custom'}
                            ],
                            value='productive',
                            labelStyle={'display': 'inline-block'},
                            className="dcc_control"
                        ),
                        dcc.Dropdown(
                            id='well_types',
                            options=well_type_options,
                            multi=True,
                            value=list(WELL_TYPES.keys()),
                            className="dcc_control"
                        ),
                    ],
                    className="pretty_container four columns"
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.P("No. of Wells"),
                                        html.H6(
                                            id="well_text",
                                            className="info_text"
                                        )
                                    ],
                                    id="wells",
                                    className="pretty_container"
                                ),

                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.P("Gas"),
                                                html.H6(
                                                    id="gasText",
                                                    className="info_text"
                                                )
                                            ],
                                            id="gas",
                                            className="pretty_container"
                                        ),
                                        html.Div(
                                            [
                                                html.P("Oil"),
                                                html.H6(
                                                    id="oilText",
                                                    className="info_text"
                                                )
                                            ],
                                            id="oil",
                                            className="pretty_container"
                                        ),
                                        html.Div(
                                            [
                                                html.P("Water"),
                                                html.H6(
                                                    id="waterText",
                                                    className="info_text"
                                                )
                                            ],
                                            id="water",
                                            className="pretty_container"
                                        ),
                                    ],
                                    id="tripleContainer",
                                )

                            ],
                            id="infoContainer",
                            className="row"
                        ),
                        html.Div(
                            [
                                dcc.Graph(
                            id='map-plot',
                            figure={ 
                                'data': [go.Choroplethmapbox(
                                    geojson=geojson_departamentos,
                                    locations=df_mapa['u_dpto'], # Esto debería coincidir con el "id" en el geojson
                                    z=df_mapa['poblacion'], # Métrica (lo que se va a medir)
                                    colorscale='Viridis', #Colores del degradé del mapa: Cividis, Viridis, Magma 
                                    text=df_mapa['nombre_departamento'],
                                    colorbar=
                                    {
                                      'title':'Pop', #Título de la barra de colores
                                      'thickness':10,
                                      'xpad': 5
                                    },
                                    marker=
                                    { # Atributos de los polígonos
                                    'opacity':0.5, #Transparencia de los polígonos
                                    'line': # Atributos de las líneas
                                      {
                                      'width':1, # Grosor de la línea frontera de los polígonos
                                      'color':'#999' # Color de la línea
                                      }
                                    },
                                    hovertemplate = '<b>%{text}</b> <br>Population: %{z:,.d}<extra></extra>' # Override de hoverinfo
                                )],
                                'layout': go.Layout(
                                        mapbox_style="light", #streets, dark, light, outdoors, satellite, satellite-streets, carto-positron
                                        autosize=True,
                                        mapbox_accesstoken=token,
                                        mapbox_zoom=3.5,
                                        margin={'t': 0, 'l': 0, 'r': 0, 'b': 0, 'pad':0},
                                        mapbox_center={"lat": 4.5709, "lon": -74.2973}
                                    )
                            }
                        )
                            ],
                            id="countGraphContainer",
                            className="pretty_container"
                        )
                    ],
                    id="rightCol",
                    className="eight columns"
                )
            ],
            className="row"
        ),
        html.Div(
            [
                html.Div(
                    [
                        dcc.Graph(id='main_graph')
                    ],
                    className='pretty_container eight columns',
                ),
                html.Div(
                    [
                        dcc.Graph(id='individual_graph')
                    ],
                    className='pretty_container four columns',
                ),
            ],
            className='row'
        ),
        html.Div(
            [
                html.Div(
                    [
                        dcc.Graph(id='pie_graph')
                    ],
                    className='pretty_container seven columns',
                ),
                html.Div(
                    [
                        dcc.Graph(id='aggregate_graph')
                    ],
                    className='pretty_container five columns',
                ),
            ],
            className='row'
        ),
    ],
    id="mainContainer",
    style={
        "display": "flex",
        "flex-direction": "column"
    }
)

# Main
if __name__ == '__main__':
    app.server.run(debug=True, threaded=True)
