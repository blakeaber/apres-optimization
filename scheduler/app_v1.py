import time
from ortools.sat.python import cp_model


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    # Class to print all solutions found
    def __init__(self, variables):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__solution_count = 0
        self.__start_time = time.time()
        self._best_solution = 0

    def on_solution_callback(self):
        self.__solution_count += 1

        if self.ObjectiveValue() > self._best_solution:
            print(
                "Solution found:",
                self.__solution_count,
                "-",
                self.ObjectiveValue(),
                "-",
                round(time.time() - self.__start_time, 2),
            )
            arr = []
            for k, v in self.__variables[0].items():
                if self.Value(v) == 1:
                    arr.append([k[0], k[1], k[2], k[3], k[4]])
            df = pd.DataFrame(
                arr, columns=["day", "hour", "minute", "vehicle", "duration"]
            )
            df.to_csv("best_solution.csv", index=False)
        print()


def _negated_bounded_span(shifts, start, length):
    """From: https://github.com/google/or-tools/blob/master/examples/python/shift_scheduling_sat.py#L29
    Filters an isolated sub-sequence of variables assigned to True.
    Extract the span of Boolean variables [start, start + length), negate them,
    and if there is variables to the left/right of this span, surround the span by
    them in non negated form.
    Args:
        shifts: a list of shifts to extract the span from.
        start: the start to the span.
        length: the length of the span.
    Returns:
        a list of variables which conjunction will be false if the sub-list is
        assigned to True, and correctly bounded by variables assigned to False,
        or by the start or end of works.
    """
    sequence = []
    # Left border (start of works, or works[start - 1])
    if start > 0:
        sequence.append(shifts[start - 1])
    sequence.extend(shifts[start + i].Not() for i in range(length))
    # Right border (end of works or works[start + length])
    if start + length < len(shifts):
        sequence.append(shifts[start + length])
    return sequence


def _get_vehicles_in_time(shifts_state, day, hour, minute, all_vehicles, all_duration):
    """Return the number of vehicles for a given timestamp"""
    return cp_model.LinearExpr.Sum(
        [
            shifts_state[
                (
                    day,
                    hour,
                    minute,
                    vehicle,
                    duration,
                )
            ]
            for vehicle in all_vehicles
            for duration in all_duration
        ]
    )


def _constraint_one_shift_per_day(
    model: cp_model.CpModel,
    shifts_state,
    assigned_shifts,
    all_days,
    all_hours,
    all_minutes,
    all_vehicles,
    all_duration,
):
    for day in all_days:
        for vehicle in all_vehicles:
            for duration in all_duration:
                # If the shift was assigned, the shifts_state that day must have at least one. 0 Otherwise
                model.AddAtLeastOne(
                    shifts_state[
                        (
                            day,
                            s_hour,
                            s_minute,
                            vehicle,
                            duration,
                        )
                    ]
                    for s_hour in all_hours
                    for s_minute in all_minutes
                ).OnlyEnforceIf(assigned_shifts[(vehicle, duration)])
                model.Add(
                    cp_model.LinearExpr.Sum(
                        [
                            shifts_state[
                                (
                                    day,
                                    s_hour,
                                    s_minute,
                                    vehicle,
                                    duration,
                                )
                            ]
                            for s_hour in all_hours
                            for s_minute in all_minutes
                        ]
                    )
                    == 0
                ).OnlyEnforceIf(assigned_shifts[(vehicle, duration)].Not())
            # Only one type of assigned shift allowed (i.e. if 4h shift is chosen, no other shift duration can be set to 1)
            model.AddAtMostOne(
                assigned_shifts[(vehicle, duration)] for duration in all_duration
            )


