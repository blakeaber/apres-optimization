from ortools.sat.python import cp_model


def shift_start_and_end_behaviour(
    model: cp_model.CpModel,
    shifts_start,
    shifts_end,
    shifts_state,
    all_minutes,
    all_vehicles,
    all_duration,
    total_minutes,
    duration_step,
    min_time_between_shifts,
    sum_of_starts,
    sum_of_ends,
    sum_equals,
):
    """This constraint specifies how shifts are build.
    A shift is bounded by a start and an end.
    Between these there can't be any other start & end.
    There must be a non-start time between an end and the next start.
    The time between a start and and end must correspond to a valid duration.
    shift_states must be 1 inside a bounded interval and 0 otherwise.
    For each start there must be one end."""
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

        for minute in all_minutes:
            # If shift_start then there must exist a shift_end and must finish within a valid duration
            model.AddAtLeastOne(
                [
                    shifts_end[(vehicle, minute + duration)]
                    for duration in all_duration
                    if minute + duration < total_minutes
                ]
            ).OnlyEnforceIf(shifts_start[(vehicle, minute)])

            for duration in all_duration:
                if minute + duration >= total_minutes:
                    continue

                # There can't be shift_starts or ends in-between
                internal_starts = [
                    shifts_start[(vehicle, minute + internal_duration)]
                    for internal_duration in range(
                        0 + duration_step, duration, duration_step
                    )
                ]
                model.Add(cp_model.LinearExpr.Sum(internal_starts) == 0).OnlyEnforceIf(
                    [
                        shifts_start[(vehicle, minute)],
                        shifts_end[(vehicle, minute + duration)],
                    ]
                )

                internal_ends = [
                    shifts_end[(vehicle, minute + internal_duration)]
                    for internal_duration in range(
                        0 + duration_step, duration, duration_step
                    )
                ]
                model.Add(cp_model.LinearExpr.Sum(internal_ends) == 0).OnlyEnforceIf(
                    [
                        shifts_start[(vehicle, minute)],
                        shifts_end[(vehicle, minute + duration)],
                    ]
                )

                # The shift states between start-end must be 1, 0 otherwhise. Include bouth boundaries
                for range_minute in range(
                    minute, minute + duration + duration_step, duration_step
                ):
                    model.Add(shifts_state[range_minute, vehicle] == 1).OnlyEnforceIf(
                        [
                            shifts_start[(vehicle, minute)],
                            shifts_end[(vehicle, minute + duration)],
                        ]
                    )

            # The 0 case is more complicated. We need to use cum_sums to know when we are
            # outside an interval
            # Compute the cumulative sum
            if minute != all_minutes[0]:
                model.Add(
                    sum_of_starts[(vehicle, minute)]
                    == (
                        sum_of_starts[(vehicle, minute - all_minutes.step)]
                        + shifts_start[(vehicle, minute)]
                    )
                )
                model.Add(
                    sum_of_ends[(vehicle, minute)]
                    == (
                        sum_of_ends[(vehicle, minute - all_minutes.step)]
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

            # Shifts set to 0 when the sum is equal & not in an end
            model.Add(
                sum_of_starts[(vehicle, minute)] == sum_of_ends[(vehicle, minute)]
            ).OnlyEnforceIf(sum_equals[(vehicle, minute)])
            model.Add(
                sum_of_starts[(vehicle, minute)] != sum_of_ends[(vehicle, minute)]
            ).OnlyEnforceIf(sum_equals[(vehicle, minute)].Not())
            model.Add(shifts_state[minute, vehicle] == 0).OnlyEnforceIf(
                [
                    sum_equals[(vehicle, minute)],
                    shifts_end[(vehicle, minute)].Not(),
                ]
            )

            # Specify minimum time to wait between shifts
            for internal_duration in range(0, min_time_between_shifts, duration_step):
                if minute + internal_duration >= total_minutes:
                    continue
                model.Add(
                    shifts_start[(vehicle, minute + internal_duration)] == 0
                ).OnlyEnforceIf(shifts_end[(vehicle, minute)])
