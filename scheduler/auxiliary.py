"""OrTools related auxiliary functions"""
from ortools.sat.python import cp_model


def define_shift_state(
    model, all_days, all_hours, all_minutes, all_vehicles, all_duration
):
    """Define the state of all shifts"""
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
    return shifts_state


def define_assigned_shifts(model, all_vehicles, all_duration):
    """Auxiliary variable to track if a shift was assigned"""
    return {
        (vehicle, duration): model.NewBoolVar(
            f"selected_shift_driv{vehicle}_d{duration}"
        )
        for vehicle in all_vehicles
        for duration in all_duration
    }


def define_shifts_start(model, all_days, all_hours, all_minutes, all_vehicles):
    """Auxiliary variable to track when a shift starts"""
    return {
        (vehicle, day, hour, minute): model.NewBoolVar(
            f"shift_start_driv_{vehicle}_d{day}_h{hour}_m{minute}"
        )
        for vehicle in all_vehicles
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    }


def define_shifts_end(model, all_days, all_hours, all_minutes, all_vehicles):
    """Auxiliary variable to track when a shift ends"""
    return {
        (vehicle, day, hour, minute): model.NewBoolVar(
            f"shift_end_d{day}_h{hour}_m{minute}"
        )
        for vehicle in all_vehicles
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    }


def define_rush_hour(model, all_hours, all_minutes, rush_hour_input):
    """Auxiliary variable to track if we are in a rush hour"""
    rush_hour = {}
    for hour in all_hours:
        for minute in all_minutes:
            var = model.NewBoolVar(f"rush_hour_h{hour}")
            rush_hour[(hour, minute)] = var
            if rush_hour_input[(hour, minute)]:
                model.Add(var == 1)
    return rush_hour


def define_completion_rate(
    model,
    all_days,
    all_hours,
    all_minutes,
    all_vehicles,
    all_duration,
    num_vehicles,
    demand_input,
    shifts_state,
):
    """Auxiliary variable to define completion_rate
    The completion rate is the min between demand and vehicles
    """
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
                        demand_input[(day, hour, minute)],
                        get_vehicles_in_time(
                            shifts_state, day, hour, minute, all_vehicles, all_duration
                        ),
                    ],
                )
    return completion_rate


def negated_bounded_span(shifts, start, length):
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


def get_vehicles_in_time(shifts_state, day, hour, minute, all_vehicles, all_duration):
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


def get_vehicles_in_time_from_solver(
    solver: cp_model.CpSolverSolutionCallback,
    shifts_state,
    day,
    hour,
    minute,
    all_vehicles,
    all_duration,
):
    """Return the number of vehicles for a given timestamp.

    It uses the provided CpSolverSolutionCallback to get the assigned real values.
    """
    return sum(
        solver.Value(shifts_state[day, hour, minute, vehicle, duration])
        for vehicle in all_vehicles
        for duration in all_duration
    )


def define_min_shifts_to_vehicles_difference(
    model,
    shifts_state,
    minimum_shifts_input,
    num_vehicles,
    all_days,
    all_hours,
    all_minutes,
    all_vehicles,
    all_duration,
):
    """Defines a new Int variable that will hold the number of vehicles needed to meet
    the min_shifts requirement. Negative values are clamped to 0"""
    vehicles_to_min_shifts = {}
    for day in all_days:
        for hour in all_hours:
            for minute in all_minutes:
                vehicles_to_min_shifts[(day, hour, minute)] = model.NewIntVar(
                    -max(num_vehicles, minimum_shifts_input[(day, hour, minute)]),
                    max(num_vehicles, minimum_shifts_input[(day, hour, minute)]),
                    f"vehicles_to_min_shifts_d{day}_h{hour}_m{minute}",
                )
                model.AddMaxEquality(
                    vehicles_to_min_shifts[(day, hour, minute)],
                    [
                        0,
                        (
                            minimum_shifts_input[(day, hour, minute)]
                            - get_vehicles_in_time(
                                shifts_state,
                                day,
                                hour,
                                minute,
                                all_vehicles,
                                all_duration,
                            )
                        ),
                    ],
                )
    return vehicles_to_min_shifts
