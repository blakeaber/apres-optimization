
import os
import subprocess
import pandas as pd
import plotly.express as px

import dash
from dash import html, dcc, Output, callback, Input, State
import dash_bootstrap_components as dbc


layout = html.Div([
    html.Div([            
    dbc.Button('Start', id='start-button'),
    html.Div(id='output-container'),
    dcc.Store(id='best-solution-data'),
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

    _ = subprocess.Popen('python optimizer_v1_6.py', shell=True, cwd='./scheduler')  
    return dbc.Alert("We're off and running! Will report back in a bit...", color="success")


@callback(Output('output-container', 'children'),
          Input('best-solution-data', 'data'))
def get_scheduler_best_solution(jsonified_cleaned_data):

    df = pd.read_json(jsonified_cleaned_data, orient='split')

    fig = px.line(
        df,
        x="time",
        y=["vehicles", "demand"],
        title=f"Best solution with {df['starts'].sum()} vehicles",
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
    return html.Div([
        dcc.Graph(id="best-solution-graph", figure=fig),
        dbc.Button("Download CSV", id="download-button"),
        dcc.Download(id="best-solution-download"),
    ])


@callback(Output('best-solution-data', 'data'), Input('interval-component', 'n_intervals'))
def clean_data(n):

    all_solutions = [i for i in os.listdir("./scheduler/solutions") if i.startswith('best_solution_')]    
    if (not n) or (not all_solutions):
        return dash.no_update
    else:
        best_solution_id = max([int(i[:-4].split('best_solution_')[1]) for i in all_solutions])

        df = (
            pd.read_csv(f"./scheduler/solutions/best_solution_{best_solution_id}.csv")
            .sort_values(["day", "hour", "day"])
            .reset_index(drop=True)
        )
        df["time"] = df.apply(lambda row: f"{row['day']}-{row['hour']}-{row['minute']}", axis=1)

        starts = df.groupby("vehicle").first().groupby("time").size()
        ends = df.groupby("vehicle").last().groupby("time").size()
        df = df.groupby("time").size()
        df = pd.concat([df, starts, ends], axis=1).fillna(0)
        df.columns = ["vehicles", "starts", "ends"]
        df = df.astype(int).reset_index()

        demand = pd.read_csv(f"./scheduler/user_input/constraint_demand.csv")
        demand["time"] = demand.apply(lambda row: f"{row['day']}-{row['hour']}-{row['minute']}", axis=1)

        df = (
            df.merge(demand, on="time")
            .sort_values(["day", "hour", "day"])
            .reset_index(drop=True)
        )

        return df.to_json(date_format='iso', orient='split')


@callback(
    Output("best-solution-download", "data"),
    Input("download-button", "n_clicks"),
    State('best-solution-data', 'data'),
    prevent_initial_call=True
)
def func(n_clicks, jsonified_cleaned_data):
    if not n_clicks:
        return dash.no_update
    else:
        df = pd.read_json(jsonified_cleaned_data, orient='split')
        return dcc.send_data_frame(df.to_csv, "best_solution.csv")

