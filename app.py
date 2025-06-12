import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table, callback_context
import plotly.express as px

#define fuels and units
fuel_types = {
    "Gas Oil": 0,
    "Natural Gas": 1,
    "Coal": 2,
}
units = {
    "kWh": 0,
    "liter": 1,
    "kg": 2,
    "m³": 3,
    "GJ": 4,
    }

# read in the data
vats = pd.read_excel("./assets/data/taxes_vat.xlsx", sheet_name="vats")
existing_price = pd.read_excel("./assets/data/existing_price.xlsx", sheet_name="existing_price")
emission_factors = pd.read_excel("./assets/data/emission_factors.xlsx", sheet_name="Factors")
conversion_gasoil = pd.read_excel("./assets/data/conversion_factors.xlsx", sheet_name="Gas Oil")
conversion_naturalgas = pd.read_excel("./assets/data/conversion_factors.xlsx", sheet_name="Natural Gas")
conversion_coal = pd.read_excel("./assets/data/conversion_factors.xlsx", sheet_name="Coal")

vats["Country_Code"] = vats["Country"].str[:2]
vats["Country"] = vats["Country"].str[5:]

null_df = pd.DataFrame(0, index=vats["Country"], columns=["Values"])
null_df["Country"] = null_df.index

vats = vats.set_index("Country")

existing_price["Country"] = existing_price["Country"].str[5:]
existing_price = existing_price.set_index("Country")
for fuel in fuel_types.keys():
    for country in vats.index:
        existing_price.loc[country,fuel] = existing_price.loc[country,fuel] * (1 + vats.loc[country,fuel])

conversion_factors = {
    "Gas Oil": conversion_gasoil,
    "Natural Gas": conversion_naturalgas,
    "Coal": conversion_coal,
    }
commodity_prices_2024 = pd.read_excel("./assets/data/commodity_prices_2024.xlsx", sheet_name="prices")

# helper functions
def fuel_conversion_to_kwh(start_unit, fuel, consumption):
    """Convert the consumption to kWh based on the fuel type and unit."""
    factor = conversion_factors[fuel].iloc[units[start_unit], units["kWh"]+1]
    kWh_consumption = consumption * factor
    return kWh_consumption

null_fig = px.choropleth(null_df,
                        locationmode="country names",
                        locations="Country",
                        scope="europe",
                        color="Values",
                        hover_name="Country",
                        width=750,
                        height=650,
                        basemap_visible=False,
                        projection="stereographic",
                        color_continuous_scale=px.colors.sequential.Blues,
                        fitbounds="locations"
) 
null_fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0},)                         
                            
ini_dataframe = pd.DataFrame(data=0, index=vats.index, columns=["Additional Costs for 10.000 kWh of Natural Gas"])

app = Dash(__name__)

