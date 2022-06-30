from subprocess import call
from dash import Dash, html, dcc, Output, callback, Input
import plotly.express as px

from others.data_provider import DebugDataProvider


# Forecast tab data provider
data_provider = DebugDataProvider()

# Load initial data
markets_list = data_provider.get_market_list()


@callback(
    Output(component_id="forecast-date-range", component_property="min_date_allowed"),
    Output(component_id="forecast-date-range", component_property="max_date_allowed"),
    Output(component_id="forecast-date-range", component_property="start_date"),
    Output(component_id="forecast-date-range", component_property="end_date"),
    Input(component_id="markets-dropdown", component_property="value"),
)
def get_market_date_range(market):
    min_date, max_date = data_provider.get_market_forecast_date_range(market)
    return min_date, max_date, min_date, max_date


@callback(
    Output(component_id="forecast-chart", component_property="figure"),
    Input(component_id="markets-dropdown", component_property="value"),
    Input(component_id="forecast-date-range", component_property="start_date"),
    Input(component_id="forecast-date-range", component_property="end_date"),
)
def get_forecast_data(market, start_date, end_date):
    data = data_provider.get_market_forecast_data(market, start_date, end_date)
    return px.line(data, x=data.index, y=["forecast", "real"])


layout = [
    html.Div(
        [
            dcc.Dropdown(markets_list, markets_list[0], id="markets-dropdown"),
            dcc.DatePickerRange(
                id="forecast-date-range",
            ),
        ]
    ),
    html.Div([dcc.Graph(id="forecast-chart")]),
]
