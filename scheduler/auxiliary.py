import utils

def define_shift_state(model, all_days, all_hours, all_minutes, all_vehicles, all_duration):
    """Define the state of all shifts"""
    shifts_state = {}
    for day in all_days:
        for s_hour in all_hours:
            for s_minute in all_minutes:
                for vehicle in all_vehicles:
                    for duration in all_duration:
                        shifts_state[
                            (
                                day,
                                s_hour,
                                s_minute,
                                vehicle,
                                duration,
                            )
                        ] = model.NewBoolVar(
                            "shift_day_%i_sH_%i_sM_%i_vehicle_%i_duration_%d"
                            % (
                                day,
                                s_hour,
                                s_minute,
                                vehicle,
                                duration,
                            )
                        )
    return shifts_state


def define_assigned_shifts(model, all_vehicles, all_duration):
    """Auxiliary variable to track if a shift was assigned"""
    return {
        (vehicle, duration): model.NewBoolVar(
            f"selected_shift_driv{vehicle}_d{duration}"
        )
        for vehicle in all_vehicles
        for duration in all_duration
    }


def define_shifts_start(model, all_days, all_hours, all_minutes, all_vehicles):
    """Auxiliary variable to track when a shift starts"""
    return {
        (vehicle, day, hour, minute): model.NewBoolVar(
            f"shift_start_driv_{vehicle}_d{day}_h{hour}_m{minute}"
        )
        for vehicle in all_vehicles
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    }


def define_shifts_end(model, all_days, all_hours, all_minutes, all_vehicles):
    """Auxiliary variable to track when a shift ends"""
    return {
        (vehicle, day, hour, minute): model.NewBoolVar(
            f"shift_end_d{day}_h{hour}_m{minute}"
        )
        for vehicle in all_vehicles
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    }


def define_rush_hour(model, all_hours, all_minutes, rush_hour_input):
    """Auxiliary variable to track if we are in a rush hour"""
    rush_hour = {}
    for hour in all_hours:
        for minute in all_minutes:
            var = model.NewBoolVar(f"rush_hour_h{hour}")
            rush_hour[(hour, minute)] = var
            if rush_hour_input[(hour, minute)]:
                model.Add(var == 1)
    return rush_hour


def define_completion_rate(
    model, 
    all_days, 
    all_hours, 
    all_minutes,
    all_vehicles,
    all_duration, 
    num_vehicles,
    demand_input,
    shifts_state
    ):
    """Auxiliary variable to define completion_rate
    The completion rate is the min between demand and vehicles
    """
    completion_rate = {
        (day, hour, minute): model.NewIntVar(
            0, num_vehicles, f"completion_rate_d{day}_h{hour}_m{minute}"
        )
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    }
    for day in all_days:
        for hour in all_hours:
            for minute in all_minutes:
                model.AddMinEquality(
                    completion_rate[(day, hour, minute)],
                    [
                        demand_input[(day, hour, minute)],
                        utils.get_vehicles_in_time(
                            shifts_state, day, hour, minute, all_vehicles, all_duration
                        ),
                    ],
                )
    return completion_rate
