from typing import Union, List
from pydantic import BaseModel


class StaticVariables(BaseModel):
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
    columns: List[str]
    index: List[int]
    data: List[List[int]]


class DynamicVariables(BaseModel):
    demand_forecast: VectorDataFrame
    minimum_shifts: Union[VectorDataFrame, None] = None
    rush_hours: Union[VectorDataFrame, None] = None
    market_hours: Union[VectorDataFrame, None] = None


class OptimizerInput(BaseModel):
    run_id: str = "99999999-9999-9999-9999-999999999999"
    num_search_workers: int = 4
    static_variables: StaticVariables
    dynamic_variables: DynamicVariables


class HeartbeatStatus(BaseModel):
    version: float = 1.0
    stage: str = "No Stage Set"
    step: int = 0
    score: int = 0
    payload: OptimizerInput = None
    solution: VectorDataFrame = None
    schedule: VectorDataFrame = None
