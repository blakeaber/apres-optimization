from subprocess import call
from dash import Dash, html, dcc, Output, callback, Input
import plotly.express as px

from others.data_provider import DebugDataProvider

data_provider = DebugDataProvider()


@callback(
    Output(component_id="scheduler-chart", component_property="figure"),
    Input(component_id="refresh-button", component_property="n_clicks"),
)
def get_market_date_range(market):
    drivers = data_provider.get_scheduler_best_solution()
    fig = px.line(
        drivers,
        x="time",
        y=["drivers", "demand"],
        title=f"Best solution with {drivers['starts'].sum()} drivers",
    )
    fig.add_bar(
        x=drivers["time"], y=drivers["starts"], name="starts", marker={"color": "green"}
    )
    fig.add_bar(
        x=drivers["time"], y=drivers["ends"], name="ends", marker={"color": "red"}
    )
    return fig


data_provider.get_scheduler_best_solution()

layout = [
    html.Div(
        [
            html.Button(id="refresh-button", children=html.Div("Refresh")),
            dcc.Graph(id="scheduler-chart"),
        ]
    ),
]