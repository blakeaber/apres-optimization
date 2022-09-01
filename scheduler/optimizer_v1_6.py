import time
import json
import pandas as pd
from ortools.sat.python import cp_model

import utils
from constraints import (
    one_shift_per_day,
    shift_min_duration,
    shifts_contiguous,
    min_shifts_per_hour,
    shift_start_and_end_behaviour,
    max_start_and_end,
    rush_hours,
    market_hours,
)
from auxiliary import (
    define_shift_state,
    define_assigned_shifts,
    define_shifts_start,
    define_shifts_end,
    define_rush_hour,
    define_completion_rate,
)


def compute_schedule(payload: dict):
    model = cp_model.CpModel()

    # Inputs
    num_days = payload["num_days"]
    num_hours = payload["num_hours"]
    num_minutes = payload["num_minutes"]
    minutes_interval = payload["minutes_interval"]
    num_vehicles = payload["num_vehicles"]
    min_duration = payload["min_duration"]
    max_duration = payload["max_duration"]
    duration_step = payload["duration_step"]
    cost_vehicle_per_minute = payload["cost_vehicle_per_minute"]
    revenue_passenger = payload["revenue_passenger"]
    max_starts_per_slot = payload["max_starts_per_slot"]
    max_ends_per_slot = payload["max_ends_per_slot"]

    # Constraint Flags
    enable_min_shift_constraint = payload["enable_min_shift_constraint"]
    enable_rush_hour_constraint = payload["enable_rush_hour_constraint"]
    enable_market_hour_constraint = payload["enable_market_hour_constraint"]

    # The states is [day, start_hour, start_minute, end_hour, end_minute, vehicle_id, shift_hours]
    # Ranges (for the for-loops)
    all_days = range(num_days)
    all_hours = range(num_hours)
    all_minutes = range(0, num_minutes, minutes_interval)
    all_vehicles = range(num_vehicles)
    all_duration = range(min_duration, max_duration, duration_step)

    # Rush hours in market
    rush_hour_input = payload["rush_hours"]

    # Market minimum shifts
    minimum_shifts_input = payload["minimum_shifts"]

    # Demand
    demand_input = payload["demand"]

    # Market open/close hours (1/0)
    market_hours_input = payload["market_hours"]

    print("-- Defining Variables-- ")
    t0 = time.time()

    # Define Auxiliary Variables
    shifts_state = define_shift_state(
        model, all_days, all_hours, all_minutes, all_vehicles, all_duration
    )
    assigned_shifts = define_assigned_shifts(model, all_vehicles, all_duration)
    shifts_start = define_shifts_start(
        model, all_days, all_hours, all_minutes, all_vehicles
    )
    shifts_end = define_shifts_end(
        model, all_days, all_hours, all_minutes, all_vehicles
    )
    rush_hour = define_rush_hour(model, all_hours, all_minutes, rush_hour_input)

    # Defining KPI Variable
    completion_rate = define_completion_rate(
        model,
        all_days,
        all_hours,
        all_minutes,
        all_vehicles,
        all_duration,
        num_vehicles,
        demand_input,
        shifts_state,
    )

    print(
        f"Time: {round(time.time() - t0, 2)} Seconds, {round((time.time() - t0) / 60, 2)} Minutes"
    )
    print(f"At: {utils.get_current_time()}")
    print("-- Defining Constraints --")
    t0 = time.time()

    # Constraint 1: A vehicle can only be assigned to a shift per day
    one_shift_per_day(
        model,
        shifts_state,
        assigned_shifts,
        all_days,
        all_hours,
        all_minutes,
        all_vehicles,
        all_duration,
    )

    # Constraint 2: The sum of assigned minutes should be at least as the shift duration or 0
    shift_min_duration(
        model,
        shifts_state,
        assigned_shifts,
        all_days,
        all_hours,
        all_minutes,
        all_vehicles,
        all_duration,
        minutes_interval,
    )

    # Constraint 3: Shifts must expand in a continous window
    # in other words, do not allow smaller shifts
    shifts_contiguous(
        model,
        shifts_state,
        assigned_shifts,
        all_days,
        all_hours,
        all_minutes,
        all_vehicles,
        all_duration,
        minutes_interval,
    )

    # Constraint 4: Minimum shifts per hour
    if enable_min_shift_constraint:
        min_shifts_per_hour(
            model,
            shifts_state,
            minimum_shifts_input,
            all_days,
            all_hours,
            all_vehicles,
            all_minutes,
            all_duration,
        )

    # # Constraint 5: Max amount of shifts that can start/end at the same time
    # Populate auxiliary variables
    shift_start_and_end_behaviour(
        model,
        shifts_state,
        shifts_start,
        shifts_end,
        all_days,
        all_hours,
        all_minutes,
        all_vehicles,
        all_duration,
        minutes_interval,
        num_days,
        num_hours,
        num_minutes,
    )
    # Add max starts & ends constraint
    max_start_and_end(
        model,
        shifts_start,
        shifts_end,
        all_days,
        all_hours,
        all_minutes,
        all_vehicles,
        max_starts_per_slot,
        max_ends_per_slot,
    )

    # Constraint 6: DO not end during rush hours
    if enable_rush_hour_constraint:
        rush_hours(
            model, shifts_end, rush_hour, all_vehicles, all_days, all_hours, all_minutes
        )

    # Constraint 7: No shifts during market closed hours
    # There are different ways to do this, i.e. `OnlyEnforceIf`, but I think this is the easiest and simplest one
    if enable_market_hour_constraint:
        market_hours(
            model,
            shifts_state,
            market_hours_input,
            all_days,
            all_hours,
            all_vehicles,
            all_minutes,
            all_duration,
        )

    print(
        f"Time: {round(time.time() - t0, 2)} Seconds, {round((time.time() - t0) / 60, 2)} Minutes"
    )
    print(f"At: {utils.get_current_time()}")
    print("-- Setting Up Optimization Problem --")
    t0 = time.time()

    # Maximize the revenue (completion_rate*revenue - occupancy*cost = completion_rate * revenue_per_passenger - activer_vehicle * cost_per_vehicle)
    model.Maximize(
        cp_model.LinearExpr.Sum(
            [
                completion_rate[(day, hour, minute)] * revenue_passenger
                - utils.get_vehicles_in_time(
                    shifts_state, day, hour, minute, all_vehicles, all_duration
                )
                * cost_vehicle_per_minute
                for day in all_days
                for hour in all_hours
                for minute in all_minutes
            ]
        )
    )

    print(
        f"Time: {round(time.time() - t0, 2)} Seconds, {round((time.time() - t0) / 60, 2)} Minutes"
    )
    print(f"At: {utils.get_current_time()}")
    print("-- Solving Optimization Problem --")
    t0 = time.time()

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = (
        7  # this enables multi-core processing of the search space
    )
    solver.parameters.enumerate_all_solutions = (
        False  # cannot enumerate all solutions when solving in parallel
    )

    # solver callback to display and record interim solutions from the solver (on the journey to optimal solutions)
    status = solver.Solve(model, utils.SolutionCollector(shifts_state))

    print(
        f"Time: {round(time.time() - t0, 2)} Seconds, {round((time.time() - t0) / 60, 2)} Minutes"
    )
    print(f"At: {utils.get_current_time()}")
    print("-- Printing Solutions --")

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"Maximum of objective function: {solver.ObjectiveValue()}\n")
    else:
        print("No solution found.")


