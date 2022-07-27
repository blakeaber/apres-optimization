

def rush_hours(model, shifts_end, rush_hour, all_vehicles, all_days, all_hours, all_minutes):
    # If rush hour, can't end the shifth at that slot
    for vehicle in all_vehicles:
        for day in all_days:
            for hour in all_hours:
                for minute in all_minutes:
                    model.Add(
                        shifts_end[(vehicle, day, hour, minute)] == 0
                    ).OnlyEnforceIf(rush_hour[(hour, minute)])
