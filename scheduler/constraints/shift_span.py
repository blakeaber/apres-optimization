from ortools.sat.python import cp_model


def shift_span(
    model: cp_model.CpModel,
    shifts_start,
    shifts_end,
    shifts_state,
    all_minutes,
    all_vehicles,
    all_duration,
    total_minutes,
    duration_step,
    sum_of_starts,
    sum_of_ends,
    sum_equals,
):
    for vehicle in all_vehicles:
        # There must be the same number of starts & ends
        model.Add(
            cp_model.LinearExpr.Sum(
                [shifts_start[(vehicle, minute)] for minute in all_minutes]
            )
            == cp_model.LinearExpr.Sum(
                [shifts_end[(vehicle, minute)] for minute in all_minutes]
            ),
        )

        # Auxiliary variable to keep track of the intervals
        for minute in all_minutes:
            end_durations_states = [
                shifts_end[(vehicle, minute + duration)]
                for duration in all_duration
                if minute + duration < total_minutes
            ]

            # If shift_start then the shift_end must finish in a good duration
            model.AddAtLeastOne(end_durations_states).OnlyEnforceIf(
                shifts_start[(vehicle, minute)]
            )

            # Only one shift start in-between
            for duration in all_duration:
                if minute + duration >= total_minutes:
                    continue

                internal_starts = []
                internal_ends = []
                for internal_duration in range(
                    0 + duration_step, duration, duration_step
                ):
                    internal_starts.append(
                        shifts_start[(vehicle, minute + internal_duration)]
                    )
                    internal_ends.append(
                        shifts_end[(vehicle, minute + internal_duration)]
                    )
                model.Add(cp_model.LinearExpr.Sum(internal_starts) == 0).OnlyEnforceIf(
                    [
                        shifts_start[(vehicle, minute)],
                        shifts_end[(vehicle, minute + duration)],
                    ]
                )
                model.Add(cp_model.LinearExpr.Sum(internal_ends) == 0).OnlyEnforceIf(
                    [
                        shifts_start[(vehicle, minute)],
                        shifts_end[(vehicle, minute + duration)],
                    ]
                )

                # The states between start-end must be 1, 0 otherwhise. Include bouth boundaries
                for range_minute in range(
                    minute, minute + duration + duration_step, duration_step
                ):
                    model.Add(shifts_state[range_minute, vehicle] == 1).OnlyEnforceIf(
                        [
                            shifts_start[(vehicle, minute)],
                            shifts_end[(vehicle, minute + duration)],
                        ]
                    )

            # Compute the cumulative sum
            if minute != all_minutes[0]:
                model.Add(
                    sum_of_starts[(vehicle, minute)]
                    == (
                        cp_model.LinearExpr.Sum(
                            [
                                shifts_start[(vehicle, in_minute)]
                                for in_minute in range(
                                    all_minutes[0], minute, all_minutes.step
                                )
                            ]
                        )
                        + shifts_start[(vehicle, minute)]
                    )
                )
                model.Add(
                    sum_of_ends[(vehicle, minute)]
                    == (
                        cp_model.LinearExpr.Sum(
                            [
                                shifts_end[(vehicle, in_minute)]
                                for in_minute in range(
                                    all_minutes[0], minute, all_minutes.step
                                )
                            ]
                        )
                        + shifts_end[(vehicle, minute)]
                    )
                )
            else:
                model.Add(
                    sum_of_starts[(vehicle, minute)] == shifts_start[(vehicle, minute)]
                )
                model.Add(
                    sum_of_ends[(vehicle, minute)] == shifts_end[(vehicle, minute)]
                )

            # For no shift when the sum is equal & not in an end
            model.Add(
                sum_of_starts[(vehicle, minute)] == sum_of_ends[(vehicle, minute)]
            ).OnlyEnforceIf(sum_equals[(vehicle, minute)])
            model.Add(
                sum_of_starts[(vehicle, minute)] != sum_of_ends[(vehicle, minute)]
            ).OnlyEnforceIf(sum_equals[(vehicle, minute)].Not())
            model.Add(shifts_state[range_minute, vehicle] == 0).OnlyEnforceIf(
                [
                    sum_equals[(vehicle, minute)],
                    shifts_end[(vehicle, minute)].Not(),
                ]
            )
