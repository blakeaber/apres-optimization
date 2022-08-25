from scheduler import utils


def shifts_contiguous(
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
                        utils.negated_bounded_span(shifts, start, length)
                    ).OnlyEnforceIf(assigned_shifts[(vehicle, duration)])
