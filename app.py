import pandas as pd
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import os
import threading
import webbrowser
import base64

# 📊 Data inladen
pad = 'KPI_table.xlsx'
df = pd.read_excel(pad, sheet_name='KPI').ffill().reset_index(drop=True)

# 🧹 Kolommen schonen
kolommen = ['Baseline 2025', 'Baseline 2050', 'Strategy 1', 'Strategy 2', 'Strategy 3']
for col in kolommen:
    df[col] = (
        df[col]
        .astype(str)
        .str.replace(r'[^\d\-,\.]', '', regex=True)
        .str.replace(',', '.')
    )
    df[col] = pd.to_numeric(df[col], errors='coerce')

# 🎨 Kleuren per groep
group_colors = {
    'Sustainability': '#2E6F40',
    'Feasibility': '#ff7f0e',
    'Financial (quantitative)': '#1f77b4'
}

# 📂 KPI's per groep
group_kpi_dict = {
    group: df[df['Group'] == group]['KPI'].tolist()
    for group in df['Group'].ffill().unique()
}

# 📝 Beschrijvingen per KPI
kpi_descriptions = {
    'Total fuel (if any) [tons or kW]': "total fuel in tons used per year",
    'Total CO2 emissions [tons]': "total CO2 emission in kilograms per year ",
    'Available seats [-]': "Available seats per year",
    'Available cargo [tons]': "Available cargo in tons per year",
    'CO2 emissions per ASK [kg]': "CO2 emissions per ASK in kilograms ",
    'CO2 emissions per RSK [kg]': "CO2 emissions per RSK in kilograms ",
    'Technical': "Feasibility score for technical feasibility. This score must be a minimum of 6 to be sufficient",
    'Regulatory': "easibility score for regulatory feasibility. This score must be a minimum of 6 to be sufficient",
    'Safety': "easibility score for safety feasibility. This score must be a minimum of 6 to be sufficient",
    'Total cost [€]': "Total costs in euros per year",
    'Revenue [€]': "total revenue in euros per year",
    'Profit [% w.r.t. total cost]': "The total profit that is made in a percentage of the total costs",
    # Voeg hier gerust meer KPI-beschrijvingen toe
}

# 🔒 Logo coderen
logo_path = os.path.expanduser('~/Desktop/logo.png')
encoded_logo = base64.b64encode(open(logo_path, 'rb').read()).decode()

# 🖼️ App opzetten
app = dash.Dash(__name__)
app.title = "KPI Dashboard"

# 🎨 Layout
app.layout = html.Div([
    dcc.Store(id='dark-mode-store', data=False),

    html.Button("🌙 Toggle Dark Mode", id="dark-mode-button", n_clicks=0, style={
        'position': 'absolute',
        'top': '20px',
        'left': '20px',
        'padding': '10px 20px',
        'fontSize': '16px',
        'borderRadius': '8px',
        'border': 'none',
        'cursor': 'pointer',
        'backgroundColor': '#ddd',
        'zIndex': '999'
    }),

    html.Div([
        html.Img(src=f'data:image/png;base64,{encoded_logo}', style={'height': '80px'})
    ], style={'display': 'flex', 'justifyContent': 'flex-end', 'alignItems': 'center'}),

    html.H1("KPI Visualisation Dashboard", id='main-title'),

    html.Label("Choose a KPI-group:", className='dropdown-label'),
    dcc.Dropdown(
        id='group-dropdown',
        options=[{'label': k, 'value': k} for k in group_kpi_dict.keys()],
        value='Sustainability',
        className='dropdown'
    ),

    html.Label("Choose a KPI:", className='dropdown-label'),
    dcc.Dropdown(id='kpi-dropdown', className='dropdown'),

    dcc.Graph(id='grafiek-output'),
   html.Div(id='grafiek-beschrijving', style={
    'marginTop': '20px',
    'fontSize': '16px',
    'padding': '10px',
    'backgroundColor': '#f2f2f2',
    'borderRadius': '8px',
    'color': '#000'  # 🔥 Dit maakt de tekst zwart
})
], id='main-container', className='light-mode')

# 🔁 Callbacks

@app.callback(
    Output('kpi-dropdown', 'options'),
    Output('kpi-dropdown', 'value'),
    Input('group-dropdown', 'value')
)
def update_kpi_options(selected_group):
    opties = [{'label': kpi, 'value': kpi} for kpi in group_kpi_dict[selected_group]]
    eerste_kpi = opties[0]['value'] if opties else None
    return opties, eerste_kpi

@app.callback(
    Output('grafiek-output', 'figure'),
    Output('grafiek-beschrijving', 'children'),
    Input('kpi-dropdown', 'value')
)
def update_graph(kpi_name):
    if not kpi_name:
        return go.Figure(), ""

    row = df[df['KPI'] == kpi_name]
    if row.empty:
        return go.Figure(), "Geen data gevonden."

    labels = ['Baseline 2025', 'Baseline 2050', 'Strategy 1', 'Strategy 2', 'Strategy 3']
    values = row[labels].values.flatten().astype(float)

    group = row['Group'].values[0]
    kleur = group_colors.get(group, 'gray')

    is_profit = 'profit' in kpi_name.lower()

    if is_profit:
        bar_values = values
        yaxis_tickformat = '.0%'
        colors = ['#317336' if v >= 0 else '#c00000' for v in bar_values]
    elif kpi_name.lower().startswith("total cost"):
        bar_values = values
        colors = ['#c00000'] * len(values)
        yaxis_tickformat = None
    elif kpi_name.lower().startswith("revenue"):
        bar_values = values
        colors = ['#317336'] * len(values)
        yaxis_tickformat = None
    else:
        bar_values = values
        colors = [kleur] * len(values)
        yaxis_tickformat = None

    fig = go.Figure(data=[
        go.Bar(x=labels, y=bar_values, marker_color=colors)
    ])

    if "total co2 emissions" in kpi_name.lower():
        fig.add_shape(type="line", x0=-0.5, x1=4.5, y0=301000, y1=301000,
                      line=dict(color="red", width=2, dash="dash"))
        fig.add_annotation(x=4, y=301000, text="Goal: 301k", showarrow=False,
                           yshift=10, font=dict(color="red", size=12))

    fig.update_layout(
        title=dict(text=kpi_name, font=dict(size=24, color='#333')),
        xaxis_title="Scenario's",
        yaxis_title=kpi_name,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#f9f9f9",
        margin=dict(t=80, l=60, r=40, b=60),
        xaxis=dict(showgrid=False),
        yaxis=dict(
            gridcolor='lightgrey',
            zeroline=False,
            tickformat=yaxis_tickformat
        ),
        transition={'duration': 500},
    )

    # ✅ Beschrijving ophalen
    kpi_name_clean = kpi_name.strip()
    desc = kpi_descriptions.get(kpi_name_clean, "Geen beschrijving beschikbaar voor deze KPI.")
    return fig, desc

@app.callback(
    Output('main-container', 'className'),
    Output('dark-mode-store', 'data'),
    Input('dark-mode-button', 'n_clicks'),
    Input('dark-mode-store', 'data'),
    prevent_initial_call='initial_duplicate'
)
def toggle_dark_mode(n_clicks, current_mode):
    if n_clicks is None:
        return 'light-mode', False
    new_mode = not current_mode
    return ('dark-mode' if new_mode else 'light-mode'), new_mode

# 🌐 Automatisch openen in browser
def open_browser():
    webbrowser.open_new("http://127.0.0.1:8050/")

if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)




#lets go go 