if __name__ == "__main__":

    # Read app settings from file (must be "latest" settings via callback)
    with open("./user_input/parameters.json", "r") as f:
        input_parameters = json.load(f)

    # Fixed parameters (based on daily optimization)
    input_parameters["num_days"] = 1
    input_parameters["num_hours"] = 24
    input_parameters["num_minutes"] = 60
    input_parameters["minutes_interval"] = 15
    input_parameters["duration_step"] = 15

    # Convert duration variables from hours to minutes
    input_parameters["min_duration"] *= 60
    input_parameters["max_duration"] *= 60

    # Read input files from folder
    # TODO: refactor and put into DataProvider object
    demand_input = pd.read_csv("./user_input/constraint_demand.csv")
    rush_hours_input = pd.read_csv("./user_input/constraint_rush_hours.csv")
    minimum_shifts_input = pd.read_csv("./user_input/constraint_min_shifts.csv")
    market_hours_input = pd.read_csv("./user_input/constraint_market_hours.csv")

    # Minimum Shifts: Convert to constraint format
    input_parameters["minimum_shifts"] = {
        (c["day"], c["hour"], c["minute"]): int(c["min_shifts"])
        for _, c in minimum_shifts_input.iterrows()
    }

    # Rush Hours: Convert to constraint format
    input_parameters["rush_hours"] = {
        (c["hour"], c["minute"]): int(c["rush_hour"])
        for _, c in rush_hours_input.iterrows()
    }

    # Demand: Convert to constraint format
    input_parameters["demand"] = {
        (c["day"], c["hour"], c["minute"]): int(round(c["demand"]))
        for _, c in demand_input.iterrows()
    }

    # Market Hours: Convert to constraint format
    input_parameters["market_hours"] = {
        (c["day"], c["hour"], c["minute"]): int(round(c["open"]))
        for _, c in market_hours_input.iterrows()
    }

    # RUN
    compute_schedule(input_parameters)
