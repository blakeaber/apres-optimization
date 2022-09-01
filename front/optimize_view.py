from datetime import datetime
import os
import json
from uuid import uuid4

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
BUTTON_STATE_RUNNING_EXECUTION = "Cancel"


layout = html.Div(
    [
        html.Div(
            [
                html.H3("Settings"),
                html.Div(id="parameters-table"),
                dbc.Button(BUTTON_STATE_NO_EXECUTION, id="start-button"),
                dcc.ConfirmDialog(
                    id="confirm-start",
                    message="This will stop any running scenarios. Are you sure?",
                ),
                html.Div(
                    id="output-container-button", style={"white-space": "pre-wrap"}
                ),
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
    State("current-heartbeat", "data"),
)
def run_script_onClick(n_clicks, button_state, heartbeat):
    if not n_clicks:
        return dash.no_update

    # Cancel if active
    if button_state == BUTTON_STATE_RUNNING_EXECUTION:
        run_id = heartbeat["payload"]["run_id"]
        requests.get(f"http://alto_api:8081/cancel/{run_id}")
        return False

    # Build the Post payload
    payload = {}

    # Static variables
    with open("./scheduler/user_input/parameters.json", "r") as f:
        payload["static_variables"] = json.load(f)

    # Dynamic variables
    dynamic_variables = {}
    path = "./scheduler/user_input/"

    # Demand
    specific_path = os.path.join(path, "constraint_demand.csv")
    if os.path.exists(specific_path):
        df = pd.read_csv(specific_path)
        dynamic_variables["demand_forecast"] = df.to_dict(orient="split")
    # Market Hours
    specific_path = os.path.join(path, "constraint_market_hours.csv")
    if os.path.exists(specific_path):
        df = pd.read_csv(specific_path)
        dynamic_variables["market_hours"] = df.to_dict(orient="split")
    # Min Shifts
    specific_path = os.path.join(path, "constraint_min_shifts.csv")
    if os.path.exists(specific_path):
        df = pd.read_csv(specific_path)
        dynamic_variables["minimum_shifts"] = df.to_dict(orient="split")
    # Rush Hours
    specific_path = os.path.join(path, "constraint_rush_hours.csv")
    if os.path.exists(specific_path):
        df = pd.read_csv(specific_path)
        dynamic_variables["rush_hours"] = df.to_dict(orient="split")
    # Fixed shifts
    specific_path = os.path.join(path, "constraint_fixed_shifts.csv")
    if os.path.exists(specific_path):
        df = pd.read_csv(specific_path)
        dynamic_variables["fixed_shifts"] = df.to_dict(orient="split")

    payload["dynamic_variables"] = dynamic_variables

    # Add a run_id and trigger execution
    payload["run_id"] = str(uuid4())

    try:
        requests.post("http://alto_api:8081/input/", json=payload)
    except Exception:
        # Try to connect to localhost if running in debug mode
        requests.post("http://0.0.0.0:8081/input/", json=payload)

    return False


@callback(
    Output("start-button", "children"),
    Output("start-button", "disabled"),
    Output("output-container-button", "children"),
    Output("current-heartbeat", "data"),
    Input("interval-component", "n_intervals"),
)
def check_for_execution(_):
    # Directly download the output
    try:
        response = requests.get("http://alto_api:8081/output/")
    except Exception:
        # Try to connect to localhost if running in debug mode
        response = requests.get("http://0.0.0.0:8081/output/")

    data = response.json()
    if data["stage_id"] == 0:
        return (
            BUTTON_STATE_NO_EXECUTION,
            False,
            "No scheduler execution detected.",
            data,
        )

    time_delta = None
    if data["start_time"]:
        if data["end_time"]:
            delta = (
                datetime.strptime(data["end_time"], "%Y-%m-%d %H:%M:%S")
                - datetime.strptime(data["start_time"], "%Y-%m-%d %H:%M:%S")
            ).seconds
        else:
            current = datetime.utcnow()
            old = datetime.strptime(data["start_time"], "%Y-%m-%d %H:%M:%S")
            delta = (current - old).seconds
        time_delta = f"{delta // 60} minutes {delta % 60} seconds"

    if data["stage_id"] in [5, -1]:
        return (
            BUTTON_STATE_NO_EXECUTION,
            False,
            f"""The optimizer was cancelled or found an optimal solution
            Current stage: {data['stage']}
            Start time: {data["start_time"] or "-"}
            End time: {data["end_time"] or "-"}
            Error message: {data["error_message"] or "-"}""",
            data,
        )
    else:
        return (
            BUTTON_STATE_RUNNING_EXECUTION,
            False,
            f"""The optimizer is running and looking for a solution
            Current stage: {data['stage']}
            Start time: {data["start_time"] or "-"}
            Time running: {time_delta or "-"}""",
            data,
        )


@callback(
    Output("output-container", "children"),
    Output("parameters-table", "children"),
    Input("current-heartbeat", "data"),
)
def display_current_solution(current_heartbeat):
    solution_data, schedule_data = (
        current_heartbeat["solution"],
        current_heartbeat["schedule"],
    )
    if solution_data:
        df_solution = pd.read_json(json.dumps(solution_data), orient="split")
    else:
        df_solution = pd.DataFrame(
            columns=[
                "time",
                "vehicles",
                "starts",
                "ends",
                "day",
                "hour",
                "minute",
                "demand",
                "min_shifts",
            ]
        )
    if schedule_data:
        df_schedule = pd.read_json(json.dumps(schedule_data), orient="split")
    else:
        df_schedule = pd.DataFrame(columns=["start_time", "end_time", "vehicle"])

    # GANTT chart
    schedule_fig = px.timeline(
        df_schedule, x_start="start_time", x_end="end_time", y="vehicle"
    )
    schedule_fig.update_yaxes(
        autorange="reversed"
    )  # otherwise tasks are listed from the bottom up

    # Vehicles over time chart
    solution_fig = px.line(
        df_solution,
        x="time",
        y=["vehicles", "demand"],
        title=f"""Best solution (run #{current_heartbeat['step']}) with {df_schedule['vehicle'].nunique()} vehicles. Total score: {current_heartbeat['total_score']:,}$ from which real score: {current_heartbeat['score_real']:,}$ and constraints cost: {current_heartbeat['score_constraints']:,}$""",
    )
    solution_fig.add_bar(
        x=df_solution["time"],
        y=df_solution["starts"],
        name="starts",
        marker={"color": "green"},
    )
    solution_fig.add_bar(
        x=df_solution["time"],
        y=df_solution["ends"],
        name="ends",
        marker={"color": "red"},
    )

    # Include min shifts if present
    if "min_shifts" in df_solution:
        solution_fig.add_scatter(
            x=df_solution["time"],
            y=df_solution["min_shifts"],
            name="min_shifts",
            opacity=0.25,
            line={"color": "purple", "dash": "dash"},
        )

    # Parameters table
    if (
        current_heartbeat["payload"]
        and current_heartbeat["payload"]["static_variables"]
    ):
        parameters_df = (
            pd.DataFrame.from_dict(
                current_heartbeat["payload"]["static_variables"], orient="index"
            )
            .transpose()
            .astype(str)
        )
        parameters_tables = [
            dbc.Table.from_dataframe(
                parameters_df.iloc[:, :5], striped=True, size="sm"
            ),
            dbc.Table.from_dataframe(
                parameters_df.iloc[:, 5:10], striped=True, size="sm"
            ),
            dbc.Table.from_dataframe(
                parameters_df.iloc[:, 10:], striped=True, size="sm"
            ),
        ]
    else:
        parameters_tables = []

    # Scores over time table
    if current_heartbeat["scores_over_time"]:
        scores_over_time_df = pd.DataFrame(
            current_heartbeat["scores_over_time"], columns=["real", "constraint"]
        )
        scores_over_time_df["total"] = (
            scores_over_time_df["real"] - scores_over_time_df["constraint"]
        )
        scores_over_time_df["constraint"] *= -1
        scores_over_time_fig = go.Figure()
        scores_over_time_fig.add_trace(
            go.Scatter(
                x=scores_over_time_df.index,
                y=scores_over_time_df["real"],
                fill="tozeroy",
                mode="lines",  # override default markers+lines
                line={"color": "green"},
                name="Real Score",
            )
        )
        scores_over_time_fig.add_trace(
            go.Scatter(
                x=scores_over_time_df.index,
                y=scores_over_time_df["constraint"],
                fill="tozeroy",
                mode="lines",
                line={"color": "red"},
                name="Constraints Cost",
            )
        )
        scores_over_time_fig.add_trace(
            go.Scatter(
                x=scores_over_time_df.index,
                y=scores_over_time_df["total"],
                mode="lines",
                line={"color": "yellow"},
                name="Total Score",
            )
        )
        scores_over_time_fig.update_layout(
            title="Scores over time", xaxis_title="Run #", yaxis_title="Score"
        )

    return html.Div(
        [
            html.Div(
                [
                    dcc.Graph(id="best-solution-graph", figure=solution_fig),
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
            html.Div(
                [
                    dcc.Graph(id="score-over-time-graph", figure=scores_over_time_fig),
                ]
            ),
        ]
    ), html.Div(parameters_tables)


@callback(
    Output("best-solution-download", "data"),
    Input("solution-download-button", "n_clicks"),
    State("current-heartbeat", "data"),
)
def download_solution_data(n_clicks, current_heartbeat):
    if not n_clicks:
        return dash.no_update

    df = pd.read_json(json.dumps(current_heartbeat["solution"]), orient="split")
    return dcc.send_data_frame(df.to_csv, "best_solution.csv")


@callback(
    Output("best-schedule-download", "data"),
    Input("schedule-download-button", "n_clicks"),
    State("current-heartbeat", "data"),
)
def download_scheduler_data(n_clicks, current_heartbeat):
    if not n_clicks:
        return dash.no_update

    df = pd.read_json(json.dumps(current_heartbeat["schedule"]), orient="split")
    return dcc.send_data_frame(df.to_csv, "best_schedule.csv")
