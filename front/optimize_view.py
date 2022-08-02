
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
        html.Div(id='output-container-button')
    ]),
    html.Div(id='output-container'),
    dcc.Store(id='best-solution-data'),
    dcc.Store(id='best-schedule-data'),
    dcc.Store(id='scheduler-process-id'),
    dcc.Interval(
        id='interval-component',
        interval=3*1000, # in milliseconds
        n_intervals=0
    )
])                      


@callback(
    Output('output-container-button', 'children'),
    Output('scheduler-process-id', 'data'),
    Input('start-button', 'n_clicks')
)
def run_script_onClick(n_clicks):
    if not n_clicks:
        return dash.no_update

    # delete old solutions from previous runs
    for f in os.listdir("./scheduler/solutions"):
        os.remove(f'./scheduler/solutions/{f}')

    pid = subprocess.Popen('python optimizer_v1_6.py', shell=True, cwd='./scheduler')
    alert = dbc.Alert(f"We're off and running (pid={pid.pid})! Will report back in a bit...", color="success")
    return alert, pid.pid


@callback(Output('output-container', 'children'),
          Input('best-solution-data', 'data'),
          Input('best-schedule-data', 'data'))
def get_scheduler_best_solution(jsonified_solution_data, jsonified_schedule_data):
    df_solution = pd.read_json(jsonified_solution_data, orient='split')
    df_schedule = pd.read_json(jsonified_schedule_data, orient='split').sort_values(['start_time', 'duration'], ascending=True)

    all_solutions = [i for i in os.listdir("./scheduler/solutions") if i.startswith('best_solution_')]    
    best_solution_id = max([int(i[:-4].split('best_solution_')[1]) for i in all_solutions])

    schedule_fig = px.timeline(df_schedule, x_start="start_time", x_end="end_time", y="vehicle")
    schedule_fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up

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
        x=df_solution["time"], y=df_solution["ends"], name="ends", marker={"color": "red"}
    )
    return html.Div([
        html.Div([
            dcc.Graph(id="best-solution-graph", figure=fig),
            dbc.Button("Download Solution", id="solution-download-button"),
            dcc.Download(id="best-solution-download")
        ]),
        html.Div([
            dcc.Graph(id="best-schedule-graph", figure=schedule_fig),
            dbc.Button("Download Schedule", id="schedule-download-button"),
            dcc.Download(id="best-schedule-download")
        ])
    ])


@callback(
    Output('best-solution-data', 'data'), 
    Input('interval-component', 'n_intervals'))
def clean_data(n):

    all_solutions = [i for i in os.listdir("./scheduler/solutions") if i.startswith('best_solution_')]    
    if (not n) or (not all_solutions):
        return dash.no_update
    else:
        best_solution_id = max([int(i[:-4].split('best_solution_')[1]) for i in all_solutions])

        df = (
            pd.read_csv(f"./scheduler/solutions/best_solution_{best_solution_id}.csv")
            .sort_values(["day", "hour", "minute"])
            .reset_index(drop=True)
        )
        df["time"] = df.apply(lambda row: f"{row['day'].astype(int)}-{row['hour'].astype(int)}-{row['minute'].astype(int)}", axis=1)

        starts = df.groupby("vehicle").first().groupby("time").size()
        ends = df.groupby("vehicle").last().groupby("time").size()
        df = df.groupby("time").size()

        df = pd.concat([df, starts, ends], axis=1).fillna(0)
        df.columns = ["vehicles", "starts", "ends"]
        df = df.astype(int).reset_index()

        demand = pd.read_csv(f"./scheduler/user_input/constraint_demand.csv")
        demand["time"] = demand.apply(lambda row: f"{row['day'].astype(int)}-{row['hour'].astype(int)}-{row['minute'].astype(int)}", axis=1)

        df = (
            df.merge(demand, on="time")
            .sort_values(["day", "hour", "minute"])
            .reset_index(drop=True)
        )

        return df.to_json(date_format='iso', orient='split')


@callback(
    Output('best-schedule-data', 'data'), 
    Input('interval-component', 'n_intervals'))
def clean_schedule_data(n):

    def get_start_time(df):
        """Based on the optimal schedule CSV, get the start times and duration (per vehicle)"""
        df = df.sort_values(['day', 'hour', 'minute'], ascending=True)
        return df.iloc[0][['day', 'hour', 'minute', 'duration']]

    all_solutions = [i for i in os.listdir("./scheduler/solutions") if i.startswith('best_solution_')]    
    if (not n) or (not all_solutions):
        return dash.no_update
    else:
        best_solution_id = max([int(i[:-4].split('best_solution_')[1]) for i in all_solutions])

        df = (
            pd.read_csv(f"./scheduler/solutions/best_solution_{best_solution_id}.csv")
            .sort_values(["day", "hour", "minute"])
            .reset_index(drop=True)
        )
        df["time"] = df.apply(lambda row: f"{row['day'].astype(int)}-{row['hour'].astype(int)}-{row['minute'].astype(int)}", axis=1)

        # Gantt chart: vehicle start times and duration (based on optimal schedules)
        schedule_df = df.groupby('vehicle').apply(get_start_time).sort_values(['day', 'hour', 'minute'], ascending=True).reset_index(drop=True)
        schedule_df.index.name = 'vehicle'
        schedule_df.reset_index(inplace=True)

        # Gantt chart: starting and ending timestamps
        schedule_df['start_time'] = pd.to_datetime(schedule_df.apply(lambda row: f'{row.hour.astype(int)}-{row.minute.astype(int)}', axis=1), format='%H-%M')
        schedule_df['end_time'] = schedule_df.apply(lambda row: row.start_time + pd.Timedelta(minutes=row.duration), axis=1)

        return schedule_df.to_json(date_format='iso', orient='split')


@callback(
    Output("best-solution-download", "data"),
    Input("solution-download-button", "n_clicks"),
    State('best-solution-data', 'data')
)
def func(n_clicks, jsonified_cleaned_data):
    if not n_clicks:
        return dash.no_update
    else:
        df = pd.read_json(jsonified_cleaned_data, orient='split')
        return dcc.send_data_frame(df.to_csv, "best_solution.csv")


@callback(
    Output("best-schedule-download", "data"),
    Input("schedule-download-button", "n_clicks"),
    State('best-schedule-data', 'data')
)
def func(n_clicks, jsonified_cleaned_data):
    if not n_clicks:
        return dash.no_update
    else:
        df = pd.read_json(jsonified_cleaned_data, orient='split')
        return dcc.send_data_frame(df.to_csv, "best_schedule.csv")
