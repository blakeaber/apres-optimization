import os
import json

import pandas as pd
import plotly.express as px


def files_to_dynamic_variables(path: str):
    """Given a path, converts the files inside it to a dynamic_variables json.
    It expects specific file names"""

    dynamic_variables = {}

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

    # Store data
    with open(os.path.join(path, "dynamic_variables.json"), "w") as f:
        json.dump({"dynamic_variables": dynamic_variables}, f)


def solution_to_graph():
    """Displays the solution graph of the best solution inside the `solutions` folder"""
    df_solution = pd.read_csv("../scheduler/solutions/best_solution_front_format.csv")

    fig = px.line(
        df_solution,
        x="time",
        y=["vehicles", "demand"],
        title=f"Best solution with {df_solution['starts'].sum()} vehicles",
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

    fig.show()


if __name__ == "__main__":
    # files_to_dynamic_variables(
    #     "/Users/jorge/Documents/dev/alto_app/scheduler/user_input"
    # )
    solution_to_graph()
