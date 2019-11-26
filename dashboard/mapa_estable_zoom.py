# Import required libraries
import datetime as dt
import base64

#Importaciones de dash
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go

# Importaciones de los diccionarios
from diccionarios import dpt_dict, mun_dict, diccionario_zoom_center,analysis_var

# Importaciones de la base de datos
import psycopg2
from sqlalchemy import create_engine, text

# Importaciones de back end
import pandas as pd
import json
from flask import Flask

# Importacion de las credenciales
from credentials import *

# ********** Extracciones de datos de la BD ********** #
postgres_str = 'postgresql://' + POSTGRES_USERNAME + ':' + POSTGRES_PASSWORD + '@' + POSTGRES_ADDRESS + ':' + POSTGRES_PORT + '/' + POSTGRES_DBNAME
cnx = create_engine(postgres_str)

query = 'SELECT * FROM POBLACION_DEPARTAMENTO_SEXO'

df_dpto_sexo = pd.read_sql_query(query, cnx)

# Cargar geojson de departamentos
with open('departamentos.geojson') as f:
    geojson_departamentos = json.loads(f.read())

# Cargar geojson de municipios
with open('municipios.geojson') as f:
    geojson_municipios = json.loads(f.read())

# Token de acceso a https://www.mapbox.com/
token = 'pk.eyJ1IjoibmV3dXNlcmZvcmV2ZXIiLCJhIjoiY2o2M3d1dTZiMGZobzMzbnp2Z2NiN3lmdyJ9.cQFKe3F3ovbfxTsM9E0ZSQ'

# Pasar relacion nombres y códigos de departamentos a DF
df_nombres = pd.DataFrame.from_dict(dpt_dict, orient='index').reset_index()

# Agregar nombre de departamento a DataFrame con datos
df_dpto_sexo = pd.merge(df_dpto_sexo,df_nombres,left_on=['u_dpto'],right_on=['index'])
df_dpto_sexo = df_dpto_sexo.rename(columns={0:'nombre_departamento'})

# Sumarizar por departamento
df_dpto_poblacion = df_dpto_sexo.groupby(['u_dpto', 'nombre_departamento']).sum()[['poblacion']].reset_index()

# Query para extraer la poblacion por municipios
query_municipios = 'SELECT * FROM POBLACION_DEPARTAMENTO_MUNICIPIO_SEXO;'

df_dpto_sexo_municipios = pd.read_sql_query(query_municipios, cnx)
df_dpto_poblacion = df_dpto_sexo.groupby(['u_dpto', 'nombre_departamento']).sum()[['poblacion']].reset_index()

# Pasar relacion nombres y códigos de departamentos a DF
df_nombres_municipios = pd.DataFrame.from_dict(mun_dict, orient='index').reset_index()

# Agregar nombre de departamento a DataFrame con datos
df_dpto_sexo_municipios = pd.merge(df_dpto_sexo_municipios,df_nombres_municipios,left_on=['u_dpto_u_mpio'],right_on=['index'])
df_dpto_sexo_municipios = df_dpto_sexo_municipios.rename(columns={0:'nombre_municipio'})

# Sumarizar por departamento
df_mun_poblacion = df_dpto_sexo_municipios.groupby(['u_dpto_u_mpio', 'nombre_municipio']).sum()[['poblacion']].reset_index()

# Funcion de filtrado por departamento. Recibe un dataframe y devuelve el dataframe filtrado por departamento
def filtrar_departamento(df, id_departamentos):
    dff = df[df['u_dpto'].isin(id_departamentos)]
    return dff

app = dash.Dash(__name__)
server = app.server

# Create controls

departments_options = [{'label': str(dpt_dict[department]),
                        'value': str(department)}
                        for department in dpt_dict]

municipios_options = [{'label': str(mun_dict[municipio]),
                       'value': str(municipio)}
                        for municipio in mun_dict]

analysis_options = [{'label': str(analysis_var[analysis]),
                     'value': str(analysis)}
                      for analysis in analysis_var]

def filtrar_municipios(codigo_departamento):
    for i in range(len(municipios_options)):
        if municipios_options[i]['value'][0:2] == departments_options[0]['value']:
            print(municipios_options[i]['label'])


test_png = 'team_32.png' # Logo Team_32
test_base64 = base64.b64encode(open(test_png, 'rb').read()).decode('ascii')
ds4a_png = 'ds4a.png' # Logo DS4A
ds4a_base64 = base64.b64encode(open(ds4a_png, 'rb').read()).decode('ascii')
min_png = 'mintic.png' # Logo DS4A
min_base64 = base64.b64encode(open(min_png, 'rb').read()).decode('ascii')

