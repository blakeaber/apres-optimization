def rush_hours(model, shifts_end, rush_hour, all_vehicles, all_minutes):
    # If rush hour, can't end the shifth at that slot
    for vehicle in all_vehicles:
        for minute in all_minutes:
            model.Add(shifts_end[(vehicle, minute)] == 0).OnlyEnforceIf(
                rush_hour[minute]
            )
