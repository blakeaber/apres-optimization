def fixed_shifts(
    model,
    shifts_state,
    fixed_shifts_input,
):
    for element in fixed_shifts_input:
        day, hour, minute, vehicle, duration = element
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
            == 1
        )
