"""API objects for better input management & validation"""

from typing import Union, List
from pydantic import BaseModel


class StaticVariables(BaseModel):
    """Scheduler constant parameters"""

    num_days: int = 1
    num_hours: int = 24
    num_minutes: int = 60
    minutes_interval: int = 15
    duration_step: int = 15
    num_vehicles: int = 20
    min_duration: int = 4
    max_duration: int = 10
    cost_vehicle_per_15min: int = 2
    revenue_passenger: int = 50
    max_starts_per_slot: int = 5
    max_ends_per_slot: int = 5
    enable_rush_hour_constraint: bool = False
    enable_market_hour_constraint: bool = False
    enable_min_shift_constraint: bool = False
    rush_hour_soft_constraint_cost: int = 50
    minimum_shifts_soft_constraint_cost: int = 50


class VectorDataFrame(BaseModel):
    """Defines a vector object simulating a pandas DataFrame which can be
    transformed with pd.read_json(object_.json(), orient="split")"""

    columns: List[str]
    index: List[int]
    data: List[List[int]]


class DynamicVariables(BaseModel):
    """Collection of dynamic inputs over time"""

    demand_forecast: VectorDataFrame
    minimum_shifts: Union[VectorDataFrame, None] = None
    rush_hours: Union[VectorDataFrame, None] = None
    market_hours: Union[VectorDataFrame, None] = None
    fixed_shifts: Union[VectorDataFrame, None] = None


class OptimizerInput(BaseModel):
    """Object that holds all the inputs required by the scheduler to run and the run UUID"""

    run_id: str = "99999999-9999-9999-9999-999999999999"
    num_search_workers: int = 4
    static_variables: StaticVariables
    dynamic_variables: DynamicVariables


class HeartbeatStatus(BaseModel):
    """Main object to keep track of scheduler executions."""

    version: float = 1.0
    stage_id: int = 0
    stage: str = "No Stage Set"
    step: int = 0
    score: int = 0
    payload: OptimizerInput = None
    solution: VectorDataFrame = None
    schedule: VectorDataFrame = None

    def set_stage(self, id: int, final_stage_message: str = "Scheduler finished"):
        """Sets the stage given its ID. `final_stage_message` specifies a custom message
        for when the scheduler has finished"""
        if id == 0:
            self.stage_id = 0
            self.stage = "No Stage Set"
        elif id == 1:
            self.stage_id = 1
            self.stage = "Defining Auxiliary Variables"
        elif id == 2:
            self.stage_id = 2
            self.stage = "Defining Constraints"
        elif id == 3:
            self.stage_id = 3
            self.stage = "Constructing Optimization Problem"
        elif id == 4:
            self.stage_id = 4
            self.stage = "Finding Solutions"
        elif id == 5:
            self.stage_id = 5
            self.stage = final_stage_message

    def reset(self):
        """Resets the output fields `stage, step, score, solution & scheduler`"""
        self.set_stage(0)
        self.step = 0
        self.score = 0
        self.solution = None
        self.schedule = None
