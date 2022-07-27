

def shift_span(
    model,
    shifts_state,
    shifts_start,
    shifts_end,
    all_days,
    all_hours,
    all_minutes,
    all_vehicles,
    all_duration,
    minutes_interval,
    num_days,
    num_hours,
    num_minutes,
):
    # TODO Make this function cleaner
    for vehicle in all_vehicles:
        for day in all_days:
            for duration in all_duration:
                # Just one start per day
                model.AddAtMostOne(
                    shifts_start[(vehicle, day, hour, minute)]
                    for hour in all_hours
                    for minute in all_minutes
                )
                # Just one end per day
                model.AddAtMostOne(
                    shifts_end[(vehicle, day, hour, minute)]
                    for hour in all_hours
                    for minute in all_minutes
                )
                for hour in all_hours:
                    for minute in all_minutes:
                        # Handle conditions to define start and end shifts
                        # Start: Previous 0 Current 1
                        # End: Current 1 Next 0
                        if (day == 0) and (hour == 0) and (minute == 0):
                            model.Add(
                                shifts_start[(vehicle, day, hour, minute)] == 1
                            ).OnlyEnforceIf(
                                shifts_state[
                                    (
                                        day,
                                        hour,
                                        minute,
                                        vehicle,
                                        duration,
                                    )
                                ],
                                shifts_state[
                                    (
                                        day,
                                        hour,
                                        minute + minutes_interval,
                                        vehicle,
                                        duration,
                                    )
                                ],
                            )
                        else:
                            if minute == 0:
                                model.Add(
                                    shifts_start[(vehicle, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            vehicle,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day if hour > 0 else day - 1,
                                            hour - 1 if hour > 0 else 23,
                                            num_minutes - minutes_interval,
                                            vehicle,
                                            duration,
                                        )
                                    ].Not(),
                                ),
                            else:
                                model.Add(
                                    shifts_start[(vehicle, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            vehicle,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute - minutes_interval,
                                            vehicle,
                                            duration,
                                        )
                                    ].Not(),
                                )
                        if (
                            (day == (num_days - 1))
                            and (hour == (num_hours - 1))
                            and (minute == (num_minutes - minutes_interval))
                        ):  # Last slot of the schedule
                            model.Add(
                                shifts_end[(vehicle, day, hour, minute)]
                                == shifts_state[
                                    (
                                        day,
                                        hour,
                                        minute,
                                        vehicle,
                                        duration,
                                    )
                                ]
                            )
                        else:
                            if minute == (60 - minutes_interval):
                                model.Add(
                                    shifts_end[(vehicle, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            vehicle,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day if hour < 23 else day + 1,
                                            hour + 1 if hour < 23 else 0,
                                            0,
                                            vehicle,
                                            duration,
                                        )
                                    ].Not(),
                                )
                            else:
                                model.Add(
                                    shifts_end[(vehicle, day, hour, minute)] == 1
                                ).OnlyEnforceIf(
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute,
                                            vehicle,
                                            duration,
                                        )
                                    ],
                                    shifts_state[
                                        (
                                            day,
                                            hour,
                                            minute + minutes_interval,
                                            vehicle,
                                            duration,
                                        )
                                    ].Not(),
                                )