#Global variables
municipios_flag  = True

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
                    ],

                    className='eight columns'
                ),
                html.Img(
                    src='data:image/png;base64,{}'.format(test_base64),
                    className='two columns',
                ),
                html.Img(
                    src='data:image/png;base64,{}'.format(ds4a_base64),
                    className='two columns',
                ),
                html.Img(
                    src='data:image/png;base64,{}'.format(min_base64),
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
                            id='department_selector',
                            options=[
                                {'label': 'All ', 'value': 'all'},
                                {'label': 'DS4A ', 'value': 'ds4a'},
                                {'label': 'Customize ', 'value': 'custom'}
                            ],
                            value='all',
                            labelStyle={'display': 'inline-block'},
                            className="dcc_control"
                        ),
                        dcc.Dropdown(
                            id='dropdown_options',
                            options=departments_options,
                            multi=True,
                            value= [],
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
                            id='analysis_selector',
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
                            id='analysis_var',
                            options=analysis_options,
                            multi=False,
                            value=list(analysis_var.keys()),
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
                                        html.P("Women"),
                                        html.H6(
                                            id="women_text",
                                            className="info_text"
                                        )
                                    ],
                                    id="women_percetage",
                                    className="pretty_container",
                                ),

                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.P("Men"),
                                                html.H6(
                                                    id="men_text",
                                                    className="info_text"
                                                )
                                            ],
                                            id="gas",
                                            className="pretty_container"
                                        ),
                                        html.Div(
                                            [
                                                html.P("Age Average"),
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
                                                html.P("Born Here"),
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
                            id='map-plot-departamentos',
                            figure={ 
                                'data': [go.Choroplethmapbox(
                                    geojson=geojson_departamentos,
                                    locations=df_dpto_poblacion['u_dpto'], # Esto debería coincidir con el "id" en el geojson
                                    z=df_dpto_poblacion['poblacion'], # Métrica (lo que se va a medir)
                                    colorscale='Viridis', #Colores del degradé del mapa: Cividis, Viridis, Magma 
                                    text=df_dpto_poblacion['nombre_departamento'],
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
                                        autosize=False,
                                        mapbox_accesstoken=token,
                                        mapbox_zoom=3.5,
                                        uirevision= 'no reset of zoom', #Sirve para que el zoom no se actualice
                                        margin={'t': 0, 'l': 0, 'r': 0, 'b': 0, 'pad':0},
                                        mapbox_center={"lat": 4.5709, "lon": -74.2973}
                                    )
                            }
                        )
                            ],
                            id="div-map-departamentos",
                            className="pretty_container"
                        ),
                        html.Div
(
    id='div-map-municipios',
    style={'border':'1px purple solid', 'display': 'none'}, children=[
    dcc.Graph(
    id='map-plot-municipios', # ID PARA EL CALLBACK
    figure={} # Vacío porque se llena en el callback
),
html.Button('Back to departments', id='boton-back')
]
),
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


@app.callback(
    Output('dropdown_options','value'),
    [
        Input('department_selector', 'value')
    ]
)
def update_dropdown(radio_buttom):
    if radio_buttom == 'ds4a':
        filtered_list = ['11','05','08','76']
        return filtered_list
    elif radio_buttom == 'all':
        filtered_list = list(dpt_dict.keys())
        return filtered_list
    else:
        return []


@app.callback(
                Output(component_id = 'map-plot-departamentos',component_property = 'figure'),
              [
                Input(component_id = 'dropdown_options',component_property = 'value')
              ]
             )
