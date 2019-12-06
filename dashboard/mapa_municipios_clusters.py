# Import required libraries
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

'''
# Importacion de las credenciales
from credentials import *

# ********** Extracciones de datos de la BD ********** #
postgres_str = 'postgresql://' + POSTGRES_USERNAME + ':' + POSTGRES_PASSWORD + '@' + POSTGRES_ADDRESS + ':' + POSTGRES_PORT + '/' + POSTGRES_DBNAME
cnx = create_engine(postgres_str)

query = 'SELECT * FROM POBLACION_DEPARTAMENTO_SEXO'

df_dpto_sexo = pd.read_sql_query(query, cnx)
'''

# Cargar geojson de departamentos
with open('departamentos.geojson') as f:
    geojson_departamentos = json.loads(f.read())

# Cargar geojson de municipios
with open('municipios.geojson') as f:
    geojson_municipios = json.loads(f.read())

# Token de acceso a https://www.mapbox.com/
token = 'pk.eyJ1IjoibmV3dXNlcmZvcmV2ZXIiLCJhIjoiY2o2M3d1dTZiMGZobzMzbnp2Z2NiN3lmdyJ9.cQFKe3F3ovbfxTsM9E0ZSQ'

#Procedimiento para sumar el código del departamento (en formato string) y el código del municipio (en formato string).
df_master = pd.read_csv('tabla_proporciones.csv')
df_master['u_dpto'] = df_master['u_dpto'].astype('str')
df_master['u_mpio'] = df_master['u_mpio'].astype('str')
df_master['u_dpto'] = df_master['u_dpto'].apply(lambda x : x.zfill(2))
df_master['u_mpio'] = df_master['u_mpio'].apply(lambda x : x.zfill(3))
df_master['str_dpto_mpio'] = df_master['u_dpto'] + df_master['u_mpio']

# Funcion de filtrado por cluster
def filtrar_cluster(df,cluster_dropdown):
    '''
    Función para filtrar los cluster en la tabla maestra (1122 municipios).
    Recibe un Dataframe y devuelve otro Dataframe filtrado.
    '''
    filtered_df = df[df['labels'].isin(cluster_dropdown)]
    return filtered_df

# Create controls

cluster_options = [{'label':'Clúster 0 ', 'value' : 0},
                   {'label':'Clúster 1 ', 'value' : 1},
                   {'label':'Clúster 2 ', 'value' : 2},
                   {'label':'Clúster 3 ', 'value' : 3},
                   {'label':'Clúster 4 ', 'value' : 4}]


lista_columnas_analisis = ['alfabetizacion','analfabetismo','escolarizado', 'descolarizado', 'remunerado','no_remunerado', 'atencion_formal', 'atencion_informal','no_necesita_atencion']
analysis_options = [{'label': i.title(),'value': i } for i in lista_columnas_analisis]

#Decoración del Frontend
test_png = 'team_32.png' # Logo Team_32
test_base64 = base64.b64encode(open(test_png, 'rb').read()).decode('ascii')
ds4a_png = 'ds4a.png' # Logo DS4A
ds4a_base64 = base64.b64encode(open(ds4a_png, 'rb').read()).decode('ascii')
min_png = 'mintic.png' # Logo DS4A
min_base64 = base64.b64encode(open(min_png, 'rb').read()).decode('ascii')

