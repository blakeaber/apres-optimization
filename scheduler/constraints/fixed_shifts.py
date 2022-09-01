def fixed_shifts(
    model,
    shifts_start,
    shifts_end,
    fixed_shifts_input,
):
    """Based on the provided fixed shifts define active starts & ends"""
    for element in fixed_shifts_input:
        vehicle, sday, shour, sminute, eday, ehour, eminute = element
        # Convert to minutes
        start_date = (sday * 60 * 24) + (shour * 60) + sminute
        end_date = (eday * 60 * 24) + (ehour * 60) + eminute

        model.Add(shifts_start[(vehicle, start_date)] == 1)
        model.Add(shifts_end[(vehicle, end_date)] == 1)
