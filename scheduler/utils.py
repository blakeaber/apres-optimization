"""Non OrTools related auxiliary functions"""
import time
from typing import List
import pandas as pd


def get_current_time():
    t = time.localtime()
    return time.strftime("%H:%M:%S", t)


def validate_fixed_shifts_input(
    df: pd.DataFrame,
    duration_step: int,
    min_duration: int,
    max_duration: int,
    num_vehicles: int,
) -> List[bool]:
    """Validates that the provided fixed shifts input contains well defined shifts"""
    invalid_shifts = []

    shifts_num_vehicles = df["vehicle"].nunique()
    if shifts_num_vehicles > num_vehicles:
        invalid_shifts.append(
            (
                "_",
                "The number of provided vehicles is bigger than the available vehicles.",
            )
        )

    for shift_id, group in df.groupby("shift_id"):
        shift_length = group["duration"]
        num_slots_worked = len(group)

        if shift_length.nunique() != 1:
            invalid_shifts.append(
                (shift_id, "Shift duration must be constant per shift.")
            )

        if not shift_length.between(min_duration, max_duration).all():
            invalid_shifts.append(
                (shift_id, "Shift duration is out of min/max provided bounds.")
            )

        shift_length = shift_length.iloc[0]
        if num_slots_worked * duration_step != shift_length:
            invalid_shifts.append(
                (
                    shift_id,
                    "Shift duration is spands more/less than the provided number of observations.",
                )
            )

    return invalid_shifts


def expand_minutes_into_components(total_minutes, num_hours, num_minutes):
    """Returns the days, hours, minutes contained inside the total minutes"""
    minutes_per_hour = num_minutes
    minutes_per_day = minutes_per_hour * num_hours

    days = total_minutes // minutes_per_day
    hours = int(total_minutes / minutes_per_hour % num_hours)
    minutes = total_minutes % minutes_per_hour

    return days, hours, minutes
