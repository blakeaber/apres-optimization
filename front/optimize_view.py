import os
import subprocess
import pandas as pd
import plotly.express as px

import dash
from dash import html, dcc, Output, callback, Input, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc


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
                html.Div(id="output-container-button"),
            ]
        ),
        html.Div(id="output-container"),
        dcc.Store(id="best-solution-data"),
        dcc.Store(id="best-schedule-data"),
        dcc.Interval(
            id="interval-component", interval=3 * 1000, n_intervals=0  # in milliseconds
        ),
    ]
)


@callback(Output("parameters-table", "children"), Input("start-button", "n_clicks"))
def display_parameters(n_clicks):
    parameters_df = pd.read_json(
        "./scheduler/user_input/parameters.json", lines=True
    ).astype(int)
    parameters_table1 = dbc.Table.from_dataframe(
        parameters_df.iloc[:, :5], striped=True, size="sm"
    )
    parameters_table2 = dbc.Table.from_dataframe(
        parameters_df.iloc[:, 5:], striped=True, size="sm"
    )
    return html.Div([parameters_table1, parameters_table2])


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
        # delete old solutions from previous runs
        for f in os.listdir("./scheduler/solutions"):
            os.remove(f"./scheduler/solutions/{f}")
        _ = subprocess.Popen("python optimizer_v1_6.py", shell=True, cwd="./scheduler")

    return True


@callback(
    Output("start-button", "children"),
    Output("start-button", "style"),
    Output("output-container-button", "children"),
    Input("start-button", "n_clicks"),
    Input("interval-component", "n_intervals"),
    State("start-button", "children"),
)
def check_for_execution(_, __, button_state):
    get_process_time = "ps aux | grep -ie '[p]ython optimizer_' | grep -v '/bin/sh' | awk '{print $10}'"
    if process_output := subprocess.run(
        get_process_time, shell=True, capture_output=True, text=True
    ).stdout:
        process_info = f"The optimizer is running and looking for a solution! Current running time: {process_output} minutes."
        return BUTTON_STATE_RUNNING_EXECUTION, {"background": "red"}, process_info
    else:
        return BUTTON_STATE_NO_EXECUTION, None, None


@callback(
    Output("output-container", "children"),
    Input("best-solution-data", "data"),
    Input("best-schedule-data", "data"),
    State("start-button", "children"),
)
def get_scheduler_best_solution(
    jsonified_solution_data, jsonified_schedule_data, button_state
):
    if jsonified_solution_data:
        df_solution = pd.read_json(jsonified_solution_data, orient="split")
    if jsonified_schedule_data:
        df_schedule = pd.read_json(jsonified_schedule_data, orient="split").sort_values(
            ["start_time", "duration"], ascending=True
        )

    all_solutions = [
        i for i in os.listdir("./scheduler/solutions") if i.startswith("best_solution_")
    ]
    if not all_solutions:
        if button_state == BUTTON_STATE_NO_EXECUTION:
            return "No solution found for last run."
        else:
            return "No solution found yet..."

    best_solution_id = max(
        int(i[:-4].split("best_solution_")[1]) for i in all_solutions
    )

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
        title=f"Best solution (run #{best_solution_id}) with {df_solution['starts'].sum()} vehicles",
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
    )


@callback(
    Output("best-solution-data", "data"), Input("interval-component", "n_intervals")
)
def clean_data(n):

    all_solutions = [
        i for i in os.listdir("./scheduler/solutions") if i.startswith("best_solution_")
    ]
    if (not n) or (not all_solutions):
        return ""
    else:
        best_solution_id = max(
            [int(i[:-4].split("best_solution_")[1]) for i in all_solutions]
        )

        df = (
            pd.read_csv(f"./scheduler/solutions/best_solution_{best_solution_id}.csv")
            .sort_values(["day", "hour", "minute"])
            .reset_index(drop=True)
        )
        df["time"] = df.apply(
            lambda row: f"{row['day'].astype(int)}-{row['hour'].astype(int)}-{row['minute'].astype(int)}",
            axis=1,
        )

        starts = df.groupby("vehicle").first().groupby("time").size()
        ends = df.groupby("vehicle").last().groupby("time").size()
        df = df.groupby("time").size()

        df = pd.concat([df, starts, ends], axis=1).fillna(0)
        df.columns = ["vehicles", "starts", "ends"]
        df = df.astype(int).reset_index()

        demand = pd.read_csv(f"./scheduler/user_input/constraint_demand.csv")
        demand["time"] = demand.apply(
            lambda row: f"{row['day'].astype(int)}-{row['hour'].astype(int)}-{row['minute'].astype(int)}",
            axis=1,
        )

        df = (
            df.merge(demand, on="time")
            .sort_values(["day", "hour", "minute"])
            .reset_index(drop=True)
        )

        return df.to_json(date_format="iso", orient="split")


@callback(
    Output("best-schedule-data", "data"), Input("interval-component", "n_intervals")
)
def clean_schedule_data(n):
    def get_start_time(df):
        """Based on the optimal schedule CSV, get the start times and duration (per vehicle)"""
        df = df.sort_values(["day", "hour", "minute"], ascending=True)
        return df.iloc[0][["day", "hour", "minute", "duration"]]

    all_solutions = [
        i for i in os.listdir("./scheduler/solutions") if i.startswith("best_solution_")
    ]
    if (not n) or (not all_solutions):
        return ""
    else:
        best_solution_id = max(
            [int(i[:-4].split("best_solution_")[1]) for i in all_solutions]
        )

        df = (
            pd.read_csv(f"./scheduler/solutions/best_solution_{best_solution_id}.csv")
            .sort_values(["day", "hour", "minute"])
            .reset_index(drop=True)
        )
        df["time"] = df.apply(
            lambda row: f"{row['day'].astype(int)}-{row['hour'].astype(int)}-{row['minute'].astype(int)}",
            axis=1,
        )

        # Gantt chart: vehicle start times and duration (based on optimal schedules)
        schedule_df = (
            df.groupby("vehicle")
            .apply(get_start_time)
            .sort_values(["day", "hour", "minute"], ascending=True)
            .reset_index(drop=True)
        )
        schedule_df.index.name = "vehicle"
        schedule_df.reset_index(inplace=True)

        # Gantt chart: starting and ending timestamps
        schedule_df["start_time"] = pd.to_datetime(
            schedule_df.apply(
                lambda row: f"{row.hour.astype(int)}-{row.minute.astype(int)}", axis=1
            ),
            format="%H-%M",
        )
        schedule_df["end_time"] = schedule_df.apply(
            lambda row: row.start_time + pd.Timedelta(minutes=row.duration), axis=1
        )

        return schedule_df.to_json(date_format="iso", orient="split")


@callback(
    Output("best-solution-download", "data"),
    Input("solution-download-button", "n_clicks"),
    State("best-solution-data", "data"),
)
def func(n_clicks, jsonified_cleaned_data):
    if not n_clicks:
        return dash.no_update
    else:
        df = pd.read_json(jsonified_cleaned_data, orient="split")
        return dcc.send_data_frame(df.to_csv, "best_solution.csv")


@callback(
    Output("best-schedule-download", "data"),
    Input("schedule-download-button", "n_clicks"),
    State("best-schedule-data", "data"),
)
def func(n_clicks, jsonified_cleaned_data):
    if not n_clicks:
        return dash.no_update
    else:
        df = pd.read_json(jsonified_cleaned_data, orient="split")
        return dcc.send_data_frame(df.to_csv, "best_schedule.csv")
