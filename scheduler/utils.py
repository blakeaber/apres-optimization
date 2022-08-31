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
                "shift_id: -",
                "The number of provided vehicles is bigger than the available vehicles.",
            )
        )

    if not df["shift_id"].is_unique:
        invalid_shifts.append(
            (
                "shift_id: -",
                "The column `shift_id` must have a unique value per shift.",
            )
        )

    for shift_id, group in df.groupby("shift_id"):
        shift_start = (
            (group["sday"] * 60 * 24) + (group["shour"] * 60) + group["sminute"]
        )
        shift_end = (group["eday"] * 60 * 24) + (group["ehour"] * 60) + group["eminute"]
        shift_length = shift_end - shift_start

        if not shift_length.between(min_duration, max_duration).all():
            invalid_shifts.append(
                (
                    f"shift_id: {shift_id}",
                    "Shift duration is out of min/max provided bounds.",
                )
            )

    return invalid_shifts

    shifts_num_vehicles = df["vehicle"].nunique()
    if shifts_num_vehicles > num_vehicles:
        invalid_shifts.append(
            (
                "shift_id: -",
                "The number of provided vehicles is bigger than the available vehicles.",
            )
        )


def expand_minutes_into_components(total_minutes):
    """Returns the days, hours, minutes contained inside the total minutes"""
    minutes_per_hour = 60
    minutes_per_day = minutes_per_hour * 24

    days = total_minutes // minutes_per_day
    hours = int(total_minutes / minutes_per_hour % 24)
    minutes = total_minutes % minutes_per_hour

    return days, hours, minutes

    return invalid_shifts


def expand_minutes_into_components(total_minutes):
    """Returns the days, hours, minutes contained inside the total minutes"""
    minutes_per_hour = 60
    minutes_per_day = minutes_per_hour * 24

    days = total_minutes // minutes_per_day
    hours = int(total_minutes / minutes_per_hour % 24)
    minutes = total_minutes % minutes_per_hour

    return days, hours, minutes
