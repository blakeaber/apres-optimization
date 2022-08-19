
from typing import Union, List
from pydantic import BaseModel

class StaticVariables(BaseModel):
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
    columns: List[str] = ["day","hour","minute","metric"]
    index: List[int] = [0,1,2,3,4]
    data: List[List[int]] = [[0,0,0,10],[0,0,15,10],[0,0,30,10],[0,0,45,10],[0,1,0,10]]

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

class HeartbeatStatus(object):
    version: float = 1.0
    stage: str = "No Stage Set"
    step: int = 0
    score: int = 0
    payload: OptimizerInput
    solution: VectorDataFrame
    schedule: VectorDataFrame

    def to_dict(self):
        return dict(
            version=self.version, 
            stage=self.stage, 
            step=self.step, 
            score=self.score,
            payload=self.payload.to_dict(),
            solution=self.solution.to_dict(),
            schedule=self.schedule.to_dict()
        )
