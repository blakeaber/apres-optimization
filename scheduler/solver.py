import time
import pandas as pd
from ortools.sat.python import cp_model

from .auxiliary import get_vehicles_in_time, get_vehicles_in_time_from_solver
from .utils import expand_minutes_into_components


def get_solution_from_states_df(df: pd.DataFrame, heartbeat):
    df = df.sort_values(["day", "hour", "minute"]).reset_index(drop=True)
    df["time"] = (
        df["day"].astype(str)
        + "-"
        + df["hour"].astype(str)
        + "-"
        + df["minute"].astype(str)
    )
    # Compute aggregations over time
    df = df.groupby("time")[["vehicle", "start", "end"]].agg(
        {"vehicle": "size", "start": "sum", "end": "sum"}
    )
    df.columns = ["vehicles", "starts", "ends"]
    df = df.reset_index()

    demand = pd.read_json(
        heartbeat.payload.dynamic_variables.demand_forecast.json(), orient="split"
    )
    demand["time"] = (
        demand["day"].astype(str)
        + "-"
        + demand["hour"].astype(str)
        + "-"
        + demand["minute"].astype(str)
    )

    if heartbeat.payload.dynamic_variables.minimum_shifts:
        min_shifts = pd.read_json(
            heartbeat.payload.dynamic_variables.minimum_shifts.json(), orient="split"
        )
        min_shifts["time"] = (
            min_shifts["day"].astype(str)
            + "-"
            + min_shifts["hour"].astype(str)
            + "-"
            + min_shifts["minute"].astype(str)
        )
        min_shifts = min_shifts.drop(columns=["day", "hour", "minute"])

    return (
        df.merge(demand, on="time")
        .merge(min_shifts, on="time")
        .sort_values(["day", "hour", "minute"])
        .reset_index(drop=True)
    )


def get_schedule_from_states_df(df):
    df = df.sort_values(["vehicle", "day", "hour", "minute"]).reset_index(drop=True)
    # Need to add 1 to the days to make them a valid datetime.
    # We want this to correctly plot a Gantt chart
    df["day"] = df["day"] + 1

    df["time"] = pd.to_datetime(
        df["day"].astype(str)
        + "-"
        + df["hour"].astype(str)
        + "-"
        + df["minute"].astype(str),
        format="%d-%H-%M",
    )

    # We are only interested in rows with a start or an end
    df = df[(df["start"] == 1) | (df["end"] == 1)]

    # Gantt chart: vehicle start times and duration (based on optimal schedules)
    # We have start-end in row pairs, so traverse the DF in pairs and set the start/end
    gantt = []
    for i in range(0, len(df), 2):
        start_row = df.iloc[i]
        end_row = df.iloc[i + 1]
        gantt.append([start_row["vehicle"], start_row["time"], end_row["time"]])
    schedule_df = pd.DataFrame(gantt, columns=["vehicle", "start_time", "end_time"])

    return schedule_df.to_dict(orient="split")


