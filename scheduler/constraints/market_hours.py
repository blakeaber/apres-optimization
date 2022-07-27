

def market_hours(
    model,
    shifts_state,
    market_hours,
    all_days,
    all_hours,
    all_vehicles,
    all_minutes,
    all_duration,
):
    for day in all_days:
        for hour in all_hours:
            for minute in all_minutes:
                for vehicle in all_vehicles:
                    for duration in all_duration:
                        if market_hours[(day, hour, minute)] == 0:  # Closed
                            model.Add(
                                shifts_state[
                                    (
                                        day,
                                        hour,
                                        minute,
                                        vehicle,
                                        duration,
                                    )
                                ]
                                == 0
                            )