def update_map(dropdown_options):
    filtered_df_sexo = filtrar_departamento(df_dpto_sexo,dropdown_options)
    filtered_df_poblacion = filtrar_departamento(df_dpto_poblacion,dropdown_options)
    z_to_show = filtered_df_sexo.groupby(['u_dpto', 'nombre_departamento']).sum()[['poblacion']].reset_index()
    return {'data': [go.Choroplethmapbox(
                                    geojson=geojson_departamentos,
                                    locations=filtered_df_poblacion['u_dpto'], # Esto debería coincidir con el "id" en el geojson
                                    z=z_to_show['poblacion'], # Métrica (lo que se va a medir)
                                    colorscale='Viridis', #Colores del degradé del mapa: Cividis, Viridis, Magma 
                                    text=filtered_df_poblacion['nombre_departamento'],
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
                                        autosize = False,
                                        mapbox_accesstoken=token,
                                        mapbox_zoom = 3.5,
                                        uirevision= 'no reset of zoom', #Sirve para que el zoom no se actualice
                                        margin={'t': 0, 'l': 0, 'r': 0, 'b': 0, 'pad':0},
                                        mapbox_center={"lat": 4.5709, "lon": -74.2973}
                                    )
                            }


@app.callback(
   [
        Output('women_text', 'children'), # Actualizar el p (la cajita de texto)
        Output('men_text', 'children') # Actualizar el p (la cajita de texto)
   ],
   [
        Input('map-plot-departamentos', 'hoverData') # Esta es para cuando se pasa el mouse por encima
   ]
)
def update_gender_count_boxes(map_data):
    estados = [each['location'] for each in map_data['points']] if map_data else None  # se arma una lista con todos los estados elegidos (es útil para la selección)
    dff = filtrar_departamento(df_dpto_sexo, estados)
    return [ format(dff['poblacion'][dff['p_sexo']=='1'].sum(),','), # Male
             format(dff['poblacion'][dff['p_sexo']=='2'].sum(),',')  # Female
           ]


@app.callback(
    [
        Output('div-map-departamentos', 'style'), # Ocultar div de mapa de departamentos
        Output('div-map-municipios', 'style'), # Mostrar div de mapa de municipios
        Output('map-plot-municipios', 'figure'),
        Output('dropdown_options','options')
    ],
    [
        Input('map-plot-departamentos', 'clickData'), # Esta es para cuando se hace click
        Input('boton-back', 'n_clicks')# Esta es para cuando se hace click
    ]
)
def mostrar_departamentos_municipios(map_data_departamentos, boton_a_departamentos):
    
    # Variable global que me sirve para controlar si se está en la vista por departamentos o por municipios
    global municipios_flag

    # Variables para alimentar el mapa y ubicarlo en el centro y zoom adecuado
    global diccionario_zoom_center
          
    # Variables para alimentar el mapa y ubicarlo en el centro y zoom adecuado

    if municipios_flag:
        municipios_flag = False
        return [
            {'display': 'block'}, # Mostrar departamentos
            {'display': 'none'},  # Ocultar municipios
            {},
            departments_options
        ]

    else:
        municipios_flag = True
        # Armar lista con el subconjunto de municipios contenido en el departamento
        lista_municipios = [i for i in geojson_municipios['features'] if str(i['id'])[:2] == str(map_data_departamentos['points'][0]['location'])]
        lista_nombres_municipios = [{'label' : str(i['properties']['NOMBRE_MPI']),
                                     'value' : str(i['properties']['MPIOS'])} for i in lista_municipios] 
        # Armar nuevo geojson
        geojson_departamento_municipios = {
        "type": "FeatureCollection",
        "name": "municipios",
        "crs": {"type": "name", "properties":{"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": lista_municipios
        }

        # Armar lista con el subconjunto de municipios contenido en el departamento
        diccionario_zoom_center[map_data_departamentos['points'][0]['location']]
        # Ajustar el zoom adecuado al departamento seleccionado
        zoom = diccionario_zoom_center[map_data_departamentos['points'][0]['location']]['zoom']
        # Ajustar el centro de la posición adecuada al departamento seleccionado
        posicion_centro = diccionario_zoom_center[map_data_departamentos['points'][0]['location']]['center']
        # Devolver el mapa con los parametros
        return [
            {'display': 'none'}, # Ocultar departamentos
            {'display': 'block'},  # Mostrar municipios
            {
                'data': [go.Choroplethmapbox(
                geojson=geojson_departamento_municipios,
                locations=df_mun_poblacion['u_dpto_u_mpio'], # Esto debería coincidir con el "id" en el geojson
                z=df_mun_poblacion['poblacion'], # Métrica (lo que se va a medir)
                colorscale='Viridis', #Colores del degradé del mapa: Cividis, Viridis, Magma 
                text=df_mun_poblacion['nombre_municipio'],
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
                mapbox_zoom=zoom,
                margin={'t': 0, 'l': 0, 'r': 0, 'b': 0, 'pad':0},
                mapbox_center=posicion_centro
                )
            },
            lista_nombres_municipios
        ]
########## Callback para ocultar mapa por departamentos y mostrar mapa por municipios y viceversa ##########

# Main
if __name__ == '__main__':
    app.server.run(debug=True, threaded=True, port = 5010)
