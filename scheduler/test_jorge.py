import time
from ortools.sat.python import cp_model


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


def _get_drivers_in_time(shifts_state, day, hour, minute, all_drivers, all_duration):
    """Return the number of drivers for a given timestamp"""
    return sum(
        shifts_state[
            (
                day,
                hour,
                minute,
                driver,
                duration,
            )
        ]
        for driver in all_drivers
        for duration in all_duration
    )


def _constraint_one_shift_per_day(
    model,
    shifts_state,
    assigned_shifts,
    all_days,
    all_hours,
    all_minutes,
    all_drivers,
    all_duration,
):
    for day in all_days:
        for driver in all_drivers:
            for duration in all_duration:
                model.Add(
                    sum(
                        shifts_state[
                            (
                                day,
                                s_hour,
                                s_minute,
                                driver,
                                duration,
                            )
                        ]
                        for s_hour in all_hours
                        for s_minute in all_minutes
                    )
                    > 0
                ).OnlyEnforceIf(assigned_shifts[(driver, duration)])
                model.Add(
                    sum(
                        shifts_state[
                            (
                                day,
                                s_hour,
                                s_minute,
                                driver,
                                duration,
                            )
                        ]
                        for s_hour in all_hours
                        for s_minute in all_minutes
                    )
                    == 0
                ).OnlyEnforceIf(assigned_shifts[(driver, duration)].Not())
            model.AddAtMostOne(
                assigned_shifts[(driver, duration)] for duration in all_duration
            )


def _constraint_shift_minimum_duration(
    model,
    shifts_state,
    assigned_shifts,
    all_days,
    all_hours,
    all_minutes,
    all_drivers,
    all_duration,
    minutes_interval,
):
    for day in all_days:
        for driver in all_drivers:
            for duration in all_duration:
                num_slots_worked = []
                for s_hour in all_hours:
                    for s_minute in all_minutes:
                        num_slots_worked.append(
                            shifts_state[
                                (
                                    day,
                                    s_hour,
                                    s_minute,
                                    driver,
                                    duration,
                                )
                            ]
                        )
                model.Add(
                    (sum(num_slots_worked) * minutes_interval) == duration
                ).OnlyEnforceIf(assigned_shifts[(driver, duration)])
                model.Add(sum(num_slots_worked) == 0).OnlyEnforceIf(
                    assigned_shifts[(driver, duration)].Not()
                )


def _constraint_shifts_contiguous(
    model,
    shifts_state,
    assigned_shifts,
    all_days,
    all_hours,
    all_minutes,
    all_drivers,
    all_duration,
    minutes_interval,
):
    for driver in all_drivers:
        for duration in all_duration:
            num_slots = int(duration / minutes_interval)
            shifts = [
                shifts_state[
                    (
                        day,
                        hour,
                        minute,
                        driver,
                        duration,
                    )
                ]
                for day in all_days
                for hour in all_hours
                for minute in all_minutes
            ]
            # Do not allow smaller slots
            for length in range(1, num_slots):
                for start in range(len(shifts) - length + 1):
                    model.AddBoolOr(
                        _negated_bounded_span(shifts, start, length)
                    ).OnlyEnforceIf(assigned_shifts[(driver, duration)])


