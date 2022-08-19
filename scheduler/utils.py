import time
import pandas as pd
from ortools.sat.python import cp_model


def get_solution_from_states_df(df, heartbeat):
    df = df.sort_values(["day", "hour", "minute"]).reset_index(drop=True)
    df["time"] = df.apply(
        lambda row: f"{row['day'].astype(int)}-{row['hour'].astype(int)}-{row['minute'].astype(int)}",
        axis=1,
    )

    starts = df.groupby("vehicle").first().groupby("time").size()
    ends = df.groupby("vehicle").last().groupby("time").size()
    df = df.groupby("time").size()

    df = pd.concat([df, starts, ends], axis=1).fillna(0)
    df.columns = ["vehicles", "starts", "ends"]
    df = df.astype(int).reset_index()

    demand = pd.read_json(heartbeat.payload.demand_forecast)
    demand["time"] = demand.apply(
        lambda row: f"{row['day'].astype(int)}-{row['hour'].astype(int)}-{row['minute'].astype(int)}",
        axis=1,
    )

    return (
        df.merge(demand, on="time")
        .sort_values(["day", "hour", "minute"])
        .reset_index(drop=True)
        .to_json(orient='split')
    )


def get_schedule_from_states_df(df):
    def get_start_time(df):
        """Based on the optimal schedule CSV, get the start times and duration (per vehicle)"""
        df = df.sort_values(["day", "hour", "minute"], ascending=True)
        return df.iloc[0][["day", "hour", "minute", "duration"]]

    df = df.sort_values(["day", "hour", "minute"]).reset_index(drop=True)
    df["time"] = df.apply(
        lambda row: f"{row['day'].astype(int)}-{row['hour'].astype(int)}-{row['minute'].astype(int)}",
        axis=1,
    )

    # Gantt chart: vehicle start times and duration (based on optimal schedules)
    schedule_df = (
        df.groupby("vehicle")
        .apply(get_start_time)
        .sort_values(["day", "hour", "minute"], ascending=True)
        .reset_index(drop=True)
    )
    schedule_df.index.name = "vehicle"
    schedule_df.reset_index(inplace=True)

    # Gantt chart: starting and ending timestamps
    schedule_df["start_time"] = pd.to_datetime(
        schedule_df.apply(
            lambda row: f"{row.hour.astype(int)}-{row.minute.astype(int)}", axis=1
        ),
        format="%H-%M",
    )
    schedule_df["end_time"] = schedule_df.apply(
        lambda row: row.start_time + pd.Timedelta(minutes=row.duration), axis=1
    )
    return schedule_df.to_json(orient='split')


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    # Class to print all solutions found
    def __init__(self, shifts_state, heartbeat):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__shifts_state = shifts_state
        self.__heartbeat = heartbeat
        self.__solution_count = 0
        self.__start_time = time.time()
        self._best_solution = 0
        

    def on_solution_callback(self):
        self.__solution_count += 1
        current_score = self.ObjectiveValue()

        if current_score > self._best_solution:
            current_time = round(time.time() - self.__start_time, 2)
            print(f'Solution found: {self.__solution_count} - {current_score} - {current_time}')

            shifts_state_values = []
            for k, v in self.__shifts_state.items():
                if self.Value(v) == 1:
                    shifts_state_values.append([k[0], k[1], k[2], k[3], k[4], current_score])

            df = pd.DataFrame(shifts_state_values, columns=["day", "hour", "minute", "vehicle", "duration", "score"])
            df.to_csv(f"./solutions/best_solution_{self.__solution_count}.csv", index=False)

            self.__heartbeat.solution = get_solution_from_states_df(df)
            self.__heartbeat.schedule = get_schedule_from_states_df(df)

            self.__heartbeat.score = current_score
            self.__heartbeat.step = self.__solution_count


def get_current_time():
    t = time.localtime()
    return time.strftime("%H:%M:%S", t)


def negated_bounded_span(shifts, start, length):
    """From: https://github.com/google/or-tools/blob/master/examples/python/shift_scheduling_sat.py#L29
    Filters an isolated sub-sequence of variables assigned to True.
    Extract the span of Boolean variables [start, start + length), negate them,
    and if there is variables to the left/right of this span, surround the span by
    them in non negated form.
    Args:
        shifts: a list of shifts to extract the span from.
        start: the start to the span.
        length: the length of the span.
    Returns:
        a list of variables which conjunction will be false if the sub-list is
        assigned to True, and correctly bounded by variables assigned to False,
        or by the start or end of works.
    """
    sequence = []
    # Left border (start of works, or works[start - 1])
    if start > 0:
        sequence.append(shifts[start - 1])
    sequence.extend(shifts[start + i].Not() for i in range(length))
    # Right border (end of works or works[start + length])
    if start + length < len(shifts):
        sequence.append(shifts[start + length])
    return sequence


def get_vehicles_in_time(shifts_state, day, hour, minute, all_vehicles, all_duration):
    """Return the number of vehicles for a given timestamp"""
    return cp_model.LinearExpr.Sum(
        [
            shifts_state[
                (
                    day,
                    hour,
                    minute,
                    vehicle,
                    duration,
                )
            ]
            for vehicle in all_vehicles
            for duration in all_duration
        ]
    )
