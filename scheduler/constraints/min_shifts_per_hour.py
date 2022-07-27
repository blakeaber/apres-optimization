from scheduler import utils


def min_shifts_per_hour(
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
                vehicles = utils._get_vehicles_in_time(
                    shifts_state, day, hour, minute, all_vehicles, all_duration
                )
                model.Add(vehicles >= minimum_shifts[(day, hour, minute)])
