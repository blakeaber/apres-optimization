from fastapi import FastAPI, BackgroundTasks
from .objects import OptimizerInput, HeartbeatStatus
from scheduler.optimizer_v1_7 import compute_schedule

optimizer = FastAPI(
    title="Alto Scheduler API",
    description="This API allows to trigger the Alto vehicle scheduler and fetch it's output.",
    version="1.7",
    contact={
        "name": "Matt Waite",
        "email": "matt@apres.io",
    },
)

# Define the global Heartbeat that will be updated by the endpoints & scheduler
heartbeat = HeartbeatStatus()
heartbeat.version = 1.7


@optimizer.get("/heartbeat/")
def optimizer_heartbeat():
    """Returns the current status of the scheduler.
    Use it to know when the scheduler is running or has found a solution."""
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
def optimizer_input(payload: OptimizerInput, background_tasks: BackgroundTasks):
    """Given a valid input payload triggers a scheduler execution."""
    heartbeat.payload = payload
    heartbeat.reset()  # Reset the output fields for a new run
    background_tasks.add_task(
        compute_schedule, heartbeat
    )  # Let FastAPI run this in another thread, so it doesn't fully block the API
    return {f"Scheduler started with run_id: {heartbeat.payload.run_id}."}


@optimizer.get("/output/")
def optimizer_output():
    """Returns the heartbeat information (like `/heartbeat/`) but includes the output
    of the last best step inside the fields `solution` and `schedule`"""
    return heartbeat.dict()


@optimizer.get("/")
def health_check():
    return {"API deployed and running."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(optimizer, host="0.0.0.0", port="8000")
