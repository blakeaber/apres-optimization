"""OrTools related auxiliary functions"""
from ortools.sat.python import cp_model
from scheduler.utils import expand_minutes_into_components


def define_shift_state(model, all_minutes, all_vehicles):
    """Define the state of all shifts"""
    shifts_state = {}
    for s_minute in all_minutes:
        for vehicle in all_vehicles:
            shifts_state[(s_minute, vehicle)] = model.NewBoolVar(
                "shift_day_m_%i_vehicle_%i"
                % (
                    s_minute,
                    vehicle,
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


def define_shifts_start(model, all_minutes, all_vehicles):
    """Auxiliary variable to track when a shift starts"""
    return {
        (vehicle, minute): model.NewBoolVar(f"shift_start_driv_{vehicle}_m{minute}")
        for vehicle in all_vehicles
        for minute in all_minutes
    }


def define_shifts_end(model, all_minutes, all_vehicles):
    """Auxiliary variable to track when a shift ends"""
    return {
        (vehicle, minute): model.NewBoolVar(f"shift_end_m{minute}")
        for vehicle in all_vehicles
        for minute in all_minutes
    }


def define_rush_hour(model, all_minutes, rush_hour_input, num_hours, num_minutes):
    """Auxiliary variable to track if we are in a rush hour"""
    rush_hour = {}
    for minute in all_minutes:
        day, hour, r_minute = expand_minutes_into_components(
            minute, num_hours, num_minutes
        )
        var = model.NewBoolVar(f"rush_hour_{minute}")
        rush_hour[minute] = var
        if rush_hour_input[(day, hour, r_minute)]:
            model.Add(var == 1)
    return rush_hour


def define_completion_rate(
    model,
    all_minutes,
    all_vehicles,
    num_vehicles,
    demand_input,
    shifts_state,
    num_hours,
    num_minutes,
):
    """Auxiliary variable to define completion_rate
    The completion rate is the min between demand and vehicles
    """
    completion_rate = {}
    for minute in all_minutes:
        completion_rate[minute] = model.NewIntVar(
            0, num_vehicles, f"completion_rate_m{minute}"
        )
        day, hour, r_minute = expand_minutes_into_components(
            minute, num_hours, num_minutes
        )
        model.AddMinEquality(
            completion_rate[minute],
            [
                demand_input[(day, hour, r_minute)],
                get_vehicles_in_time(shifts_state, minute, all_vehicles),
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


def get_vehicles_in_time(shifts_state, minute, all_vehicles):
    """Return the number of vehicles for a given timestamp"""
    return cp_model.LinearExpr.Sum(
        [
            shifts_state[
                (
                    minute,
                    vehicle,
                )
            ]
            for vehicle in all_vehicles
        ]
    )


def get_vehicles_in_time_from_solver(
    solver: cp_model.CpSolverSolutionCallback,
    shifts_state,
    minute,
    all_vehicles,
):
    """Return the number of vehicles for a given timestamp.

    It uses the provided CpSolverSolutionCallback to get the assigned real values.
    """
    return sum(solver.Value(shifts_state[minute, vehicle]) for vehicle in all_vehicles)


def define_min_shifts_to_vehicles_difference(
    model,
    shifts_state,
    minimum_shifts_input,
    num_vehicles,
    all_minutes,
    all_vehicles,
    num_hours,
    num_minutes,
):
    """Defines a new Int variable that will hold the number of vehicles needed to meet
    the min_shifts requirement. Negative values are clamped to 0"""
    vehicles_to_min_shifts = {}
    for minute in all_minutes:
        day, hour, r_minute = expand_minutes_into_components(
            minute, num_hours, num_minutes
        )
        vehicles_to_min_shifts[minute] = model.NewIntVar(
            -max(num_vehicles, minimum_shifts_input[(day, hour, r_minute)]),
            max(num_vehicles, minimum_shifts_input[(day, hour, r_minute)]),
            f"vehicles_to_min_shifts_m{minute}",
        )
        model.AddMaxEquality(
            vehicles_to_min_shifts[minute],
            [
                0,
                (
                    minimum_shifts_input[(day, hour, r_minute)]
                    - get_vehicles_in_time(
                        shifts_state,
                        minute,
                        all_vehicles,
                    )
                ),
            ],
        )
    return vehicles_to_min_shifts
