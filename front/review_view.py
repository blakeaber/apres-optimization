
from subprocess import call
from dash import Dash, html, dcc, Output, callback, Input
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

# demand_df = pd.read_csv(f"./scheduler/user_input/constraint_demand.csv").sort_values(["hour", "minute"]).reset_index(drop=True)
# demand_df["time"] = demand_df.apply(lambda row: f"0-{row['hour']}-{row['minute']}", axis=1)

# demand_df = pd.DataFrame(data=[[0, 5, 15, 11]], columns=['day', 'hour', 'minute', 'demand'])
# demand_table = dbc.Table.from_dataframe(demand_df, striped=True, size='sm')
# demand_jumbotron = dbc.Col(
#     html.Div(
#         [
#             html.H4("Demand Forecast", className="display-10"),
#             html.Hr(className="my-2"),
#             html.P("See sample format below:"),
#             demand_table,
#             html.Div(["Please label the file ", html.B("constraint_demand.csv")])
#         ],
#         className="p-5 bg-light border rounded-3",
#     ),
#     md=3,
# )

# min_shifts_df = pd.DataFrame(data=[[0, 23, 30, 3]], columns=['day', 'hour', 'minute', 'min_shifts'])
# min_shifts_table = dbc.Table.from_dataframe(min_shifts_df, striped=True, size='sm')
# min_shifts_jumbotron = dbc.Col(
#     html.Div(
#         [
#             html.H4("Minimum Shifts", className="display-10"),
#             html.Hr(className="my-2"),
#             html.P("See sample format below:"),
#             min_shifts_table,
#             html.Div(["Please label the file ", html.B("constraint_min_shifts.csv")])
#         ],
#         className="p-5 bg-light border rounded-3",
#     ),
#     md=3,
# )

# market_hours_df = pd.DataFrame(data=[[0, 1, 45, 0]], columns=['day', 'hour', 'minute', 'open'])
# market_hours_table = dbc.Table.from_dataframe(market_hours_df, striped=True, size='sm')
# market_hours_jumbotron = dbc.Col(
#     html.Div(
#         [
#             html.H4("Market Hours", className="display-10"),
#             html.Hr(className="my-2"),
#             html.P("See sample format below:"),
#             market_hours_table,
#             html.P('"open" is either 0 or 1'),
#             html.Div(["Please label the file ", html.B("constraint_market_hours.csv")])
#         ],
#         className="p-5 bg-light border rounded-3",
#     ),
#     md=3,
# )

# rush_hours_df = pd.DataFrame(data=[[9, 0, 1]], columns=['hour', 'minute', 'rush_hour'])
# rush_hours_table = dbc.Table.from_dataframe(rush_hours_df, striped=True, size='sm')
# rush_hours_jumbotron = dbc.Col(
#     html.Div(
#         [
#             html.H4("Rush Hours", className="display-10"),
#             html.Hr(className="my-2"),
#             html.P("See sample format below:"),
#             rush_hours_table,
#             html.P('"rush_hour" is either 0 or 1'),
#             html.Div(["Please label the file ", html.B("constraint_rush_hours.csv")])
#         ],
#         className="p-5 bg-light border rounded-3",
#     ),
#     md=3,
# )

# jumbotron = dbc.Row(
#     [demand_jumbotron, min_shifts_jumbotron, market_hours_jumbotron, rush_hours_jumbotron],
#     className="align-items-md-stretch",
# )



layout = dbc.Card()