app = dash.Dash(__name__)
server = app.server


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
                            'Filter by department:',
                            className="control_label"
                        ),
                        dcc.RadioItems(
                            id='cluster_button_selector',
                            options=[
                                {'label': 'All ', 'value': 'all'},
                                {'label': 'Customize ', 'value': 'custom'}
                            ],
                            value='all',
                            labelStyle={'display': 'inline-block'},
                            className="dcc_control"
                        ),
                        dcc.Dropdown(
                            id='cluster_dropdown_options',
                            options=cluster_options,
                            multi=True,
                            value= [],
                            className="dcc_control"
                        ),
                        dcc.RadioItems(
                            id='group_button_selector',
                            options=[
                                {'label': 'Clustered ', 'value': 'clustered'},
                                {'label': 'Municipality ', 'value': 'municipality'}
                            ],
                            value='clustered',
                            labelStyle={'display': 'inline-block'},
                            className="dcc_control"
                        ),
                        html.P(
                            'Filter by welfare variable:',
                            className="control_label"
                        ),
                        dcc.Dropdown(
                            id='analysis_dropdown_options',
                            options=analysis_options,
                            multi=False,
                            value=[],
                            className="dcc_control"
                        ),
                        html.P(
                            'Select Scatter Plot options:',
                            className="control_label"
                        ),
                        dcc.Dropdown(
                            id='scatter1_dropdown_options',
                            options=analysis_options,
                            multi=False,
                            value=[],
                            className="dcc_control"
                        ),
                        dcc.Dropdown(
                            id='scatter2_dropdown_options',
                            options=analysis_options,
                            multi=False,
                            value=[],
                            className="dcc_control"
                        ),
                        html.P(
                            'Select Top:',
                            className="control_label"
                        ),
                        dcc.RadioItems(
                            id='top_button_selector',
                            options=[
                                {'label': 'Highest 5 ', 'value': 'high_5'},
                                {'label': 'Lowest 5 ', 'value': 'low_5'}
                            ],
                            value='high_5',
                            labelStyle={'display': 'inline-block'},
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
                                            id="men_percentage",
                                            className="pretty_container"
                                        ),
                                        html.Div(
                                            [
                                                html.P("Variable",
                                                    id='variable_text'),
                                                html.H6(
                                                    id="variable_percentage_text",
                                                    className="info_text"
                                                )
                                            ],
                                            id="women_percentage",
                                            className="pretty_container"
                                        ),
                                        html.Div(
                                            [
                                                html.P("Municipalities Count"),
                                                html.H6(
                                                    id="municipalities_text",
                                                    className="info_text"
                                                )
                                            ],
                                            id="municipalities_count",
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
                            id='map-plot-municipios',
                            figure={ 
                                'data': [go.Choroplethmapbox(
                                    geojson=geojson_municipios,
                                    locations=df_master['str_dpto_mpio'], # Esto debería coincidir con el "id" en el geojson
                                    z=df_master['labels'], # Métrica (lo que se va a medir)
                                    colorscale=[
                                                [0,    "blue"],
                                                [0.20, "blue"],
                                                [0.20, "orange"],
                                                [0.40, "orange"],
                                                [0.40, "green"],
                                                [0.60, "green"],
                                                [0.60, "red"],
                                                [0.80, "red"],
                                                [0.80, "rgb(73,33,109)"],
                                                [1,    "rgb(73,33,109)"]], #Colores del degradé del mapa: Cividis, Viridis, Magma 
                                    text=df_master['u_mpio'],
                                    colorbar=
                                    {
                                      'title':'Clúster', #Título de la barra de colores
                                      'thickness':10,
                                      'xpad': 5,
                                      'tickvals' : [0,1,2,3,4]
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
                                    hovertemplate = '<b>%{text}</b> <br>Clúster: %{z:,.d}<extra></extra>' # Override de hoverinfo
                                )],
                                'layout': go.Layout(
                                        mapbox_style="light", #streets, dark, light, outdoors, satellite, satellite-streets, carto-positron
                                        autosize=False,
                                        mapbox_accesstoken=token,
                                        mapbox_zoom=4,
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
                        dcc.Graph(id='bar_graph_cluster',
                                  figure={}
    ),
                    ],
                    className='pretty_container eight columns',
                ),
                html.Div(
                    [
                        dcc.Graph(
        id='scatter_plot',
        figure={}
    )
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
                        dcc.Graph(id='box-plot')
                    ],
                    className='pretty_container seven columns',
                ),
                html.Div(
                    [
                        dcc.Graph(id='bar_graph')
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
        Output('cluster_dropdown_options','value'),
    [
        Input('cluster_button_selector', 'value')
    ]
)
def update_dropdown(radio_button):
    if radio_button == 'all':
        filtered_list = ['0','1','2','3','4']
        return filtered_list
    else:
        return []


@app.callback(
   [
        Output('municipalities_text', 'children'),
        Output('variable_percentage_text','children'), #Cambia
        Output('variable_text','children'),
        Output('women_text','children'), #Cambia
        Output('men_text','children') #Cambia
   ],
   [
        Input('map-plot-municipios', 'hoverData'),# Esta es para cuando se pasa el mouse por encima
        Input('cluster_dropdown_options','value'),
        Input('analysis_dropdown_options','value'),
        Input('group_button_selector','value')
   ]
)
def update_text_boxes(map_data,cluster_dropdown,analysis_dropdown_options,group_button):
    if group_button == 'clustered':
        filtered_df = filtrar_cluster(df_master,cluster_dropdown)
        percentage_men = filtered_df['sexo_m'].sum()/filtered_df['poblacion'].sum()
        percentage_women = filtered_df['sexo_f'].sum()/filtered_df['poblacion'].sum()
        return [filtered_df.shape[0],
                r'{:.2%}'.format(filtered_df[analysis_dropdown_options].mean()),
                analysis_dropdown_options.title(),
                r'{:.2%}'.format((percentage_women)),
                r'{:.2%}'.format((percentage_men))]
    elif group_button == 'municipality':
        filtered_df = filtrar_cluster(df_master,cluster_dropdown)
        municipio = [each['location'] for each in map_data['points']] if map_data else None
        filtered_df_sex = df_master[df_master['str_dpto_mpio'] == municipio[0]]
        percentage_men = filtered_df_sex['sexo_m']/(filtered_df_sex['sexo_m'] + filtered_df_sex['sexo_f'])
        percentage_women = filtered_df_sex['sexo_f']/(filtered_df_sex['sexo_m'] + filtered_df_sex['sexo_f'])
        analysis_var_mun = filtered_df[filtered_df['str_dpto_mpio'] == municipio[0]][analysis_dropdown_options]
        return [filtered_df.shape[0],
                r'{:.2%}'.format(analysis_var_mun.values[0]),
                analysis_dropdown_options.title(),
                r'{:.2%}'.format((percentage_women.values[0])),
                r'{:.2%}'.format((percentage_men.values[0]))]


@app.callback(
    [
    Output('map-plot-municipios','figure')
    ],
    [
    Input('cluster_dropdown_options','value')
    ]
)
def update_map(cluster_dropdown):
    filtered_df = filtrar_cluster(df_master,cluster_dropdown)
    text = filtered_df['municipio'] + ',' + filtered_df['departamento'] + '.' + filtered_df['poblacion'].apply(lambda x : 'Población: ' + str(f'{x:,}'))
    return [{ 
            'data': [go.Choroplethmapbox(
                                    geojson=geojson_municipios,
                                    locations=filtered_df['str_dpto_mpio'], # Esto debería coincidir con el "id" en el geojson
                                    z=filtered_df['labels'], # Métrica (lo que se va a medir)
                                    colorscale= [
                                                [0,    "blue"],
                                                [0.20, "blue"],
                                                [0.20, "orange"],
                                                [0.40, "orange"],
                                                [0.40, "green"],
                                                [0.60, "green"],
                                                [0.60, "red"],
                                                [0.80, "red"],
                                                [0.80, "rgb(73,33,109)"],
                                                [1,    "rgb(73,33,109)"]], #Colores del degradé del mapa: Cividis, Viridis, Magma 
                                    text=text,
                                    colorbar=
                                    {
                                      'title':'Clúster', #Título de la barra de colores
                                      'thickness':10,
                                      'xpad': 5,
                                      'tickvals' : [0,1,2,3,4]
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
                                    hovertemplate = '<b>%{text}</b> <br>Clúster: %{z:,.d}<extra></extra>' # Override de hoverinfo
                                )],
                                'layout': go.Layout(
                                        mapbox_style="light", #streets, dark, light, outdoors, satellite, satellite-streets, carto-positron
                                        autosize=False,
                                        mapbox_accesstoken=token,
                                        mapbox_zoom=4,
                                        uirevision= 'no reset of zoom', #Sirve para que el zoom no se actualice
                                        margin={'t': 0, 'l': 0, 'r': 0, 'b': 0, 'pad':0},
                                        mapbox_center={"lat": 4.5709, "lon": -74.2973}
                                    )
                            }]

@app.callback(
    [
    Output('bar_graph','figure')
    ],
    [
    Input('cluster_dropdown_options','value'),
    Input('analysis_dropdown_options','value'),
    Input('top_button_selector','value')
    ]
)
def update_barplot(cluster_dropdown,analysis_dropdown_options,top_button_selector):
    if top_button_selector == 'high_5':
        filtered_df = filtrar_cluster(df_master,cluster_dropdown)
        df_cluster0 = filtered_df[filtered_df['labels'] == 0].sort_values(by = analysis_dropdown_options, ascending = False)[0:7]
        df_cluster1 = filtered_df[filtered_df['labels'] == 1].sort_values(by = analysis_dropdown_options, ascending = False)[0:7]
        df_cluster2 = filtered_df[filtered_df['labels'] == 2].sort_values(by = analysis_dropdown_options, ascending = False)[0:7]
        df_cluster3 = filtered_df[filtered_df['labels'] == 3].sort_values(by = analysis_dropdown_options, ascending = False)[0:7]
        df_cluster4 = filtered_df[filtered_df['labels'] == 4].sort_values(by = analysis_dropdown_options, ascending = False)[0:7]
        return [{'data': [
                        {'x': df_cluster0['municipio'], 'y': df_cluster0[analysis_dropdown_options], 'type': 'bar', 'name': 'Clúster 0','opacity' : 0.9},
                        {'x': df_cluster1['municipio'], 'y': df_cluster1[analysis_dropdown_options], 'type': 'bar', 'name': 'Clúster 1','opacity' : 0.9},
                        {'x': df_cluster2['municipio'], 'y': df_cluster2[analysis_dropdown_options], 'type': 'bar', 'name': 'Clúster 2','opacity' : 0.9},
                        {'x': df_cluster3['municipio'], 'y': df_cluster3[analysis_dropdown_options], 'type': 'bar', 'name': 'Clúster 3','opacity' : 0.9},
                        {'x': df_cluster4['municipio'], 'y': df_cluster4[analysis_dropdown_options], 'type': 'bar', 'name': 'Clúster 4','opacity' : 0.9}
                        ],
                        'layout': {
                        'title': analysis_dropdown_options.title() + ' Highest 5'}
                }]
    else:
        filtered_df = filtrar_cluster(df_master,cluster_dropdown)
        df_cluster0 = filtered_df[filtered_df['labels'] == 0].sort_values(by = analysis_dropdown_options, ascending = True)[0:7]
        df_cluster1 = filtered_df[filtered_df['labels'] == 1].sort_values(by = analysis_dropdown_options, ascending = True)[0:7]
        df_cluster2 = filtered_df[filtered_df['labels'] == 2].sort_values(by = analysis_dropdown_options, ascending = True)[0:7]
        df_cluster3 = filtered_df[filtered_df['labels'] == 3].sort_values(by = analysis_dropdown_options, ascending = True)[0:7]
        df_cluster4 = filtered_df[filtered_df['labels'] == 4].sort_values(by = analysis_dropdown_options, ascending = True)[0:7]
        return [{'data':[
                        {'x': df_cluster0['municipio'], 'y': df_cluster0[analysis_dropdown_options], 'type': 'bar', 'name': 'Clúster 0','opacity' : 0.9},
                        {'x': df_cluster1['municipio'], 'y': df_cluster1[analysis_dropdown_options], 'type': 'bar', 'name': 'Clúster 1','opacity' : 0.9},
                        {'x': df_cluster2['municipio'], 'y': df_cluster2[analysis_dropdown_options], 'type': 'bar', 'name': 'Clúster 2','opacity' : 0.9},
                        {'x': df_cluster3['municipio'], 'y': df_cluster3[analysis_dropdown_options], 'type': 'bar', 'name': 'Clúster 3','opacity' : 0.9},
                        {'x': df_cluster4['municipio'], 'y': df_cluster4[analysis_dropdown_options], 'type': 'bar', 'name': 'Clúster 4','opacity' : 0.9}
                        ],
                        'layout': {
                        'title': analysis_dropdown_options.title() + ' Lowest 5'}
                }]


@app.callback(
    [
    Output('scatter_plot','figure')
    ],
    [
    Input('cluster_dropdown_options','value'),
    Input('analysis_dropdown_options','value'),
    Input('scatter1_dropdown_options','value'),
    Input('scatter2_dropdown_options','value')
    ]
)
def update_scatterplot(cluster_dropdown,analysis_dropdown_options,scatter1_dropdown_options, scatter2_dropdown_options):
    filtered_df = filtrar_cluster(df_master,cluster_dropdown)
    return [
            {
            'data': [
                dict(
                    x=filtered_df[filtered_df['labels'] == i][scatter1_dropdown_options],
                    y=filtered_df[filtered_df['labels'] == i][scatter2_dropdown_options],
                    text=filtered_df[filtered_df['labels'] == i]['municipio'],
                    mode='markers',
                    opacity=0.7,
                    marker={
                        'size': 15,
                        'line': {'width': 0.5, 'color': 'white'}
                    },
                    name = 'Clúster ' + str(i)
                ) for i in sorted(filtered_df.labels.unique())
            ],
            'layout': dict(
                xaxis={'type': 'log', 'title': scatter1_dropdown_options.title()},
                yaxis={'title': scatter2_dropdown_options.title()},
                margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
                legend={'x': 0, 'y': 1},
                hovermode='closest'
            ),
            'marker_color' : 'Set1'
        }]



@app.callback(
    [
    Output('bar_graph_cluster','figure')
    ],
    [
    Input('cluster_dropdown_options','value')
    ]
)
def update_barplot_cluster(cluster_dropdown):
    filtered_df = filtrar_cluster(df_master,cluster_dropdown)
    df_cluster0 = filtered_df[filtered_df['labels'] == 0].describe().loc['mean',lista_columnas_analisis]
    df_cluster1 = filtered_df[filtered_df['labels'] == 1].describe().loc['mean',lista_columnas_analisis]
    df_cluster2 = filtered_df[filtered_df['labels'] == 2].describe().loc['mean',lista_columnas_analisis]
    df_cluster3 = filtered_df[filtered_df['labels'] == 3].describe().loc['mean',lista_columnas_analisis]
    df_cluster4 = filtered_df[filtered_df['labels'] == 4].describe().loc['mean',lista_columnas_analisis]
    return [{'data':[
                    {'x': df_cluster0.index, 'y': df_cluster0.values, 'type': 'bar', 'name': 'Clúster 0','opacity' : 0.9},
                    {'x': df_cluster1.index, 'y': df_cluster1.values, 'type': 'bar', 'name': 'Clúster 1','opacity' : 0.9},
                    {'x': df_cluster2.index, 'y': df_cluster2.values, 'type': 'bar', 'name': 'Clúster 2','opacity' : 0.9},
                    {'x': df_cluster2.index, 'y': df_cluster3.values, 'type': 'bar', 'name': 'Clúster 3','opacity' : 0.9},
                    {'x': df_cluster2.index, 'y': df_cluster4.values, 'type': 'bar', 'name': 'Clúster 4','opacity' : 0.9}
                    ],
                        'layout': {
                        'title': 'Clúster Variables'}
                }]
    


@app.callback(
    [
    Output('box-plot','figure')
    ],
    [
    Input('cluster_dropdown_options','value'),
    Input('analysis_dropdown_options','value')
    ]
)
def update_boxplot(cluster_dropdown,analysis_dropdown_options):
    filtered_df = filtrar_cluster(df_master,cluster_dropdown)
    df_cluster0 = filtered_df[filtered_df['labels'] == 0]
    df_cluster1 = filtered_df[filtered_df['labels'] == 1]
    df_cluster2 = filtered_df[filtered_df['labels'] == 2]
    df_cluster3 = filtered_df[filtered_df['labels'] == 3]
    df_cluster4 = filtered_df[filtered_df['labels'] == 4]

    boxplot_0 = go.Box(
        y = df_cluster0[analysis_dropdown_options],
        name = "Clúster 0",
        boxpoints = 'outliers',
        marker_color = 'blue'
    )

    boxplot_1 = go.Box(
        y = df_cluster1[analysis_dropdown_options],
        name = "Clúster 1",
        boxpoints = 'outliers',
        marker_color = 'orange'
    )

    boxplot_2 = go.Box(
        y = df_cluster2[analysis_dropdown_options],
        name = "Clúster 2",
        boxpoints = 'outliers',
        marker_color = 'green'
    )

    boxplot_3 = go.Box(
        y = df_cluster3[analysis_dropdown_options],
        name = "Clúster 3",
        boxpoints = 'outliers',
        marker_color = 'red'
    )

    boxplot_4 = go.Box(
        y = df_cluster4[analysis_dropdown_options],
        name = "Clúster 4",
        boxpoints = 'outliers',
        marker_color = 'rgb(73,33,109)'
    )

    data = [boxplot_0,boxplot_1,boxplot_2,boxplot_3,boxplot_4]

    layout = go.Layout(
        title = analysis_dropdown_options.title()
    )

    fig = go.Figure(data=data,layout=layout)
    return [fig]


# Main
if __name__ == '__main__':
    app.server.run(debug=True, threaded=True, port = 5011)