app.layout = html.Div(
    style={
        "fontFamily": "Arial, sans-serif",
        "margin": "0 auto",
        "maxWidth": "1000px",
        "padding": "30px",
        "backgroundColor": "#f9f9f9"
    },
    children=[
        html.H1(
            "How much will ETS2 cost you?",
            style={"textAlign": "center", "color": "#2c3e50"}
        ),

        html.P(
            "In 2027 ETS2 will be rolled out across the EU. "
            "The main part of ETS2 is a carbon pricing mechanism for transportation and heating. "
            "With this dashboard, you can explore how heating price increases may affect you and the rest of Europe.",
            style={"fontSize": "16px", "lineHeight": "1.6", "color": "#555"}
        ),

        html.Div([
            
            html.Div([
                html.Div([
                    html.Label("Heating fuel"),
                    dcc.Dropdown(
                        id="fuel_dropdown",
                        options=[{"label": ft, "value": ft} for ft in fuel_types.keys()],
                        value="Natural Gas",
                        placeholder="Wähle ein Heizmittel"
                    )
                ], style={"flex": "1"}),

                html.Div([
                    html.Label("Yearly Consumption"),
                    dcc.Input(
                        id="consumption",
                        type="number",
                        min=0,
                        value=10000,
                        style={"width": "100%", "padding": "8px"}
                    )
                ], style={"flex": "1", "marginRight": "10px"}),

                html.Div([
                    html.Label("Unit"),
                    dcc.Dropdown(
                        id="unit_dropdown",
                        options=[{"label": unit, "value": unit} for unit, value in units.items() if value in [0, 3, 4]],
                        value="kWh",
                        placeholder="Wähle eine Einheit"
                    )
                ], style={"flex": "1", "marginLeft": "10px"})

            ], style={"display": "flex", "marginTop": "20px", "gap": "10px", "marginBottom": "20px"}),

            html.Label("Choose your country:", style={"marginTop": "20px"}),
            dcc.Dropdown(
                id="country_dropdown",
                options=[{"label": country, "value": country} for country in vats.index],
                value="Germany",
                placeholder="Wähle ein Land",
                style={"marginBottom": "20px"}
            ),

            html.Div([
                html.Div([
                    html.Label("Set CO₂ price (€/ton):", style={"marginTop": "20px", "marginBottom": "50px"}),
                    dcc.Slider(
                        id="co2_price",
                        min=0,
                        max=300,
                        value=50,
                        marks={0: "0", 150: "150", 300: "300"},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                ], style={"flex": "0 0 65%"}),
                html.Div([
                    html.Label("Adjust maximum CO₂ price:", style={"marginTop": "30px", "marginBottom": "10px"}),
                    html.Div([
                        dcc.Input(
                            id="max_price",
                            type="number",
                            value=300,
                            style={"width": "100%", "padding": "8px"}
                        ),
                        html.Div([
                            "€/tCO₂"
                        ], style={"marginTop": "8px", "marginLeft": "5px"})
                    ], style={"display": "flex"}),
                ], style={"flex": "0 0 35%"}),
            ], style={"display": "flex", "marginRight": "20px"})
        ], style={"backgroundColor": "#ffffff", "padding": "20px", "borderRadius": "8px", "boxShadow": "0 2px 5px rgba(0,0,0,0.1)"}),

        html.Br(),

        html.Div([
            html.Label("Your additional costs per year due to ETS2:"),
            html.Div(id="costs_text_output", style={
                "padding": "10px",
                "border": "1px solid #ccc",
                "borderRadius": "5px",
                "backgroundColor": "#f8f9fa",
                "width": "200px",
                "fontWeight": "bold",
                "marginTop": "5px"
            })
        ]),

        html.H2("Impact across Europe", style={"marginTop": "40px", "color": "#2c3e50"}),
        dcc.Graph(id="map", figure=null_fig),

        html.Div([
            html.H2("Data Table", style={"marginTop": "40px", "color": "#2c3e50"}),
            html.Button("Download Data as csv", id="download_dataframe_button", style={
                        "backgroundColor": "#2c3e50",
                        "color": "white",
                        "padding": "10px 10px",
                        "border": "none",
                        "borderRadius": "5px",
                        "fontSize": "16px",
                        "cursor": "pointer",
                        "marginLeft": "690px"
                        }),
            dcc.Download(id="download_dataframe")
        ], style={"display": "flex", "marginTop": "20px", "gap": "10px", "marginBottom": "20px"}),
    
        dash_table.DataTable(
            id="dataframe",
            data=ini_dataframe.to_dict("records"),
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "5px"},
            style_header={
                "backgroundColor": "#2c3e50",
                "color": "white",
                "fontWeight": "bold"
            },
            style_data={
                "backgroundColor": "#f4f4f4",
                "color": "#333"
            },
        )
    ]
)

# Callback zum Aktualisieren des Sliders
@app.callback(
    Output("co2_price", "max"),
    Output("co2_price", "marks"),
    Input("max_price", "value")
)
def update_slider_max(new_max):
    if new_max is None:
        return 300, {0: "0", 300: "300"}  # fallback
    return new_max, {0: "0", new_max: str(new_max)}


