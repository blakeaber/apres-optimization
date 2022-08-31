from dash import html, dcc, Output, callback, Input, State
import dash_bootstrap_components as dbc

import io
import base64
import datetime
import pandas as pd

from dash import dcc, html, dash_table

drag_and_drop_css = {
    "width": "100%",
    "height": "60px",
    "lineHeight": "60px",
    "borderWidth": "1px",
    "borderStyle": "dashed",
    "borderRadius": "5px",
    "textAlign": "center",
    "margin": "10px",
}

demand_df = pd.DataFrame(
    data=[[0, 5, 15, 11]], columns=["day", "hour", "minute", "demand"]
)
demand_table = dbc.Table.from_dataframe(demand_df, striped=True, size="sm")
demand_jumbotron = dbc.Col(
    html.Div(
        [
            html.H4("Demand Forecast", className="display-10"),
            html.Hr(className="my-2"),
            html.P("See sample format below:"),
            demand_table,
            html.Div(["Please label the file ", html.B("constraint_demand.csv")]),
        ],
        className="p-5 bg-light border rounded-3",
    ),
    md=3,
)

min_shifts_df = pd.DataFrame(
    data=[[0, 23, 30, 3]], columns=["day", "hour", "minute", "min_shifts"]
)
min_shifts_table = dbc.Table.from_dataframe(min_shifts_df, striped=True, size="sm")
min_shifts_jumbotron = dbc.Col(
    html.Div(
        [
            html.H4("Minimum Shifts", className="display-10"),
            html.Hr(className="my-2"),
            html.P("See sample format below:"),
            min_shifts_table,
            html.Div(["Please label the file ", html.B("constraint_min_shifts.csv")]),
        ],
        className="p-5 bg-light border rounded-3",
    ),
    md=3,
)

market_hours_df = pd.DataFrame(
    data=[[0, 1, 45, 0]], columns=["day", "hour", "minute", "open"]
)
market_hours_table = dbc.Table.from_dataframe(market_hours_df, striped=True, size="sm")
market_hours_jumbotron = dbc.Col(
    html.Div(
        [
            html.H4("Market Hours", className="display-10"),
            html.Hr(className="my-2"),
            html.P("See sample format below:"),
            market_hours_table,
            html.P('"open" is either 0 or 1'),
            html.Div(["Please label the file ", html.B("constraint_market_hours.csv")]),
        ],
        className="p-5 bg-light border rounded-3",
    ),
    md=3,
)

rush_hours_df = pd.DataFrame(data=[[9, 0, 1]], columns=["hour", "minute", "rush_hour"])
rush_hours_table = dbc.Table.from_dataframe(rush_hours_df, striped=True, size="sm")
rush_hours_jumbotron = dbc.Col(
    html.Div(
        [
            html.H4("Rush Hours", className="display-10"),
            html.Hr(className="my-2"),
            html.P("See sample format below:"),
            rush_hours_table,
            html.P('"rush_hour" is either 0 or 1'),
            html.Div(["Please label the file ", html.B("constraint_rush_hours.csv")]),
        ],
        className="p-5 bg-light border rounded-3",
    ),
    md=3,
)

fixed_shifts_df = pd.DataFrame(
    data=[[0, 0, 0, 4, 30, 0, 9, 0]],
    columns=[
        "shift_id",
        "vehicle",
        "sday",
        "shour",
        "sminute",
        "eday",
        "ehour",
        "eminute",
    ],
)
fixed_shifts_table = dbc.Table.from_dataframe(fixed_shifts_df, striped=True, size="sm")
fixed_shifts_jumbotron = dbc.Col(
    html.Div(
        [
            html.H4("Fixed Shifts (Optional)", className="display-10"),
            html.Hr(className="my-2"),
            html.P("See sample format below:"),
            fixed_shifts_table,
            html.P('"shift_id" must be unique per id'),
            html.Div(["Please label the file ", html.B("constraint_fixed_shifts.csv")]),
        ],
        className="p-5 bg-light border rounded-3",
    ),
    md=6,
)

jumbotron = dbc.Row(
    [
        demand_jumbotron,
        min_shifts_jumbotron,
        market_hours_jumbotron,
        rush_hours_jumbotron,
        fixed_shifts_jumbotron,
    ],
    className="align-items-md-stretch",
)


layout = html.Div(
    [
        html.Div(
            [
                html.H4(
                    "Hi! Please upload data (in 15 minute increments) to create a schedule 😃"
                ),
                html.H6("When everything looks good, move on to the next step ✅"),
            ]
        ),
        html.Br(),
        jumbotron,
        dcc.Upload(
            id="upload-data",
            children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
            style=drag_and_drop_css,
            multiple=True,  # Allow multiple files to be uploaded
        ),
        html.Div(id="output-data-upload"),
    ]
)


def parse_contents(contents, filename, date):
    _, content_string = contents.split(",")

    decoded = base64.b64decode(content_string)
    try:
        if "csv" in filename:
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
            df.to_csv(f"./scheduler/user_input/{filename}", index=None)
        elif "xls" in filename:
            df = pd.read_excel(io.BytesIO(decoded))
            df.to_csv(f"./scheduler/user_input/{filename}", index=None)
    except Exception as e:
        print(e)
        return html.Div(["There was an error processing this file."])

    return html.Div(
        [
            html.H5(filename),
            html.H6(datetime.datetime.fromtimestamp(date)),
            dash_table.DataTable(
                df.to_dict("records"),
                [{"name": i, "id": i} for i in df.columns],
                page_size=5,
            ),
            html.Hr(),  # horizontal line
        ]
    )


@callback(
    Output("output-data-upload", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    State("upload-data", "last_modified"),
)
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d)
            for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)
        ]
        return children
