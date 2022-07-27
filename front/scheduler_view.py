from subprocess import call
from dash import Dash, html, dcc, Output, callback, Input
import plotly.express as px

from others.data_provider import DebugDataProvider


def get_market_date_range():
    vehicles = data_provider.get_scheduler_best_solution()
    fig = px.line(
        vehicles,
        x="time",
        y=["vehicles", "demand"],
        title=f"Best solution with {vehicles['starts'].sum()} vehicles",
    )
    fig.add_bar(
        x=vehicles["time"],
        y=vehicles["starts"],
        name="starts",
        marker={"color": "green"},
    )
    fig.add_bar(
        x=vehicles["time"], y=vehicles["ends"], name="ends", marker={"color": "red"}
    )
    return fig


data_provider = DebugDataProvider()
data_provider.get_scheduler_best_solution()

layout = [
    html.Div(
        [
            dcc.Graph(id="scheduler-chart", figure=get_market_date_range()),
        ]
    ),
]
