import time
from ortools.sat.python import cp_model


def get_current_time():
    t = time.localtime()
    return time.strftime("%H:%M:%S", t)


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
