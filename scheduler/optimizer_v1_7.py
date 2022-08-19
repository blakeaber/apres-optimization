
import time
import json
import pandas as pd
from api.objects import HeartbeatStatus
from ortools.sat.python import cp_model

import utils
from constraints import (
    one_shift_per_day,
    shift_min_duration,
    shifts_contiguous,
    min_shifts_per_hour,
    shift_span,
    max_start_and_end,
    rush_hours,
    market_hours
)
from auxiliary import (
    define_shift_state, 
    define_assigned_shifts, 
    define_shifts_start,
    define_shifts_end,
    define_rush_hour,
    define_completion_rate
)

def compute_schedule(heartbeat: HeartbeatStatus):
    model = cp_model.CpModel()

    # Inputs
    num_days = heartbeat.payload.num_days
    num_hours = heartbeat.payload.num_hours
    num_minutes = heartbeat.payload.num_minutes
    minutes_interval = heartbeat.payload.minutes_interval
    num_vehicles = heartbeat.payload.num_vehicles
    min_duration = heartbeat.payload.min_duration
    max_duration = heartbeat.payload.max_duration
    duration_step = heartbeat.payload.duration_step
    cost_vehicle_per_minute = heartbeat.payload.cost_vehicle_per_15min
    revenue_passenger = heartbeat.payload.revenue_passenger
    max_starts_per_slot = heartbeat.payload.max_starts_per_slot
    max_ends_per_slot = heartbeat.payload.max_ends_per_slot

    # Constraint Flags
    enable_min_shift_constraint = heartbeat.payload.enable_min_shift_constraint
    enable_rush_hour_constraint = heartbeat.payload.enable_rush_hour_constraint
    enable_market_hour_constraint = heartbeat.payload.enable_market_hour_constraint

    # The states is [day, start_hour, start_minute, end_hour, end_minute, vehicle_id, shift_hours]
    # Ranges (for the for-loops)
    all_days = range(num_days)
    all_hours = range(num_hours)
    all_minutes = range(0, num_minutes, minutes_interval)
    all_vehicles = range(num_vehicles)
    all_duration = range(min_duration, max_duration, duration_step)

    # Rush Hours: Convert to constraint format
    rush_hour_input = {
        (c["hour"], c["minute"]): int(c["rush_hour"]) for _, c 
        in pd.read_json(heartbeat.payload.rush_hours).iterrows()
    }

    # Demand: Convert to constraint format
    demand_input = {
        (c["day"], c["hour"], c["minute"]): int(round(c["demand"]))
        for _, c in pd.read_json(heartbeat.payload.demand_forecast).iterrows()
    }

    # Market Hours: Convert to constraint format
    market_hours_input = {
        (c["day"], c["hour"], c["minute"]): int(round(c["open"]))
        for _, c in pd.read_json(heartbeat.payload.market_hours).iterrows()
    }

    # Minimum Shifts: Convert to constraint format
    minimum_shifts_input = {
        (c["day"], c["hour"], c["minute"]): int(c["min_shifts"])
        for _, c in pd.read_json(heartbeat.payload.minimum_shifts).iterrows()
    }

    heartbeat.stage = 'Defining Auxiliary Variables'

    # Define Auxiliary Variables
    shifts_state = define_shift_state(model, all_days, all_hours, all_minutes, all_vehicles, all_duration)
    assigned_shifts = define_assigned_shifts(model, all_vehicles, all_duration)
    shifts_start = define_shifts_start(model, all_days, all_hours, all_minutes, all_vehicles)
    shifts_end = define_shifts_end(model, all_days, all_hours, all_minutes, all_vehicles)
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
        shifts_state
    )

    heartbeat.stage = 'Defining Constraints'

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
    shift_span(
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

    heartbeat.stage = 'Constructing Optimization Problem'

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

    heartbeat.stage = 'Finding Solutions'

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = heartbeat.payload.num_search_workers  # this enables multi-core processing of the search space
    solver.parameters.enumerate_all_solutions = False  # cannot enumerate all solutions when solving in parallel

    # solver callback to display and record interim solutions from the solver (on the journey to optimal solutions)
    status = solver.Solve(model, utils.SolutionCollector(shifts_state, heartbeat))

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"Maximum of objective function: {solver.ObjectiveValue()}\n")
    else:
        print("No solution found.")