@app.callback(
    Output("unit_dropdown", "options"),
    Input("fuel_dropdown", "value")
)
def update_unit_dropdown_options(fuel_input):
    if fuel_input == "Gas Oil":
        return [unit for unit, value in units.items() if value in [0,1,2,4]]
    elif fuel_input == "Natural Gas":
        return [unit for unit, value in units.items() if value in [0,3,4]]
    elif fuel_input == "Coal":
        return [unit for unit, value in units.items() if value in [0,2,4]]
    else:
        return ["Fehler beim Laden der möglichen Einheiten"]

@app.callback(
        Output("map", "figure"),
        Output("dataframe", "data"),
        Output("costs_text_output", "children"),
        Input("fuel_dropdown", "value"),
        Input("unit_dropdown", "value"),
        Input("consumption", "value"),
        Input("co2_price", "value"),
        Input("country_dropdown", "value"),
        State("dataframe", "data"),
        State("map", "figure")
)
def calculations(fuel_input, unit_input, consumption_input, price_input, country_input, state_df, state_fig):
    
    ctx = callback_context
    
    triggered_input = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_input == "country_dropdown":
        df = pd.DataFrame(state_df)
        cols = df.columns
        costs_text = df[df["Country"]==country_input][cols[1]].values[0]
        return state_fig, state_df, f"{costs_text} €"
    
    add_price_per_kwh = pd.DataFrame(data=0, index=vats.index, columns=fuel_types.keys())

    if consumption_input == None or fuel_input == None or unit_input == None:
        return null_fig, add_price_per_kwh.to_dict("records"), "-"
    
    co2_price_per_kg = price_input / 1000

    for fuel in fuel_types.keys():

        add_price_per_kwh[fuel] = co2_price_per_kg * emission_factors[fuel][0]

        for country in vats.index:
            add_price_per_kwh.loc[country,fuel] = add_price_per_kwh.loc[country,fuel] * (1 + vats.loc[country,fuel])  
    add_price_per_kwh = add_price_per_kwh.sub(existing_price)

    consumption = consumption_input
    unit = unit_input
    fuel = fuel_input
    add_costs_user = pd.DataFrame([add_price_per_kwh.index, add_price_per_kwh[fuel].copy()], columns=add_price_per_kwh.index).T
    add_costs_user.columns = ["Country", fuel]

    consumption_kwh = fuel_conversion_to_kwh(unit, fuel, consumption)

    add_costs_user[fuel] = pd.to_numeric(add_costs_user[fuel], errors="coerce")  
    add_costs_user[fuel] = add_costs_user[fuel] * consumption_kwh

    add_costs_user = add_costs_user.round(2)
    map_data = add_costs_user

    fig = px.choropleth(map_data,    
                        locationmode="country names",
                        locations="Country",
                        scope="europe",
                        color=fuel_input,
                        hover_name="Country",
                        width=750,
                        height=650,
                        basemap_visible=False,
                        projection="stereographic",
                        color_continuous_scale=px.colors.sequential.Blues,
                        fitbounds="locations"
    ) 
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0},
                        coloraxis_colorbar=dict(
                            title="Costs",
                            tickprefix="€",
                            ticks="outside",
                            len=1,
                            y=0.5,
                        )
                      )

    costs_text = add_costs_user[add_costs_user["Country"]==country_input][fuel_input].values[0]

    add_costs_user.columns = ["Country", f"Additional Costs for {consumption_input} {unit_input} of {fuel_input}"]

    return fig, add_costs_user.to_dict("records"), f"{costs_text} €"

@app.callback(
        Output("download_dataframe", "data"),
        State("dataframe", "data"),
        State("consumption", "value"),
        State("fuel_dropdown", "value"),
        State("unit_dropdown", "value"),
        State("co2_price", "value"),
        Input("download_dataframe_button", "n_clicks"),
        prevent_initial_call=True
)
def download(df_as_dict, cons, fuel:str, unit:str, price, n_clicks):
    unit = unit.replace("³", "3")
    fuel = fuel.replace(" ", "")
    return dcc.send_data_frame(pd.DataFrame(df_as_dict).to_csv, f"data_{fuel}_{cons}_{unit}_price_{price}.csv")

##########################
if __name__ == "__main__":
    app.run(debug=True)