def _constraint_shift_minimum_duration(
    model,
    shifts_state,
    assigned_shifts,
    all_days,
    all_hours,
    all_minutes,
    all_vehicles,
    all_duration,
    minutes_interval,
):
    # The sum of time worked must be the same as duration
    for vehicle in all_vehicles:
        for duration in all_duration:
            for day in all_days:
                num_slots_worked = []
                for s_hour in all_hours:
                    for s_minute in all_minutes:
                        num_slots_worked.append(
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
                model.Add(
                    (cp_model.LinearExpr.Sum(num_slots_worked) * minutes_interval)
                    == duration
                ).OnlyEnforceIf(assigned_shifts[(vehicle, duration)])
                model.Add(cp_model.LinearExpr.Sum(num_slots_worked) == 0).OnlyEnforceIf(
                    assigned_shifts[(vehicle, duration)].Not()
                )


def _constraint_shifts_contiguous(
    model,
    shifts_state,
    assigned_shifts,
    all_days,
    all_hours,
    all_minutes,
    all_vehicles,
    all_duration,
    minutes_interval,
):
    for vehicle in all_vehicles:
        for duration in all_duration:
            # For each duration, compute the number of slots it spans
            num_slots = int(duration / minutes_interval)
            # Get all the states for the corresponding duration
            shifts = [
                shifts_state[
                    (
                        day,
                        hour,
                        minute,
                        vehicle,
                        duration,
                    )
                ]
                for day in all_days
                for hour in all_hours
                for minute in all_minutes
            ]
            # Do not allow smaller slots than num_slots Bigger slots will be constraint by the sum of durations
            for length in range(1, num_slots):
                for start in range(len(shifts) - length + 1):
                    model.AddBoolOr(
                        _negated_bounded_span(shifts, start, length)
                    ).OnlyEnforceIf(assigned_shifts[(vehicle, duration)])


def _constraint_shift_start_and_shift_end(
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
):
    # TODO Make this function cleaner
    for vehicle in all_vehicles:
        for day in all_days:
            for duration in all_duration:
                # Just one start per day
                model.AddAtMostOne(
                    shifts_start[(vehicle, day, hour, minute)]
                    for hour in all_hours
                    for minute in all_minutes
                )
                # Just one end per day
                model.AddAtMostOne(
                    shifts_end[(vehicle, day, hour, minute)]
                    for hour in all_hours
                    for minute in all_minutes
                )
                for hour in all_hours:
                    for minute in all_minutes:
                        # Handle conditions to define start and end shifts
                        # Start: Previous 0 Current 1
                        # End: Current 1 Next 0
                        if (day == 0) and (hour == 0) and (minute == 0):
                            model.Add(
                                shifts_start[(vehicle, day, hour, minute)] == 1
                            ).OnlyEnforceIf(
                                shifts_state[
                                    (
                                        day,
                                        hour,
                                        minute,
                                        vehicle,
                                        duration,
                                    )
                                ],
                                shifts_state[
                                    (
                                        day,
                                        hour,
                                        minute + minutes_interval,
                                        vehicle,
                                        duration,
                                    )
                                ],
                            )
                        else:
                            if minute == 0:
                                model.Add(
                                    shifts_start[(vehicle, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            vehicle,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day if hour > 0 else day - 1,
                                            hour - 1 if hour > 0 else 23,
                                            num_minutes - minutes_interval,
                                            vehicle,
                                            duration,
                                        )
                                    ].Not(),
                                ),
                            else:
                                model.Add(
                                    shifts_start[(vehicle, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            vehicle,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute - minutes_interval,
                                            vehicle,
                                            duration,
                                        )
                                    ].Not(),
                                )
                        if (
                            (day == (num_days - 1))
                            and (hour == (num_hours - 1))
                            and (minute == (num_minutes - minutes_interval))
                        ):  # Last slot of the schedule
                            model.Add(
                                shifts_end[(vehicle, day, hour, minute)]
                                == shifts_state[
                                    (
                                        day,
                                        hour,
                                        minute,
                                        vehicle,
                                        duration,
                                    )
                                ]
                            )
                        else:
                            if minute == (60 - minutes_interval):
                                model.Add(
                                    shifts_end[(vehicle, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            vehicle,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day if hour < 23 else day + 1,
                                            hour + 1 if hour < 23 else 0,
                                            0,
                                            vehicle,
                                            duration,
                                        )
                                    ].Not(),
                                )
                            else:
                                model.Add(
                                    shifts_end[(vehicle, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            vehicle,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute + minutes_interval,
                                            vehicle,
                                            duration,
                                        )
                                    ].Not(),
                                )


def _constraint_max_starts_and_ends(
    model,
    shifts_start,
    shifts_end,
    all_days,
    all_hours,
    all_minutes,
    all_vehicles,
    max_starts_per_slot,
    max_ends_per_slot,
):
    # The sum of starts and ends per slot can't be higher than the max
    for day in all_days:
        for hour in all_hours:
            for minute in all_minutes:
                starts = cp_model.LinearExpr.Sum(
                    [
                        shifts_start[
                            (
                                vehicle,
                                day,
                                hour,
                                minute,
                            )
                        ]
                        for vehicle in all_vehicles
                    ]
                )
                ends = cp_model.LinearExpr.Sum(
                    [
                        shifts_end[
                            (
                                vehicle,
                                day,
                                hour,
                                minute,
                            )
                        ]
                        for vehicle in all_vehicles
                    ]
                )
                model.Add(starts <= max_starts_per_slot)
                model.Add(ends <= max_ends_per_slot)


def _constraint_rush_hours(
    model, shifts_end, rush_hour, all_vehicles, all_days, all_hours, all_minutes
):
    # If rush hour, can't end the shifth at that slot
    for vehicle in all_vehicles:
        for day in all_days:
            for hour in all_hours:
                for minute in all_minutes:
                    model.Add(
                        shifts_end[(vehicle, day, hour, minute)] == 0
                    ).OnlyEnforceIf(rush_hour[(hour, minute)])


def _constraint_minimum_shifts_per_hour(
    model,
    shifts_state,
    minimum_shifts,
    all_days,
    all_hours,
    all_vehicles,
    all_minutes,
    all_duration,
):
    # The sum of active vehicles per slot can't be smaller than the minimum specified shifts
    for day in all_days:
        for hour in all_hours:
            for minute in all_minutes:
                vehicles = _get_vehicles_in_time(
                    shifts_state, day, hour, minute, all_vehicles, all_duration
                )
                model.Add(vehicles >= minimum_shifts[(day, hour, minute)])


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
"""


def compute_schedule(payload: dict):
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

    rush_hour_input = payload["rush_hours"]

    # Market minimum shifts
    minimum_shifts = payload["minimum_shifts"]

    # Demand
    demand = payload["demand"]

    model = cp_model.CpModel()

    print("Defining variables and constraints")
    t0 = time.time()

    # Define all states
    shifts_state = {}
    for day in all_days:
        for s_hour in all_hours:
            for s_minute in all_minutes:
                for vehicle in all_vehicles:
                    for duration in all_duration:
                        shifts_state[
                            (
                                day,
                                s_hour,
                                s_minute,
                                vehicle,
                                duration,
                            )
                        ] = model.NewBoolVar(
                            "shift_day_%i_sH_%i_sM_%i_vehicle_%i_duration_%d"
                            % (
                                day,
                                s_hour,
                                s_minute,
                                vehicle,
                                duration,
                            )
                        )
    # Auxiliary variable to track if a shift was assigned
    assigned_shifts = {
        (vehicle, duration): model.NewBoolVar(
            f"selected_shift_driv{vehicle}_d{duration}"
        )
        for vehicle in all_vehicles
        for duration in all_duration
    }
    # Auxiliary variables to track when a shift starts & ends
    shifts_start = {
        (vehicle, day, hour, minute): model.NewBoolVar(
            f"shift_start_driv_{vehicle}_d{day}_h{hour}_m{minute}"
        )
        for vehicle in all_vehicles
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    }
    shifts_end = {
        (vehicle, day, hour, minute): model.NewBoolVar(
            f"shift_end_d{day}_h{hour}_m{minute}"
        )
        for vehicle in all_vehicles
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    }
    # Auxiliary variable to track if we are in a rush hour
    rush_hour = {}
    for hour in all_hours:
        for minute in all_minutes:
            var = model.NewBoolVar(f"rush_hour_h{hour}_d{day}")
            rush_hour[(hour, minute)] = var
            if rush_hour_input[(hour, minute)]:
                model.Add(var == 1)

    # Constraint 1: A vehicle can only be assigned to a shift per day
    _constraint_one_shift_per_day(
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
    _constraint_shift_minimum_duration(
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
    _constraint_shifts_contiguous(
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
    _constraint_minimum_shifts_per_hour(
        model,
        shifts_state,
        minimum_shifts,
        all_days,
        all_hours,
        all_vehicles,
        all_minutes,
        all_duration,
    )

    # # Constraint 5: Max amount of shifts that can start/end at the same time
    # Populate auxiliary variables
    _constraint_shift_start_and_shift_end(
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
    _constraint_max_starts_and_ends(
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
    _constraint_rush_hours(
        model, shifts_end, rush_hour, all_vehicles, all_days, all_hours, all_minutes
    )

    print(
        "\t Time:",
        round(time.time() - t0, 2),
        "seconds",
        round((time.time() - t0) / 60, 2),
        "minutes",
    )
    print("Defining objective function")
    t0 = time.time()

    # Auxiliary variable to define completion_rate,
    # The completion rate is the min between demand and vehicles
    completion_rate = {
        (day, hour, minute): model.NewIntVar(
            0, num_vehicles, f"completion_rate_d{day}_h{hour}_m{minute}"
        )
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    }
    for day in all_days:
        for hour in all_hours:
            for minute in all_minutes:
                model.AddMinEquality(
                    completion_rate[(day, hour, minute)],
                    [
                        demand[(day, hour, minute)],
                        _get_vehicles_in_time(
                            shifts_state, day, hour, minute, all_vehicles, all_duration
                        ),
                    ],
                )

    # Maximize the revenue (completion_rate*revenue - occupancy*cost = completion_rate * revenue_per_passenger - activer_vehicle * cost_per_vehicle)
    model.Maximize(
        cp_model.LinearExpr.Sum(
            [
                completion_rate[(day, hour, minute)] * revenue_passenger
                - _get_vehicles_in_time(
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
        "\t Time:",
        round(time.time() - t0, 2),
        "seconds",
        round((time.time() - t0) / 60, 2),
        "minutes",
    )
    print("Solving problem")
    t0 = time.time()

    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    status = solver.Solve(
        model, SolutionCollector([shifts_state, shifts_start, shifts_start])
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
        model.AddBoolOr(_negated_bounded_span([a, b], i, 2))
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
    }
    compute_schedule(inputs)
