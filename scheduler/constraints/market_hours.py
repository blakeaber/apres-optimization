from scheduler.utils import expand_minutes_into_components


def market_hours(
    model,
    shifts_state,
    market_hours_input,
    all_vehicles,
    all_minutes,
):
    for minute in all_minutes:
        for vehicle in all_vehicles:
            day, hour, r_minute = expand_minutes_into_components(minute)
            if market_hours_input[(day, hour, r_minute)] == 0:  # Closed
                model.Add(
                    shifts_state[
                        (
                            minute,
                            vehicle,
                        )
                    ]
                    == 0
                )
