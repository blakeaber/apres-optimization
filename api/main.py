from fastapi import FastAPI
from .objects import OptimizerInput, HeartbeatStatus
from scheduler.optimizer_v1_7 import compute_schedule

optimizer = FastAPI(debug=True)

heartbeat = HeartbeatStatus()
heartbeat.version = 1.7


@optimizer.get("/heartbeat/")
async def optimizer_heartbeat():
    return dict(
        run_id=heartbeat.payload.run_id
        if heartbeat.payload and hasattr(heartbeat, "payload")
        else None,
        version=heartbeat.version,
        stage=heartbeat.stage,
        step=heartbeat.step,
        score=heartbeat.score,
    )


@optimizer.post("/input/")
async def optimizer_input(payload: OptimizerInput):
    heartbeat.payload = payload
    compute_schedule(heartbeat)


@optimizer.get("/output/")
async def optimizer_output():
    return heartbeat.dict()


@optimizer.get("/")
def health_check():
    return {"API deployed and running."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(optimizer, host="0.0.0.0", port="8000")
