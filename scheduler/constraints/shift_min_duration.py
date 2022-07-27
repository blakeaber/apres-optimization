from ortools.sat.python import cp_model


def shift_min_duration(
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
