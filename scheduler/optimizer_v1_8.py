import os
import pandas as pd
from ortools.sat.python import cp_model

from api.objects import HeartbeatStatus
from .solver import define_maximization_function, SolutionCollector
from .constraints import (
    one_shift_per_day,
    shift_min_duration,
    shifts_contiguous,
    min_shifts_per_hour,
    shift_span,
    max_start_and_end,
    rush_hours,
    market_hours,
    fixed_shifts,
)
from .auxiliary import (
    define_shift_state,
    define_assigned_shifts,
    define_shifts_start,
    define_shifts_end,
    define_rush_hour,
    define_completion_rate,
    define_min_shifts_to_vehicles_difference,
)


def compute_schedule(heartbeat: HeartbeatStatus):
    model = cp_model.CpModel()

    # Inputs
    num_days = heartbeat.payload.static_variables.num_days
    num_hours = heartbeat.payload.static_variables.num_hours
    num_minutes = heartbeat.payload.static_variables.num_minutes
    minutes_interval = heartbeat.payload.static_variables.minutes_interval
    num_vehicles = heartbeat.payload.static_variables.num_vehicles
    min_duration = (
        heartbeat.payload.static_variables.min_duration * 60
    )  # Convert to minutes
    max_duration = (
        heartbeat.payload.static_variables.max_duration * 60
    )  # Convert to minutes
    duration_step = heartbeat.payload.static_variables.duration_step
    cost_vehicle_per_minute = heartbeat.payload.static_variables.cost_vehicle_per_15min
    revenue_passenger = heartbeat.payload.static_variables.revenue_passenger
    max_starts_per_slot = heartbeat.payload.static_variables.max_starts_per_slot
    max_ends_per_slot = heartbeat.payload.static_variables.max_ends_per_slot
    rush_hour_soft_constraint_cost = (
        heartbeat.payload.static_variables.rush_hour_soft_constraint_cost
    )
    minimum_shifts_soft_constraint_cost = (
        heartbeat.payload.static_variables.minimum_shifts_soft_constraint_cost
    )

    # Constraint Flags
    enable_min_shift_constraint = (
        heartbeat.payload.static_variables.enable_min_shift_constraint
    )
    enable_rush_hour_constraint = (
        heartbeat.payload.static_variables.enable_rush_hour_constraint
    )
    enable_market_hour_constraint = (
        heartbeat.payload.static_variables.enable_market_hour_constraint
    )

    # The states is [day, start_hour, start_minute, end_hour, end_minute, vehicle_id, shift_hours]
    # Ranges (for the for-loops)
    total_minutes = num_minutes * num_hours * num_days
    all_minutes = range(0, total_minutes, minutes_interval)
    all_vehicles = range(num_vehicles)
    all_duration = range(min_duration, max_duration, duration_step)

    # Demand: Convert to constraint format
    demand_input = {
        (c["day"], c["hour"], c["minute"]): int(round(c["demand"]))
        for _, c in pd.read_json(
            heartbeat.payload.dynamic_variables.demand_forecast.json(), orient="split"
        ).iterrows()
    }

    # Rush Hours: Convert to constraint format
    if heartbeat.payload.dynamic_variables.rush_hours:
        rush_hour_input = {
            (c["hour"], c["minute"]): int(c["rush_hour"])
            for _, c in pd.read_json(
                heartbeat.payload.dynamic_variables.rush_hours.json(), orient="split"
            ).iterrows()
        }
    else:
        rush_hour_input = None

    # Market Hours: Convert to constraint format
    if heartbeat.payload.dynamic_variables.market_hours:
        market_hours_input = {
            (c["day"], c["hour"], c["minute"]): int(round(c["open"]))
            for _, c in pd.read_json(
                heartbeat.payload.dynamic_variables.market_hours.json(), orient="split"
            ).iterrows()
        }
    else:
        market_hours_input = None

    # Minimum Shifts: Convert to constraint format
    if heartbeat.payload.dynamic_variables.minimum_shifts:
        minimum_shifts_input = {
            (c["day"], c["hour"], c["minute"]): int(c["min_shifts"])
            for _, c in pd.read_json(
                heartbeat.payload.dynamic_variables.minimum_shifts.json(),
                orient="split",
            ).iterrows()
        }
    else:
        minimum_shifts_input = None

    # Fixed shifts: Convert to constraint format
    if heartbeat.payload.dynamic_variables.fixed_shifts:
        fixed_shifts_input = {
            (c["day"], c["hour"], c["minute"]): int(c["min_shifts"])
            for _, c in pd.read_json(
                heartbeat.payload.dynamic_variables.fixed_shifts.json(), orient="split"
            ).iterrows()
        }
    else:
        fixed_shifts_input = None

    heartbeat.set_stage(1)
    print("Defining Auxiliary Variables")

    # Define Auxiliary Variables
    shifts_state = define_shift_state(model, all_minutes, all_vehicles)
    # assigned_shifts = define_assigned_shifts(model, all_vehicles, all_duration)
    shifts_start = define_shifts_start(model, all_minutes, all_vehicles)
    shifts_end = define_shifts_end(model, all_minutes, all_vehicles)

    # Defining KPI Variable
    completion_rate = define_completion_rate(
        model,
        all_minutes,
        all_vehicles,
        num_vehicles,
        demand_input,
        shifts_state,
        num_hours,
        num_minutes,
    )

    heartbeat.set_stage(2)
    print("Defining Constraints")

    # Constraint 1: A vehicle can only be assigned to a shift per day
    # one_shift_per_day(
    #     model,
    #     shifts_state,
    #     assigned_shifts,
    #     all_days,
    #     all_hours,
    #     all_minutes,
    #     all_vehicles,
    #     all_duration,
    # )

    # Constraint 2: The sum of assigned minutes should be at least as the shift duration or 0
    # shift_min_duration(
    #     model,
    #     shifts_state,
    #     assigned_shifts,
    #     all_days,
    #     all_hours,
    #     all_minutes,
    #     all_vehicles,
    #     all_duration,
    #     minutes_interval,
    # )

    # Constraint 3: Shifts must expand in a continous window
    # in other words, do not allow smaller shifts
    # shifts_contiguous(
    #     model,
    #     shifts_state,
    #     assigned_shifts,
    #     all_days,
    #     all_hours,
    #     all_minutes,
    #     all_vehicles,
    #     all_duration,
    #     minutes_interval,
    # )

    # Constraint 4: Max amount of shifts that can start/end at the same time
    # Populate auxiliary variables
    sum_of_starts = {
        (vehicle, minute): model.NewIntVar(
            0, len(all_minutes), f"sum_of_starts_v{vehicle}_m{minute}"
        )
        for vehicle in all_vehicles
        for minute in all_minutes
    }
    sum_of_ends = {
        (vehicle, minute): model.NewIntVar(
            0, len(all_minutes), f"sum_of_ends_v{vehicle}_m{minute}"
        )
        for vehicle in all_vehicles
        for minute in all_minutes
    }
    sum_equals = {
        (vehicle, minute): model.NewBoolVar(f"sum_of_ends_v{vehicle}_m{minute}")
        for vehicle in all_vehicles
        for minute in all_minutes
    }

    # There must be at least one active state (i.e. one start)
    # We do this to avoid the "empty shifts case" and prevent
    # the solver to exploit that path, making it faster to find a feasible solution.
    model.AddAtLeastOne(shifts_start.values())

    shift_span(
        model,
        shifts_start,
        shifts_end,
        shifts_state,
        all_minutes,
        all_vehicles,
        all_duration,
        total_minutes,
        duration_step,
        sum_of_starts,
        sum_of_ends,
        sum_equals,
    )

    # Add max starts & ends constraint
    max_start_and_end(
        model,
        shifts_start,
        shifts_end,
        all_minutes,
        all_vehicles,
        max_starts_per_slot,
        max_ends_per_slot,
    )

    # Constraint 5: Minimum shifts per hour
    # This is also a soft-constraint, but if the hard-constraint is enabled the soft
    # do not play any role
    if enable_min_shift_constraint and minimum_shifts_input:
        min_shifts_per_hour(
            model,
            shifts_state,
            minimum_shifts_input,
            all_vehicles,
            all_minutes,
            all_duration,
            num_hours,
            num_minutes,
        )
    # Define a new variable to keep track of the difference between the min_shifts and
    # the actual vehicles. We need this to use the max() function in the solver
    vehicles_to_min_shifts = define_min_shifts_to_vehicles_difference(
        model,
        shifts_state,
        minimum_shifts_input,
        num_vehicles,
        all_minutes,
        all_vehicles,
        num_hours,
        num_minutes,
    )

    # Constraint 6: DO not end during rush hours
    # This is also a soft-constraint, but if the hard-constraint is enabled the soft
    # do not play any role
    if enable_rush_hour_constraint:
        rush_hour = define_rush_hour(
            model, all_minutes, rush_hour_input, num_hours, num_minutes
        )
        rush_hours(model, shifts_end, rush_hour, all_vehicles, all_minutes)

    # Constraint 7: No shifts during market closed hours
    # There are different ways to do this, i.e. `OnlyEnforceIf`, but I think this is the easiest and simplest one
    if enable_market_hour_constraint and market_hours_input:
        market_hours(
            model,
            shifts_state,
            market_hours_input,
            all_vehicles,
            all_minutes,
            num_hours,
            num_minutes,
        )

    # Constraint 8: Fixed shifts
    # if fixed_shifts_input:
    #     fixed_shifts(
    #         model,
    #         shifts_state,
    #         fixed_shifts_input,
    #     )

    heartbeat.set_stage(3)
    print("Constructing Optimization Problem")

    # Maximize the revenue (completion_rate*revenue - occupancy*cost = completion_rate * revenue_per_passenger - activer_vehicle * cost_per_vehicle)
    model.Maximize(
        define_maximization_function(
            shifts_state,
            completion_rate,
            revenue_passenger,
            cost_vehicle_per_minute,
            rush_hour_input,
            vehicles_to_min_shifts,
            all_vehicles,
            shifts_end,
            all_minutes,
            rush_hour_soft_constraint_cost,
            minimum_shifts_soft_constraint_cost,
            num_hours,
            num_minutes,
        )
    )

    # Everything was setup fine, remove previous solutions before starting the solver
    for f in os.listdir("./scheduler/solutions"):
        os.remove(f"./scheduler/solutions/{f}")

    heartbeat.set_stage(4)
    print("Finding Solutions")

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = (
        heartbeat.payload.num_search_workers
    )  # this enables multi-core processing of the search space
    solver.parameters.enumerate_all_solutions = (
        False  # cannot enumerate all solutions when solving in parallel
    )

    # solver callback to display and record interim solutions from the solver (on the journey to optimal solutions)
    status = solver.Solve(
        model,
        SolutionCollector(
            heartbeat,
            shifts_state,
            completion_rate,
            revenue_passenger,
            cost_vehicle_per_minute,
            rush_hour_input,
            vehicles_to_min_shifts,
            all_vehicles,
            all_duration,
            shifts_start,
            shifts_end,
            all_minutes,
            rush_hour_soft_constraint_cost,
            minimum_shifts_soft_constraint_cost,
            num_hours,
            num_minutes,
            sum_of_starts,
            sum_of_ends,
            sum_equals,
        ),
    )

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"Maximum of objective function: {solver.ObjectiveValue()}\n")
        sol_type = "Optimal" if status == cp_model.OPTIMAL else "Feasible"
        heartbeat.set_stage(5, f"Scheduler finished - {sol_type} solution found.")
    else:
        print("No solution found.")
        heartbeat.set_stage(5, "Scheduler finished - No solution found.")
