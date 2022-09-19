import os
import pandas as pd

from ortools.sat.python import cp_model

from api.objects import HeartbeatStatus
from .solver import define_maximization_function, SolutionCollector
from .constraints import (
    min_shifts_per_hour,
    shift_start_and_end_behaviour,
    max_start_and_end,
    rush_hours,
    market_hours,
    fixed_shifts,
)
from .auxiliary import (
    define_shift_state,
    define_shifts_start,
    define_shifts_end,
    define_rush_hour,
    define_completion_rate,
    define_min_shifts_to_vehicles_difference,
    define_sum_of_ends,
    define_sum_of_equals,
    define_sum_of_starts,
)
from .utils import validate_fixed_shifts_input


def compute_schedule(heartbeat: HeartbeatStatus, multiprocess_pipe=None):
    """This function defines the model contraints, objective function and runs the
    optimizer until it finds an optimal or no-solution.

    Args:
        heartbeat (HeartbeatStatus): Status object which will be updated with the run information.
        multiprocess_pipe (_type_, optional): Multiprocessing pipe to send the current heartbeat object
            everytime it is updated. Defaults to None.
    """
    model = cp_model.CpModel()

    # Static Inputs
    num_hours = heartbeat.payload.static_variables.num_hours
    num_vehicles = heartbeat.payload.static_variables.num_vehicles
    min_duration = int(
        heartbeat.payload.static_variables.min_duration * 60
    )  # Convert to minutes
    max_duration = int(
        heartbeat.payload.static_variables.max_duration * 60
    )  # Convert to minutes
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
    min_time_between_shifts = heartbeat.payload.static_variables.min_time_between_shifts

    # Hard Constraints Flags
    enable_min_shift_constraint = (
        heartbeat.payload.static_variables.enable_min_shift_constraint
    )
    enable_rush_hour_constraint = (
        heartbeat.payload.static_variables.enable_rush_hour_constraint
    )
    enable_market_hour_constraint = (
        heartbeat.payload.static_variables.enable_market_hour_constraint
    )

    # Utility Ranges (for the for-loops)
    duration_step = 15  # In minutes. We default to every 15 minutes ticks.
    total_minutes = (
        60 * num_hours
    )  # We work in minutes, so we convert the hours into minutes.
    all_minutes = range(0, total_minutes, duration_step)
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
            (c["day"], c["hour"], c["minute"]): int(c["rush_hour"])
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

    # Fixed shifts: Convert to cosntraint format (list)
    if heartbeat.payload.dynamic_variables.fixed_shifts:
        df_fixed_shifts = pd.read_json(
            heartbeat.payload.dynamic_variables.fixed_shifts.json(), orient="split"
        )
        invalid_shifts = validate_fixed_shifts_input(
            df_fixed_shifts,
            duration_step,
            min_duration,
            max_duration,
            num_vehicles,
        )
        if invalid_shifts:
            raise ValueError("Fixed shifts input contains errors", invalid_shifts)
        fixed_shifts_input = df_fixed_shifts.iloc[:, 1:].to_numpy()
        del df_fixed_shifts
    else:
        fixed_shifts_input = None

    # Define the main and auxiliary variables for the model
    heartbeat.set_stage(1)
    if multiprocess_pipe:
        multiprocess_pipe.send(heartbeat)
    print("Defining Auxiliary Variables", flush=True)

    shifts_start = define_shifts_start(model, all_minutes, all_vehicles)
    shifts_end = define_shifts_end(model, all_minutes, all_vehicles)
    sum_of_starts = define_sum_of_starts(model, all_minutes, all_vehicles)
    sum_of_ends = define_sum_of_ends(model, all_minutes, all_vehicles)
    sum_equals = define_sum_of_equals(model, all_minutes, all_vehicles)
    shifts_state = define_shift_state(model, all_minutes, all_vehicles)

    # Auxiliary variable - It will be used to define the objective function
    completion_rate = define_completion_rate(
        model,
        all_minutes,
        all_vehicles,
        num_vehicles,
        demand_input,
        shifts_state,
    )

    # Define the constraints
    heartbeat.set_stage(2)
    if multiprocess_pipe:
        multiprocess_pipe.send(heartbeat)
    print("Defining Constraints", flush=True)

    # Constraint #1
    # There must be at least one active state (i.e. one start)
    # We do this to avoid the "empty shifts case" and prevent
    # the solver from exploiting that path, making it faster to find a feasible solution.
    model.AddAtLeastOne(shifts_start.values())

    # Constraint #2
    # This is the main constraints
    # Defines how the start and end of a shift must be constructed
    shift_start_and_end_behaviour(
        model,
        shifts_start,
        shifts_end,
        shifts_state,
        all_minutes,
        all_vehicles,
        all_duration,
        total_minutes,
        duration_step,
        min_time_between_shifts,
        sum_of_starts,
        sum_of_ends,
        sum_equals,
    )

    # Constraint #3: Max starts & ends per time slot
    max_start_and_end(
        model,
        shifts_start,
        shifts_end,
        all_minutes,
        all_vehicles,
        max_starts_per_slot,
        max_ends_per_slot,
    )

    # Constraint #4: Minimum shifts per hour
    # This is also a soft-constraint, but if the hard-constraint is enabled the soft
    # does not play any role
    if enable_min_shift_constraint and minimum_shifts_input:
        min_shifts_per_hour(
            model,
            shifts_state,
            minimum_shifts_input,
            all_vehicles,
            all_minutes,
            all_duration,
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
    )

    # Constraint #5: Do not end during rush hours
    # This is also a soft-constraint, but if the hard-constraint is enabled the soft
    # does not play any role
    if enable_rush_hour_constraint:
        rush_hour = define_rush_hour(model, all_minutes, rush_hour_input)
        rush_hours(model, shifts_end, rush_hour, all_vehicles, all_minutes)

    # Constraint #6: No shifts during market closed hours
    if enable_market_hour_constraint and market_hours_input:
        market_hours(
            model,
            shifts_state,
            market_hours_input,
            all_vehicles,
            all_minutes,
        )

    # Constraint #7: Fixed shifts
    if fixed_shifts_input is not None:
        fixed_shifts(model, shifts_start, shifts_end, fixed_shifts_input)

    # Define the optimization function
    heartbeat.set_stage(3)
    if multiprocess_pipe:
        multiprocess_pipe.send(heartbeat)
    print("Constructing Optimization Problem", flush=True)

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
        )
    )

    # Everything was setup fine, remove previous solutions before starting the solver
    for f in os.listdir("./scheduler/solutions"):
        os.remove(f"./scheduler/solutions/{f}")

    # Run the scheduler
    heartbeat.set_stage(4)
    if multiprocess_pipe:
        multiprocess_pipe.send(heartbeat)
    print("Finding Solutions", flush=True)

    model.AddDecisionStrategy(
        shifts_start.values(), cp_model.CHOOSE_FIRST, cp_model.SELECT_MAX_VALUE
    )
    model.AddDecisionStrategy(
        shifts_end.values(), cp_model.CHOOSE_FIRST, cp_model.SELECT_MAX_VALUE
    )

    solver = cp_model.CpSolver()
    solver.parameters.num_workers = (
        heartbeat.payload.num_workers
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
            shifts_start,
            shifts_end,
            all_minutes,
            rush_hour_soft_constraint_cost,
            minimum_shifts_soft_constraint_cost,
            multiprocess_pipe,
        ),
    )

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"Maximum of objective function: {solver.ObjectiveValue()}\n", flush=True)
        sol_type = "Optimal" if status == cp_model.OPTIMAL else "Feasible"
        heartbeat.set_stage(5, f"Scheduler finished - {sol_type} solution found.")
    else:
        print("No solution found.", flush=True)
        heartbeat.set_stage(5, "Scheduler finished - No solution found.")
    heartbeat.set_end_time()
    if multiprocess_pipe:
        multiprocess_pipe.send(heartbeat)

        # Finish process and close the process pipe
        multiprocess_pipe.send(None)
        multiprocess_pipe.close()