def define_maximization_function(
    shifts_state,
    completion_rate,
    revenue_passenger,
    cost_vehicle_per_minute,
    rush_hour_input,
    vehicles_to_min_shifts,
    all_vehicles,
    shifts_end,
    all_minutes,
    rush_hour_soft_constraint_cost,
    minimum_shifts_soft_constraint_cost,
):
    """Returns an OrTools maximization function"""

    def _define_rush_hour_soft_constraint(minute):
        day, hour, r_minutes = expand_minutes_into_components(minute)

        return (
            cp_model.LinearExpr.Sum(
                [
                    shifts_end[
                        (
                            driver,
                            minute,
                        )
                    ]
                    for driver in all_vehicles
                ]
            )
            * rush_hour_input[(hour, r_minutes)]
            * rush_hour_soft_constraint_cost
        )

    def _define_minimum_shifts_soft_constraint(minute):
        return vehicles_to_min_shifts[(minute)] * minimum_shifts_soft_constraint_cost

    return cp_model.LinearExpr.Sum(
        [
            (
                completion_rate[minute] * revenue_passenger
                - get_vehicles_in_time(shifts_state, minute, all_vehicles)
                * cost_vehicle_per_minute
            )
            - _define_rush_hour_soft_constraint(minute)
            - _define_minimum_shifts_soft_constraint(minute)
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
    vehicles_to_min_shifts,
    all_vehicles,
    shifts_end,
    all_minutes,
    rush_hour_soft_constraint_cost,
    minimum_shifts_soft_constraint_cost,
):
    """Computes and returns the final value of the maximization function.

    A tuple is returned, the first one represents the real revenue from operations,
    the second represents the cost added by unmet soft constraints.

    It uses the provided CpSolverSolutionCallback to get the assigned real values.
    """
    real_part = sum(
        (
            solver.Value(completion_rate[minute]) * revenue_passenger
            - (
                get_vehicles_in_time_from_solver(
                    solver, shifts_state, minute, all_vehicles
                )
                * cost_vehicle_per_minute
            )
        )
        for minute in all_minutes
    )

    def _define_rush_hours_soft(minute):
        day, hour, r_minutes = expand_minutes_into_components(minute)

        return (
            sum(solver.Value(shifts_end[driver, minute]) for driver in all_vehicles)
            * rush_hour_input[hour, r_minutes]
            * rush_hour_soft_constraint_cost
        )

    def _define_minimum_shifts_soft(minute):
        return (
            solver.Value(vehicles_to_min_shifts[(minute)])
            * minimum_shifts_soft_constraint_cost
        )

    soft_constraints = sum(
        _define_rush_hours_soft(minute) + _define_minimum_shifts_soft(minute)
        for minute in all_minutes
    )

    return real_part, soft_constraints


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    # Class to print all solutions found
    def __init__(
        self,
        heartbeat,
        shifts_state,
        completion_rate,
        revenue_passenger,
        cost_vehicle_per_minute,
        rush_hour_input,
        vehicles_to_min_shifts,
        all_vehicles,
        all_duration,
        shifts_start,
        shifts_end,
        all_minutes,
        rush_hour_soft_constraint_cost,
        minimum_shifts_soft_constraint_cost,
        sum_of_starts,
        sum_of_ends,
        sum_equals,
        multiprocess_pipe,
    ):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__heartbeat = heartbeat
        self.__shifts_state = shifts_state
        self.__completion_rate = completion_rate
        self.__revenue_passenger = revenue_passenger
        self.__cost_vehicle_per_minute = cost_vehicle_per_minute
        self.__rush_hour_input = rush_hour_input
        self.__vehicles_to_min_shifts = vehicles_to_min_shifts
        self.__all_vehicles = all_vehicles
        self.__all_duration = all_duration
        self.__shifts_start = shifts_start
        self.__shifts_end = shifts_end
        self.__all_minutes = all_minutes
        self.__rush_hour_soft_constraint_cost = rush_hour_soft_constraint_cost
        self.__minimum_shifts_soft_constraint_cost = minimum_shifts_soft_constraint_cost
        self.__solution_count = 0
        self.__start_time = time.time()
        self.__best_solution = -1e6
        self.__multiprocess_pipe = multiprocess_pipe
        self.__sum_of_starts = sum_of_starts
        self.__sum_of_ends = sum_of_ends
        self.__sum_equal = sum_equals

    def on_solution_callback(self):
        self.__solution_count += 1
        current_score = int(self.ObjectiveValue())

        if current_score > self.__best_solution:
            current_time = round(time.time() - self.__start_time, 2)
            score_real, score_constraints = compute_maximization_function_components(
                self,
                self.__shifts_state,
                self.__completion_rate,
                self.__revenue_passenger,
                self.__cost_vehicle_per_minute,
                self.__rush_hour_input,
                self.__vehicles_to_min_shifts,
                self.__all_vehicles,
                self.__shifts_end,
                self.__all_minutes,
                self.__rush_hour_soft_constraint_cost,
                self.__minimum_shifts_soft_constraint_cost,
            )
            print(
                f"Solution found: {self.__solution_count} - {current_score}$ ({score_real}$ from real -{score_constraints}$ from soft constraints) - {current_time} seconds"
            )

            # DEBUG
            # for i in self.__all_minutes:
            #     print(
            #         i,
            #         f"({self.Value(self.__shifts_state[(i, 0)])})",
            #         self.Value(self.__shifts_start[(0, i)]),
            #         self.Value(self.__shifts_end[(0, i)]),
            #         f"ss {self.Value(self.__sum_of_starts[(0, i)])}",
            #         f"se {self.Value(self.__sum_of_ends[(0, i)])}",
            #         f"eq {self.Value(self.__sum_equal[(0, i)])}",
            #         "----------",
            #         f"({self.Value(self.__shifts_state[(i, 1)])})",
            #         self.Value(self.__shifts_start[(1, i)]),
            #         self.Value(self.__shifts_end[(1, i)]),
            #         f"ss {self.Value(self.__sum_of_starts[(1, i)])}",
            #         f"se {self.Value(self.__sum_of_ends[(1, i)])}",
            #         f"eq {self.Value(self.__sum_equal[(1, i)])}",
            #     )

            shifts_state_values = []
            for k, v in self.__shifts_state.items():
                if self.Value(v) == 1:
                    day, hour, r_minutes = expand_minutes_into_components(
                        k[0],
                    )

                    shifts_state_values.append(
                        [
                            day,
                            hour,
                            r_minutes,
                            k[1],
                            self.Value(self.__shifts_start[k[1], k[0]]),
                            self.Value(self.__shifts_end[k[1], k[0]]),
                        ]
                    )
            # Ward against empty solutions (which are possible if not constrainted)
            if not shifts_state_values:
                return
            df = pd.DataFrame(
                shifts_state_values,
                columns=[
                    "day",
                    "hour",
                    "minute",
                    "vehicle",
                    "start",
                    "end",
                ],
            )
            df.to_csv(
                f"./scheduler/solutions/best_solution_{self.__solution_count}.csv",
                index=False,
            )

            self.__heartbeat.solution = get_solution_from_states_df(
                df, self.__heartbeat
            ).to_dict(orient="split")
            self.__heartbeat.schedule = get_schedule_from_states_df(df)

            self.__heartbeat.total_score = current_score
            self.__heartbeat.score_real = score_real
            self.__heartbeat.score_constraints = -score_constraints
            self.__heartbeat.step = self.__solution_count

            # If we have a multiprocess pipe, send the heartbeat through it
            if self.__multiprocess_pipe:
                self.__multiprocess_pipe.send(self.__heartbeat)

            # Store the solution in front format for ease of debugging
            get_solution_from_states_df(df, self.__heartbeat).to_csv(
                "./scheduler/solutions/best_solution_front_format.csv", index=False
            )

        print()