def _constraint_shift_start_and_shift_end(
    model,
    shifts_state,
    shifts_start,
    shifts_end,
    all_days,
    all_hours,
    all_minutes,
    all_drivers,
    all_duration,
    minutes_interval,
    num_days,
    num_hours,
    num_minutes,
):
    # TODO Make this function cleaner
    for driver in all_drivers:
        for day in all_days:
            for duration in all_duration:
                model.AddAtMostOne(
                    shifts_start[(driver, day, hour, minute)]
                    for hour in all_hours
                    for minute in all_minutes
                )
                model.AddAtMostOne(
                    shifts_end[(driver, day, hour, minute)]
                    for hour in all_hours
                    for minute in all_minutes
                )
                for hour in all_hours:
                    for minute in all_minutes:
                        if (day == 0) and (hour == 0) and (minute == 0):
                            model.Add(
                                shifts_start[(driver, day, hour, minute)] == 1
                            ).OnlyEnforceIf(
                                shifts_state[
                                    (
                                        day,
                                        hour,
                                        minute,
                                        driver,
                                        duration,
                                    )
                                ],
                                shifts_state[
                                    (
                                        day,
                                        hour,
                                        minute + minutes_interval,
                                        driver,
                                        duration,
                                    )
                                ],
                            )
                        else:
                            if minute == 0:
                                model.Add(
                                    shifts_start[(driver, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            driver,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day if hour > 0 else day - 1,
                                            hour - 1 if hour > 0 else 23,
                                            num_minutes - minutes_interval,
                                            driver,
                                            duration,
                                        )
                                    ].Not(),
                                ),
                            else:
                                model.Add(
                                    shifts_start[(driver, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            driver,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute - minutes_interval,
                                            driver,
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
                                shifts_end[(driver, day, hour, minute)]
                                == shifts_state[
                                    (
                                        day,
                                        hour,
                                        minute,
                                        driver,
                                        duration,
                                    )
                                ]
                            )
                        else:
                            if minute == (60 - minutes_interval):
                                model.Add(
                                    shifts_end[(driver, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            driver,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day if hour < 23 else day + 1,
                                            hour + 1 if hour < 23 else 0,
                                            0,
                                            driver,
                                            duration,
                                        )
                                    ].Not(),
                                )
                            else:
                                model.Add(
                                    shifts_end[(driver, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            driver,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute + minutes_interval,
                                            driver,
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
    all_drivers,
    max_starts_per_slot,
    max_ends_per_slot,
):
    for day in all_days:
        for hour in all_hours:
            for minute in all_minutes:
                starts = sum(
                    shifts_start[
                        (
                            driver,
                            day,
                            hour,
                            minute,
                        )
                    ]
                    for driver in all_drivers
                )
                ends = sum(
                    shifts_end[
                        (
                            driver,
                            day,
                            hour,
                            minute,
                        )
                    ]
                    for driver in all_drivers
                )
                model.Add(starts <= max_starts_per_slot)
                model.Add(ends <= max_ends_per_slot)


def _constraint_rush_hours(
    model, shifts_end, rush_hour, all_drivers, all_days, all_hours, all_minutes
):
    for driver in all_drivers:
        for day in all_days:
            for hour in all_hours:
                for minute in all_minutes:
                    model.Add(
                        shifts_end[(driver, day, hour, minute)] == 0
                    ).OnlyEnforceIf(rush_hour[(hour, minute)])


def _constraint_minimum_shifts_per_hour(
    model,
    shifts_state,
    minimum_shifts,
    all_days,
    all_hours,
    all_drivers,
    all_minutes,
    all_duration,
):
    for day in all_days:
        for hour in all_hours:
            drivers = sum(
                _get_drivers_in_time(
                    shifts_state, day, hour, minute, all_drivers, all_duration
                )
                for minute in all_minutes
            )
            model.Add(minimum_shifts[(day, hour)] <= drivers)


"""
Constraints:
- [x] Shift duration
- [x] Number of drivers (same as number of vehicles?)
- [x] A driver can only be assigned to one shift per day
- [x] The sum of assigned time must be at least of the shift duration
- [x] The assigned shift slots must be consecutive
- [x] Minimum shifts per hour
- [x] Max amount of shifts that can start/end per minute slot
- [x] Don't end during rush hours
- [] Assume callouts
"""


def compute_schedule(payload: dict):
    # Constants
    num_days = 1
    num_hours = 24
    num_minutes = 60
    minutes_interval = 15
    num_drivers = 2
    min_duration = 4 * 60  # hour * minutes
    max_duration = 10 * 60  # hour * minutes
    duration_step = 15  # minutes
    cost_driver_per_hour = 13.5
    cost_driver_per_minute = cost_driver_per_hour / 60
    revenue_passenger = 13.5
    max_starts_per_slot = 1  # 4
    max_ends_per_slot = 1  # 4

    # The states is [day, start_hour, start_minute, end_hour, end_minute, driver_id, shift_hours]
    # Ranges (for simplicity)
    all_days = range(num_days)
    all_hours = range(num_hours)
    all_minutes = range(0, num_minutes, minutes_interval)
    all_drivers = range(num_drivers)
    all_duration = range(min_duration, max_duration, duration_step)

    rush_hour_input = {}
    for hour in all_hours:
        for minute in all_minutes:
            rush_hour_input[(hour, minute)] = 1 if hour in {6, 7, 8, 9, 11} else 0

    # Market minimum shifts
    minimum_shifts = {}
    for day in all_days:
        for hour in all_hours:
            minimum_shifts[(day, hour)] = 1 if hour in {15} else 0

    model = cp_model.CpModel()

    print("Defining variables and constraints")
    t0 = time.time()

    # Define all states
    shifts_state = {}
    for day in all_days:
        for s_hour in all_hours:
            for s_minute in all_minutes:
                for driver in all_drivers:
                    for duration in all_duration:
                        shifts_state[
                            (
                                day,
                                s_hour,
                                s_minute,
                                driver,
                                duration,
                            )
                        ] = model.NewBoolVar(
                            "shift_day_%i_sH_%i_sM_%i_driver_%i_duration_%d"
                            % (
                                day,
                                s_hour,
                                s_minute,
                                driver,
                                duration,
                            )
                        )
    # Auxiliary variable to track if a shift was assigned
    assigned_shifts = {
        (driver, duration): model.NewBoolVar(f"selected_shift_driv{driver}_d{duration}")
        for driver in all_drivers
        for duration in all_duration
    }
    # Auxiliary variable to track when a shift starts & ends
    shifts_start = {
        (driver, day, hour, minute): model.NewBoolVar(
            f"shift_start_driv_{driver}_d{day}_h{hour}_m{minute}"
        )
        for driver in all_drivers
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    }
    shifts_end = {
        (driver, day, hour, minute): model.NewBoolVar(
            f"shift_end_d{day}_h{hour}_m{minute}"
        )
        for driver in all_drivers
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

    # Constraint: A driver can only be assigned to a shift per day
    _constraint_one_shift_per_day(
        model,
        shifts_state,
        assigned_shifts,
        all_days,
        all_hours,
        all_minutes,
        all_drivers,
        all_duration,
    )

    # DEBUG
    model.Add(shifts_state[(0, 4, 0, 0, 300)] == 1)

    # Constraint: The sum of assigned minutes should be at least as the shift duration or 0
    _constraint_shift_minimum_duration(
        model,
        shifts_state,
        assigned_shifts,
        all_days,
        all_hours,
        all_minutes,
        all_drivers,
        all_duration,
        minutes_interval,
    )

    # Constraint: Shifts must expand in a continous window
    # in other words, do not allow smaller shifts
    _constraint_shifts_contiguous(
        model,
        shifts_state,
        assigned_shifts,
        all_days,
        all_hours,
        all_minutes,
        all_drivers,
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
        all_drivers,
        all_minutes,
        all_duration,
    )

    # # Constraint 6: Max amount of shifts that can start/end at the same time
    # Populate auxiliary variables
    _constraint_shift_start_and_shift_end(
        model,
        shifts_state,
        shifts_start,
        shifts_end,
        all_days,
        all_hours,
        all_minutes,
        all_drivers,
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
        all_drivers,
        max_starts_per_slot,
        max_ends_per_slot,
    )

    # Constraint 7: DO not end during rush hours
    _constraint_rush_hours(
        model, shifts_end, rush_hour, all_drivers, all_days, all_hours, all_minutes
    )

    # Input: demand
    demand = {
        (day, hour, minute): 1 if hour < 12 else 0
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    }

    print("\t Time:", round(time.time() - t0, 2), "seconds")
    print("Defining objective function")
    t0 = time.time()

    # Auxiliary variable to define completion_rate,
    # The completion rate is the min between demand and drivers
    completion_rate = {
        (day, hour, minute): model.NewIntVar(
            0, num_drivers, f"completion_rate_d{day}_h{hour}_m{minute}"
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
                        _get_drivers_in_time(
                            shifts_state, day, hour, minute, all_drivers, all_duration
                        ),
                    ],
                )

    # Maximize the revenue (completion_rate*revenue - occupancy*cost = completion_rate * revenue_per_passenger - activer_driver * cost_per_driver)
    model.Maximize(
        sum(
            completion_rate[(day, hour, minute)] * revenue_passenger
            - _get_drivers_in_time(
                shifts_state, day, hour, minute, all_drivers, all_duration
            )
            * cost_driver_per_minute
            for day in all_days
            for hour in all_hours
            for minute in all_minutes
        )
    )

    print("\t Time:", round(time.time() - t0, 2), "seconds")
    print("Solving problem")
    t0 = time.time()

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    print("\t Time:", round(time.time() - t0, 2), "seconds")

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"Maximum of objective function: {solver.ObjectiveValue()}\n")
        for day in all_days:
            for s_hour in all_hours:
                for s_minute in all_minutes:
                    for driver in all_drivers:
                        for duration in all_duration:
                            if (
                                solver.Value(
                                    shifts_state[
                                        (
                                            day,
                                            s_hour,
                                            s_minute,
                                            driver,
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
                                    "Driver",
                                    driver,
                                    "Duration",
                                    duration,
                                    "SHIFT_START",
                                    solver.Value(
                                        shifts_start[
                                            (
                                                driver,
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
                                                driver,
                                                duration,
                                            )
                                        ]
                                    ),
                                    "SHIFT_END",
                                    solver.Value(
                                        shifts_end[
                                            (
                                                driver,
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
    compute_schedule({})
