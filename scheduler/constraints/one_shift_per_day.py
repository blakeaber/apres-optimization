from ortools.sat.python import cp_model


def one_shift_per_day(
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
