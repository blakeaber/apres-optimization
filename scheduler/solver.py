import time
import pandas as pd
from ortools.sat.python import cp_model

import utils


def define_maximization_function(
    shifts_state,
    completion_rate,
    revenue_passenger,
    cost_vehicle_per_minute,
    rush_hour_input,
    all_vehicles,
    all_duration,
    shifts_end,
    all_days,
    all_hours,
    all_minutes,
    rush_hour_soft_constraint_cost,
):
    """Returns an OrTools maximization function"""
    return cp_model.LinearExpr.Sum(
        [
            (
                completion_rate[(day, hour, minute)] * revenue_passenger
                - utils.get_vehicles_in_time(
                    shifts_state, day, hour, minute, all_vehicles, all_duration
                )
                * cost_vehicle_per_minute
            )
            - (
                cp_model.LinearExpr.Sum(
                    [
                        shifts_end[
                            (
                                driver,
                                day,
                                hour,
                                minute,
                            )
                        ]
                        for driver in all_vehicles
                    ]
                )
                * rush_hour_input[(hour, minute)]
                * rush_hour_soft_constraint_cost
            )
            for day in all_days
            for hour in all_hours
            for minute in all_minutes
        ]
    )


def compute_maximization_function_components(
    solver: cp_model.CpSolverSolutionCallback,
    shifts_state,
    completion_rate,
    revenue_passenger,
    cost_vehicle_per_minute,
    rush_hour_input,
    all_vehicles,
    all_duration,
    shifts_end,
    all_days,
    all_hours,
    all_minutes,
    rush_hour_soft_constraint_cost,
):
    """Computes and returns the final value of the maximization function.

    A tuple is returned, the first one represents the real revenue from operations,
    the second represents the cost added by unmet soft constraints.

    It uses the provided CpSolverSolutionCallback to get the assigned real values.
    """
    real_part = sum(
        (
            solver.Value(completion_rate[day, hour, minute]) * revenue_passenger
            - (
                utils.get_vehicles_in_time_from_solver(
                    solver, shifts_state, day, hour, minute, all_vehicles, all_duration
                )
                * cost_vehicle_per_minute
            )
        )
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    )

    soft_constraints = sum(
        sum(
            solver.Value(shifts_end[driver, day, hour, minute])
            for driver in all_vehicles
        )
        * rush_hour_input[hour, minute]
        * rush_hour_soft_constraint_cost
        for day in all_days
        for hour in all_hours
        for minute in all_minutes
    )

    return real_part, soft_constraints


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    # Class to print all solutions found
    def __init__(
        self,
        shifts_state,
        completion_rate,
        revenue_passenger,
        cost_vehicle_per_minute,
        rush_hour_input,
        all_vehicles,
        all_duration,
        shifts_end,
        all_days,
        all_hours,
        all_minutes,
        rush_hour_soft_constraint_cost,
    ):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__shifts_state = shifts_state
        self.__completion_rate = completion_rate
        self.__revenue_passenger = revenue_passenger
        self.__cost_vehicle_per_minute = cost_vehicle_per_minute
        self.__rush_hour_input = rush_hour_input
        self.__all_vehicles = all_vehicles
        self.__all_duration = all_duration
        self.__shifts_end = shifts_end
        self.__all_days = all_days
        self.__all_hours = all_hours
        self.__all_minutes = all_minutes
        self.__rush_hour_soft_constraint_cost = rush_hour_soft_constraint_cost
        self.__solution_count = 0
        self.__start_time = time.time()
        self._best_solution = 0

    def on_solution_callback(self):
        self.__solution_count += 1
        current_score = int(self.ObjectiveValue())

        if current_score > self._best_solution:
            current_time = round(time.time() - self.__start_time, 2)
            real, constraints = compute_maximization_function_components(
                self,
                self.__shifts_state,
                self.__completion_rate,
                self.__revenue_passenger,
                self.__cost_vehicle_per_minute,
                self.__rush_hour_input,
                self.__all_vehicles,
                self.__all_duration,
                self.__shifts_end,
                self.__all_days,
                self.__all_hours,
                self.__all_minutes,
                self.__rush_hour_soft_constraint_cost,
            )
            print(
                f"Solution found: {self.__solution_count} - {current_score}$ ({real}$ from real -{constraints}$ from soft constraints) - {current_time} seconds"
            )

            shifts_state_values = []
            for k, v in self.__shifts_state.items():
                if self.Value(v) == 1:
                    shifts_state_values.append(
                        [k[0], k[1], k[2], k[3], k[4], current_score]
                    )
            df = pd.DataFrame(
                shifts_state_values,
                columns=["day", "hour", "minute", "vehicle", "duration", "score"],
            )
            df.to_csv(
                f"./solutions/best_solution_{self.__solution_count}.csv", index=False
            )

        print()
