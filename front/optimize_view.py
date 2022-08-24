import os
import subprocess
import json

import pandas as pd
import plotly.express as px
import dash
from dash import html, dcc, Output, callback, Input, State
import dash_bootstrap_components as dbc
import requests


# create output directories if not exists
solutions_directory_path = "./scheduler/solutions"
directory_exists = os.path.exists(solutions_directory_path)
if not directory_exists:
    os.makedirs(solutions_directory_path)

# Button states
BUTTON_STATE_NO_EXECUTION = "Start"
BUTTON_STATE_RUNNING_EXECUTION = "Running"


layout = html.Div(
    [
        html.Div(
            [
                html.H3("Settings"),
                html.Div(id="parameters-table"),
                dbc.Button(BUTTON_STATE_NO_EXECUTION, id="start-button", disabled=True),
                dcc.ConfirmDialog(
                    id="confirm-start",
                    message="This will stop any running scenarios. Are you sure?",
                ),
                html.Div(id="output-container-button"),
            ]
        ),
        html.Div(id="output-container"),
        dcc.Store(id="current-heartbeat"),
        dcc.Interval(
            id="interval-component", interval=3 * 1000, n_intervals=0  # in milliseconds
        ),
    ]
)


@callback(
    Output("confirm-start", "displayed"),
    Input("start-button", "n_clicks"),
    State("start-button", "children"),
)
def run_script_onClick(n_clicks, button_state):
    if not n_clicks:
        return dash.no_update

    # kill zombie optimization runs (if they exist)
    delete_previous_runs = (
        "ps aux | grep -ie '[p]ython optimizer_' | awk '{print $2}' | xargs kill -9 $1"
    )
    _ = subprocess.run(delete_previous_runs, shell=True)

    # run latest scenario
    if button_state == BUTTON_STATE_NO_EXECUTION:
        pass

    return True


@callback(
    Output("start-button", "children"),
    Output("output-container-button", "children"),
    Output("current-heartbeat", "data"),
    Input("interval-component", "n_intervals"),
)
def check_for_execution(_):
    # Directly download the output
    try:
        response = requests.get("http://alto_api/output/")
    except Exception:
        # Try to connect to localhost if running in debug mode
        response = requests.get("http://0.0.0.0/output/")

    data = response.json()
    if data["stage_id"] == 0:
        return (
            BUTTON_STATE_NO_EXECUTION,
            "No scheduler execution detected.",
            data,
        )
    return (
        BUTTON_STATE_RUNNING_EXECUTION,
        f"The optimizer is running and looking for a solution! Current stage: {data['stage']}.",
        data,
    )


@callback(
    Output("output-container", "children"),
    Output("parameters-table", "children"),
    Input("current-heartbeat", "data"),
)
def display_current_solution(current_heartbeat):
    if current_heartbeat["stage_id"] < 4:
        return dash.no_update

    solution_data, schedule_data = (
        current_heartbeat["solution"],
        current_heartbeat["schedule"],
    )
    if solution_data:
        df_solution = pd.read_json(json.dumps(solution_data), orient="split")
    if schedule_data:
        df_schedule = pd.read_json(
            json.dumps(schedule_data), orient="split"
        ).sort_values(["start_time", "duration"], ascending=True)

    schedule_fig = px.timeline(
        df_schedule, x_start="start_time", x_end="end_time", y="vehicle"
    )
    schedule_fig.update_yaxes(
        autorange="reversed"
    )  # otherwise tasks are listed from the bottom up

    fig = px.line(
        df_solution,
        x="time",
        y=["vehicles", "demand"],
        title=f"Best solution (run #{current_heartbeat['step']}) with {df_solution['starts'].sum()} vehicles",
    )
    fig.add_bar(
        x=df_solution["time"],
        y=df_solution["starts"],
        name="starts",
        marker={"color": "green"},
    )
    fig.add_bar(
        x=df_solution["time"],
        y=df_solution["ends"],
        name="ends",
        marker={"color": "red"},
    )

    # Min shifts if present
    if "min_shifts" in df_solution:
        fig.add_scatter(
            x=df_solution["time"],
            y=df_solution["min_shifts"],
            name="min_shifts",
            opacity=0.25,
            line={"color": "purple", "dash": "dash"},
        )

    # Parameters
    parameters_df = (
        pd.DataFrame.from_dict(
            current_heartbeat["payload"]["static_variables"], orient="index"
        )
        .transpose()
        .astype(str)
    )
    parameters_table1 = dbc.Table.from_dataframe(
        parameters_df.iloc[:, [0, 1, 2, 5, 6]], striped=True, size="sm"
    )
    parameters_table2 = dbc.Table.from_dataframe(
        parameters_df.iloc[:, 7:], striped=True, size="sm"
    )

    return html.Div(
        [
            html.Div(
                [
                    dcc.Graph(id="best-solution-graph", figure=fig),
                    dbc.Button("Download Solution", id="solution-download-button"),
                    dcc.Download(id="best-solution-download"),
                ]
            ),
            html.Div(
                [
                    dcc.Graph(id="best-schedule-graph", figure=schedule_fig),
                    dbc.Button("Download Schedule", id="schedule-download-button"),
                    dcc.Download(id="best-schedule-download"),
                ]
            ),
        ]
    ), html.Div([parameters_table1, parameters_table2])


@callback(
    Output("best-solution-download", "data"),
    Input("solution-download-button", "n_clicks"),
    State("current-heartbeat", "data"),
)
def func(n_clicks, current_heartbeat):
    if not n_clicks:
        return dash.no_update

    df = pd.read_json(json.dumps(current_heartbeat["solution"]), orient="split")
    return dcc.send_data_frame(df.to_csv, "best_solution.csv")


@callback(
    Output("best-schedule-download", "data"),
    Input("schedule-download-button", "n_clicks"),
    State("current-heartbeat", "data"),
)
def func(n_clicks, current_heartbeat):
    if not n_clicks:
        return dash.no_update

    df = pd.read_json(json.dumps(current_heartbeat["schedule"]), orient="split")
    return dcc.send_data_frame(df.to_csv, "best_schedule.csv")
