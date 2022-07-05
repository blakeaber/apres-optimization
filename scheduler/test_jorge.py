from math import ceil
from ortools.sat.python import cp_model


def compute_schedule(payload: dict):
    # Constants
    num_days = 1
    num_hours = 24
    num_minutes = 60
    minutes_interval = 15
    num_drivers = 3
    min_duration = 4 * 60  # hour * minutes
    max_duration = 10 * 60  # hour * minutes
    duration_step = 15  # minutes
    cost_driver_per_hour = 13.5
    cost_driver_per_minute = cost_driver_per_hour / 60
    revenue_passenger = 13.5

    # The states is [day, start_hour, start_minute, end_hour, end_minute, driver_id, shift_hours]
    # Ranges (for simplicity)
    all_days = range(num_days)
    all_hours = range(num_hours)
    all_minutes = range(0, num_minutes, minutes_interval)
    all_drivers = range(num_drivers)
    all_duration = range(min_duration, max_duration, duration_step)

    model = cp_model.CpModel()

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
        (driver, duration): model.NewBoolVar(f"selected_shift_{duration}")
        for driver in all_drivers
        for duration in all_duration
    }

    # A driver can only be assigned to a shift per day
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
            model.AddExactlyOne(
                assigned_shifts[(driver, duration)] for duration in all_duration
            )

    # DEBUG
    model.Add(shifts_state[(0, 4, 0, 0, 300)] == 1)

    # The sum of assigned minutes should be at least as the shift duration or 0
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
                    (sum(num_slots_worked) * minutes_interval) >= duration
                ).OnlyEnforceIf(assigned_shifts[(driver, duration)])
                model.Add(sum(num_slots_worked) == 0).OnlyEnforceIf(
                    assigned_shifts[(driver, duration)].Not()
                )

    # Input: demand
    demand = {
        (day, hour, minute): 1
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    }

    def _get_drivers_in_time(day, hour, minute):
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
                        _get_drivers_in_time(day, hour, minute),
                    ],
                )

    # Maximize the revenue (completion_rate*revenue - occupancy*cost = completion_rate * revenue_per_passenger - activer_driver * cost_per_driver)
    model.Maximize(
        sum(
            completion_rate[(day, hour, minute)] * revenue_passenger
            - _get_drivers_in_time(day, hour, minute) * cost_driver_per_minute
            for day in all_days
            for hour in all_hours
            for minute in all_minutes
        )
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

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
                                )
    else:
        print("No solution found.")


if __name__ == "__main__":
    compute_schedule({})
