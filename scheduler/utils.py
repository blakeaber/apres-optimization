import time
import pandas as pd
from ortools.sat.python import cp_model


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    # Class to print all solutions found
    def __init__(self, shifts_state):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__shifts_state = shifts_state
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

        print()


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
