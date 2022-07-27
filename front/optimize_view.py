
import os
import subprocess
import pandas as pd
import dash
from dash import Dash, html, dcc, Output, callback, Input
import dash_bootstrap_components as dbc
import plotly.express as px


layout = dbc.Card()


layout = html.Div([
    html.Div([            
    dbc.Button('Start', id='start-button'),
    html.Div(id='output-container-button'),
    html.Div(id='output-container-graph'),
    dcc.Interval(
        id='interval-component',
        interval=3*1000, # in milliseconds
        n_intervals=0
    )
    ])
])                      


empty_card = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H4("Results TBD", className="card-title"),
                html.P(
                    "As soon as the first solution comes in, we'll show it here "
                    "but remember, it's not guaranteed to be optimal!",
                    className="card-text",
                ),
            ]
        ),
    ],
    style={"width": "18rem"},
)


@callback(
    Output('output-container-button', 'children'),
    Input('start-button', 'n_clicks')
)
def run_script_onClick(n_clicks):
    if not n_clicks:
        return dash.no_update

    # delete old solutions from previous runs
    for f in os.listdir("./scheduler/solutions"):
        os.remove(f'./scheduler/solutions/{f}')

    _ = subprocess.Popen('python app_v1_6.py', shell=True, cwd='./scheduler')  
    return dbc.Alert("We're off and running! Will report back in a bit...", color="success")


@callback(Output('output-container-graph', 'children'),
            Input('interval-component', 'n_intervals'))
def get_scheduler_best_solution(n):

    # if not n:
    #     return dash.no_update
    
    # if not os.listdir("./scheduler/solutions"):
    #     return empty_card

    # try:
    #     all_solutions = sorted([int(i[:-4].split('best_solution_')) for i in os.listdir("./scheduler/solutions")])
    #     best_solution = int(all_solutions[-1][1])
    #     print(best_solution)
    # except:
    #     return empty_card

    step = 2

    df = (
        pd.read_csv(f"./scheduler/solutions/best_solution_{step}.csv")
        .sort_values(["day", "hour", "day"])
        .reset_index(drop=True)
    )
    df["time"] = (
        df["day"].astype(str)
        + "-"
        + df["hour"].astype(str)
        + "-"
        + df["minute"].astype(str)
    )

    starts = df.groupby("vehicle").first().groupby("time").size()
    ends = df.groupby("vehicle").last().groupby("time").size()
    df = df.groupby("time").size()
    df = pd.concat([df, starts, ends], axis=1).fillna(0)
    df.columns = ["vehicles", "starts", "ends"]
    df = df.astype(int).reset_index()

    demand = pd.read_csv(f"./scheduler/user_input/constraint_demand.csv")
    demand["time"] = (
        demand["day"].astype(str)
        + "-"
        + demand["hour"].astype(str)
        + "-"
        + demand["minute"].astype(str)
    )

    df = (
        df.merge(demand, on="time")
        .sort_values(["day", "hour", "day"])
        .reset_index(drop=True)
    )

    fig = px.line(
        df,
        x="time",
        y=["vehicles", "demand"],
        title=f"Best solution ({step}) with {df['starts'].sum()} vehicles",
    )
    fig.add_bar(
        x=df["time"],
        y=df["starts"],
        name="starts",
        marker={"color": "green"},
    )
    fig.add_bar(
        x=df["time"], y=df["ends"], name="ends", marker={"color": "red"}
    )
    return dcc.Graph(id="scheduler-chart", figure=fig)
