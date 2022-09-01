from scheduler.auxiliary import get_vehicles_in_time
from scheduler.utils import expand_minutes_into_components


def min_shifts_per_hour(
    model,
    shifts_state,
    minimum_shifts,
    all_vehicles,
    all_minutes,
    all_duration,
):
    """The sum of active vehicles per slot can't be smaller than the minimum specified shifts"""
    for minute in all_minutes:
        vehicles = get_vehicles_in_time(shifts_state, minute, all_vehicles)
        day, hour, r_minutes = expand_minutes_into_components(minute)
        model.Add(vehicles >= minimum_shifts[(day, hour, r_minutes)])
