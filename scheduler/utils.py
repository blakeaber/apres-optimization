import time
from ortools.sat.python import cp_model


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    # Class to print all solutions found
    def __init__(self, variables):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__solution_count = 0
        self.__start_time = time.time()
        self._best_solution = 0

    def on_solution_callback(self):
        self.__solution_count += 1

        if self.ObjectiveValue() > self._best_solution:
            print(
                "Solution found:",
                self.__solution_count,
                "-",
                self.ObjectiveValue(),
                "-",
                round(time.time() - self.__start_time, 2),
            )
            arr = []
            for k, v in self.__variables[0].items():
                if self.Value(v) == 1:
                    arr.append([k[0], k[1], k[2], k[3], k[4]])
            df = pd.DataFrame(
                arr, columns=["day", "hour", "minute", "vehicle", "duration"]
            )
            df.to_csv("best_solution.csv", index=False)
        print()


def _negated_bounded_span(shifts, start, length):
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


def _get_vehicles_in_time(shifts_state, day, hour, minute, all_vehicles, all_duration):
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
