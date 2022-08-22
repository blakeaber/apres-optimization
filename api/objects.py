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


class OptimizerInput(BaseModel):
    """Object that holds all the inputs required by the scheduler to run and the run UUID"""

    run_id: str = "99999999-9999-9999-9999-999999999999"
    num_search_workers: int = 4
    static_variables: StaticVariables
    dynamic_variables: DynamicVariables


class HeartbeatStatus(BaseModel):
    """Main object to keep track of scheduler executions."""

    version: float = 1.0
    stage: str = "No Stage Set"
    step: int = 0
    score: int = 0
    payload: OptimizerInput = None
    solution: VectorDataFrame = None
    schedule: VectorDataFrame = None

    def reset(self):
        """Resets the output fields `stage, step, score, solution & scheduler`"""
        self.stage = "No Stage Set"
        self.step = 0
        self.score = 0
        self.solution = None
        self.schedule = None
