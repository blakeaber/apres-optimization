"""
Constraints:
- [x] Shift duration
- [x] Number of vehicles (same as number of vehicles?)
- [x] A vehicle can only be assigned to one shift per day
- [x] The sum of assigned time must be at least of the shift duration
- [x] The assigned shift slots must be consecutive
- [x] Minimum shifts per hour
- [x] Max amount of shifts that can start/end per minute slot
- [x] Don't end during rush hours
- [] Do not schedule shifts when the market is closed
"""

import time
from ortools.sat.python import cp_model
from scheduler import utils
from scheduler.constraints import (
    one_shift_per_day,
    shift_min_duration,
    shifts_contiguous,
    min_shifts_per_hour,
    shift_span,
    max_start_and_end,
    rush_hours,
    market_hours
)
from scheduler.auxiliary import (
    define_shift_state, 
    define_assigned_shifts, 
    define_shifts_start,
    define_shifts_end,
    define_rush_hour,
    define_completion_rate
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

    print("Defining Variables")
    t0 = time.time()

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

    print(f'Time: {round(time.time() - t0, 2)} Seconds, {round((time.time() - t0) / 60, 2)} Minutes')
    print("Defining Constraints")
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
    rush_hours(
        model, shifts_end, rush_hour, all_vehicles, all_days, all_hours, all_minutes
    )

    # Constraint 7: No shifts during market closed hours
    # There are different ways to do this, i.e. `OnlyEnforceIf`, but I think this is the easiest and simplest one
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

    print(f'Time: {round(time.time() - t0, 2)} Seconds, {round((time.time() - t0) / 60, 2)} Minutes')
    print("Setting Up Optimization Problem...")
    t0 = time.time()

    # Maximize the revenue (completion_rate*revenue - occupancy*cost = completion_rate * revenue_per_passenger - activer_vehicle * cost_per_vehicle)
    model.Maximize(
        cp_model.LinearExpr.Sum(
            [
                completion_rate[(day, hour, minute)] * revenue_passenger
                - utils._get_vehicles_in_time(
                    shifts_state, day, hour, minute, all_vehicles, all_duration
                )
                * cost_vehicle_per_minute
                for day in all_days
                for hour in all_hours
                for minute in all_minutes
            ]
        )
    )

    print(f'Time: {round(time.time() - t0, 2)} Seconds, {round((time.time() - t0) / 60, 2)} Minutes')
    print("Solving Optimization Problem...")
    t0 = time.time()

    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    status = solver.Solve(
        model, utils.SolutionCollector([shifts_state, shifts_start, shifts_start])
    )

    print(
        "\t Time:",
        round(time.time() - t0, 2),
        "seconds",
        round((time.time() - t0) / 60, 2),
        "minutes",
    )

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"Maximum of objective function: {solver.ObjectiveValue()}\n")
        print(
            "Type of solution:", "Optimal" if status == cp_model.OPTIMAL else "Feasible"
        )
        for day in all_days:
            for s_hour in all_hours:
                for s_minute in all_minutes:
                    for vehicle in all_vehicles:
                        for duration in all_duration:
                            if (
                                solver.Value(
                                    shifts_state[
                                        (
                                            day,
                                            s_hour,
                                            s_minute,
                                            vehicle,
                                            duration,
                                        )
                                    ]
                                )
                                == 1
                            ):
                                print(
                                    "day",
                                    day,
                                    "sHour",
                                    s_hour,
                                    "sMinute",
                                    s_minute,
                                    "vehicle",
                                    vehicle,
                                    "Duration",
                                    duration,
                                    "SHIFT_START",
                                    solver.Value(
                                        shifts_start[
                                            (
                                                vehicle,
                                                day,
                                                s_hour,
                                                s_minute,
                                            )
                                        ]
                                    ),
                                    "REAL",
                                    solver.Value(
                                        shifts_state[
                                            (
                                                day,
                                                s_hour,
                                                s_minute,
                                                vehicle,
                                                duration,
                                            )
                                        ]
                                    ),
                                    "SHIFT_END",
                                    solver.Value(
                                        shifts_end[
                                            (
                                                vehicle,
                                                day,
                                                s_hour,
                                                s_minute,
                                            )
                                        ]
                                    ),
                                )
    else:
        print("No solution found.")


def test():
    model = cp_model.CpModel()
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    a = model.NewBoolVar("a")
    b = model.NewBoolVar("b")
    # c = model.NewBoolVar("c")

    # 1 pair - 2 var
    for i in range(1):
        model.AddBoolOr(utils._negated_bounded_span([a, b], i, 2))
    # model.AddBoolOr([a, b])
    # model.AddBoolOr([a.Not(), b.Not()])

    # 2 pair - 2 var
    # model.AddBoolOr([a, b.Not()])
    # model.AddBoolOr([a, b])
    # model.AddBoolOr([a.Not(), b])

    # 1 pair - 3 var
    # model.AddBoolOr([a, b, c])
    # model.AddBoolOr([a.Not(), b.Not(), c.Not()])

    class SolutionCollector(cp_model.CpSolverSolutionCallback):
        def __init__(self, variables):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self.__variables = variables
            self.solution_list = []

        def on_solution_callback(self):
            self.solution_list.append([self.Value(v) for v in self.__variables])

    solution_collector = SolutionCollector([a, b])
    solver.SearchForAllSolutions(model, solution_collector)

    print(*solution_collector.solution_list, sep="\n")
    print(len(solution_collector.solution_list))


if __name__ == "__main__":
    import pandas as pd

    minimum_shifts = pd.read_csv("dallas_minimum_shifts.csv")
    minimum_shifts = {
        (c["day"], c["hour"], c["minute"]): int(c["min_shifts"])
        for _, c in minimum_shifts.iterrows()
    }
    rush_hours = pd.read_csv("dallas_rush_hours.csv")
    rush_hours = {
        (c["hour"], c["minute"]): int(c["rush_hour"]) for _, c in rush_hours.iterrows()
    }
    demand = pd.read_csv("dallas_forecast_v3_clip.csv")
    demand = {
        (c["day"], c["hour"], c["minute"]): int(round(c["demand"]))
        for _, c in demand.iterrows()
    }
    market_hours = pd.read_csv("dallas_market_hours.csv")
    market_hours = {
        (c["day"], c["hour"], c["minute"]): int(round(c["open"]))
        for _, c in market_hours.iterrows()
    }

    inputs = {
        "num_days": 1,
        "num_hours": 24,
        "num_minutes": 60,
        "minutes_interval": 15,
        "num_vehicles": 77,
        "min_duration": 4 * 60,
        "max_duration": 10 * 60,
        "duration_step": 15,
        "cost_vehicle_per_minute": 13.5 / 60,
        "revenue_passenger": 13.5,
        "max_starts_per_slot": 5,
        "max_ends_per_slot": 5,
        "minimum_shifts": minimum_shifts,
        "rush_hours": rush_hours,
        "demand": demand,
        "market_hours": market_hours,
    }
    compute_schedule(inputs)
