
from fastapi import FastAPI
from objects import OptimizerInput, HeartbeatStatus
from scheduler.optimizer_v1_7 import compute_schedule

optimizer = FastAPI()

heartbeat = HeartbeatStatus
heartbeat.version = 1.7


@optimizer.get("/heartbeat/")
async def optimizer_heartbeat():
    return dict(
        run_id=heartbeat.payload.run_id, 
        version=heartbeat.version, 
        stage=heartbeat.stage, 
        step=heartbeat.step, 
        score=heartbeat.score
    )

@optimizer.post("/input/")
async def optimizer_input(payload: OptimizerInput):
    heartbeat.payload = payload.to_dict()
    compute_schedule(heartbeat)

@optimizer.get("/output/")
async def optimizer_output():
    return heartbeat.to_dict()
