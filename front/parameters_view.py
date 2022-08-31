import json
from dash import html, Output, callback, Input, State
import dash_bootstrap_components as dbc


layout = html.Div(
    [
        dbc.Accordion(
            [
                dbc.AccordionItem(
                    [
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Minutes Between Time Ticks"),
                                dbc.Input(type="number", placeholder=15, disabled=True),
                            ],
                            className="mb-3",
                        ),
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Hours to simulate"),
                                dbc.Input(
                                    id="hours_to_simulate",
                                    type="number",
                                    placeholder=24,
                                    min=1,
                                    max=168,
                                    step=1,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Total Vehicles In Market"),
                                dbc.Input(
                                    id="vehicle_count",
                                    type="number",
                                    placeholder=20,
                                    min=1,
                                    max=100,
                                    step=1,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Minimum Shift Length (hours)"),
                                dbc.Input(
                                    id="min_shift",
                                    type="number",
                                    placeholder=4,
                                    min=1,
                                    max=23,
                                    step=1,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Maximum Shift Length (hours)"),
                                dbc.Input(
                                    id="max_shift",
                                    type="number",
                                    placeholder=10,
                                    min=1,
                                    max=23,
                                    step=1,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText(
                                    "Minimum Time Between Shifts (minutes)"
                                ),
                                dbc.Input(
                                    id="min_time_between_shifts",
                                    type="number",
                                    placeholder=30,
                                    min=0,
                                    step=15,
                                ),
                            ],
                            className="mb-3",
                        ),
                    ],
                    title="Shift Parameters",
                ),
                dbc.AccordionItem(
                    [
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Cost of the vehicle per minute"),
                                dbc.InputGroupText("$"),
                                dbc.Input(
                                    id="vehicle_cost",
                                    type="number",
                                    placeholder=2,
                                    min=1,
                                    max=25,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Revenue per trip"),
                                dbc.InputGroupText("$"),
                                dbc.Input(
                                    id="trip_revenue",
                                    type="number",
                                    placeholder=50,
                                    min=1,
                                    max=100,
                                    step=1,
                                ),
                            ],
                            className="mb-3",
                        ),
                    ],
                    title="Revenue Parameters",
                ),
                dbc.AccordionItem(
                    [
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText(
                                    "Maximum vehicle outflow every 15 minutes"
                                ),
                                dbc.Input(
                                    id="depot_starts",
                                    type="number",
                                    placeholder=5,
                                    min=1,
                                    max=15,
                                    step=1,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText(
                                    "Maximum vehicle inflow every 15 minutes"
                                ),
                                dbc.Input(
                                    id="depot_ends",
                                    type="number",
                                    placeholder=5,
                                    min=1,
                                    max=15,
                                    step=1,
                                ),
                            ],
                            className="mb-3",
                        ),
                    ],
                    title="Depot Parameters",
                ),
                dbc.AccordionItem(
                    [
                        dbc.InputGroup(
                            [
                                dbc.Checklist(
                                    options=[
                                        {"label": "Enforce Market Hours", "value": 1},
                                        {"label": "Enforce Rush Hours", "value": 2},
                                        {"label": "Enforce Minimum Shifts", "value": 3},
                                    ],
                                    value=[1],
                                    id="constraint_switches",
                                    inline=True,
                                    switch=True,
                                ),
                                dbc.FormText(
                                    "Too many hard constraints can lead to a lack of solutions"
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Cost of Rush Hour soft constraint"),
                                dbc.InputGroupText("$"),
                                dbc.Input(
                                    id="rush_hour_soft_constraint_cost",
                                    type="number",
                                    placeholder=0,
                                    min=0,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText(
                                    "Cost of Minimum Shifts soft constraint"
                                ),
                                dbc.InputGroupText("$"),
                                dbc.Input(
                                    id="minimum_shifts_soft_constraint_cost",
                                    type="number",
                                    placeholder=0,
                                    min=0,
                                ),
                            ],
                            className="mb-3",
                        ),
                    ],
                    title="Manage Constraints",
                ),
            ]
        ),
        html.Br(),
        html.Div(
            [
                dbc.Button("Submit", id="parameter-submit", className="me-2"),
                html.Hr(),
                html.Div(id="parameter-confirmation"),
            ]
        ),
    ]
)


@callback(
    Output("parameter-confirmation", "children"),
    Input("parameter-submit", "n_clicks"),
    State("hours_to_simulate", "value"),
    State("vehicle_count", "value"),
    State("min_shift", "value"),
    State("max_shift", "value"),
    State("min_time_between_shifts", "value"),
    State("vehicle_cost", "value"),
    State("trip_revenue", "value"),
    State("depot_starts", "value"),
    State("depot_ends", "value"),
    State("constraint_switches", "value"),
    State("rush_hour_soft_constraint_cost", "value"),
    State("minimum_shifts_soft_constraint_cost", "value"),
)
def on_save_params(
    n_clicks,
    hours_to_simulate,
    num_vehicles,
    min_shift,
    max_shift,
    min_time_between_shifts,
    vehicle_cost,
    trip_revenue,
    depot_starts,
    depot_ends,
    constraint_flags,
    rush_hour_soft_constraint_cost,
    minimum_shifts_soft_constraint_cost,
):
    if n_clicks is not None:
        parameter_settings = {
            "num_hours": hours_to_simulate,
            "num_vehicles": num_vehicles,
            "min_duration": min_shift,
            "max_duration": max_shift,
            "min_time_between_shifts": min_time_between_shifts,
            "cost_vehicle_per_minute": vehicle_cost,
            "revenue_passenger": trip_revenue,
            "max_starts_per_slot": depot_starts,
            "max_ends_per_slot": depot_ends,
            "enable_rush_hour_constraint": False,
            "enable_market_hour_constraint": False,
            "enable_min_shift_constraint": False,
            "rush_hour_soft_constraint_cost": rush_hour_soft_constraint_cost,
            "minimum_shifts_soft_constraint_cost": minimum_shifts_soft_constraint_cost,
        }

        if any([v == None for v in parameter_settings.values()]):
            return dbc.Alert(
                "Some values are not filled out... please resubmit", color="warning"
            )

        for value in constraint_flags:
            if value == 1:
                parameter_settings["enable_market_hour_constraint"] = True
            elif value == 2:
                parameter_settings["enable_rush_hour_constraint"] = True
            elif value == 3:
                parameter_settings["enable_min_shift_constraint"] = True
            else:
                pass

        with open("./scheduler/user_input/parameters.json", "w") as f:
            json.dump(parameter_settings, f)

        return dbc.Alert("Settings saved... Well done!", color="success")
