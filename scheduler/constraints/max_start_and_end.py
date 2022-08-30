from ortools.sat.python import cp_model


def max_start_and_end(
    model,
    shifts_start,
    shifts_end,
    all_minutes,
    all_vehicles,
    max_starts_per_slot,
    max_ends_per_slot,
):
    # The sum of starts and ends per slot can't be higher than the max
    for minute in all_minutes:
        starts = cp_model.LinearExpr.Sum(
            [
                shifts_start[
                    (
                        vehicle,
                        minute,
                    )
                ]
                for vehicle in all_vehicles
            ]
        )
        ends = cp_model.LinearExpr.Sum(
            [
                shifts_end[
                    (
                        vehicle,
                        minute,
                    )
                ]
                for vehicle in all_vehicles
            ]
        )
        model.Add(starts <= max_starts_per_slot)
        model.Add(ends <= max_ends_per_slot)
