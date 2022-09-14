import multiprocessing

from fastapi import FastAPI, BackgroundTasks, HTTPException

from .objects import OptimizerInput, HeartbeatStatus
from scheduler.optimizer_v1_8 import compute_schedule

optimizer = FastAPI(
    title="Alto Scheduler API",
    description="This API allows to trigger the Alto vehicle scheduler and fetch it's output.",
    version="1.8",
    contact={
        "name": "Matt Waite",
        "email": "matt@apres.io",
    },
)

# Define the global Heartbeat that will be updated by the endpoints & scheduler
heartbeat = HeartbeatStatus()
heartbeat.version = 1.8

# Keep track of the current running scheduler process
_current_scheduler_process = None


def _update_heartbeat_from_pipe(multiprocess_pipe):
    """Auxiliary function that will run in a thread. Updates the heartbeat object
    with a new one comming from the process pipe"""
    try:
        global heartbeat
        while True:
            # Read from the pipe until it is cancelled or the process is terminated
            data = multiprocess_pipe.recv()
            if data and isinstance(data, HeartbeatStatus):
                heartbeat = data
            else:
                break
    except Exception as e:
        if heartbeat.stage_id != -1:
            heartbeat.set_error("The scheduler process was terminated.")
        heartbeat.set_end_time()
    finally:
        multiprocess_pipe.close()


def _scheduler_wrapper(heartbeat, multiprocess_pipe):
    """Wrapper function that will run in its own process.
    It executes the scheduler and watches for errors"""
    try:
        compute_schedule(heartbeat, multiprocess_pipe)
    except Exception as e:
        heartbeat.set_error(str(e))
        multiprocess_pipe.send(heartbeat)
    finally:
        multiprocess_pipe.close()


@optimizer.get("/heartbeat/")
def optimizer_heartbeat():
    """Returns the current status of the scheduler.
    Use it to know when the scheduler is running or has found a solution."""
    return dict(
        run_id=heartbeat.payload.run_id
        if heartbeat.payload and hasattr(heartbeat, "payload")
        else None,
        version=heartbeat.version,
        stage_id=heartbeat.stage_id,
        stage=heartbeat.stage,
        step=heartbeat.step,
        total_score=heartbeat.total_score,
        real_score=heartbeat.score_real,
        constraint_score=heartbeat.score_constraints,
    )


@optimizer.post("/input/")
def optimizer_input(payload: OptimizerInput, background_tasks: BackgroundTasks):
    """Given a valid input payload triggers a scheduler execution."""
    # Check that we are in a valid stage to start the scheduler
    global _current_scheduler_process
    if _current_scheduler_process and _current_scheduler_process.is_alive():
        raise HTTPException(
            status_code=404,
            detail="Cannot start a scheduler run while a previous run is still running. Check `/heartbeat/`",
        )
    _current_scheduler_process = (
        None  # Set it to None in case it finished gracefully and it is not alive
    )

    # Prepare the heartbeat for a new run
    heartbeat.payload = payload
    heartbeat.reset()

    # Initialize pipe for multiprocess
    read_pipe, write_pripe = multiprocessing.Pipe()
    # Create a new process for the scheduler
    _current_scheduler_process = multiprocessing.Process(
        target=_scheduler_wrapper, args=(heartbeat, write_pripe)
    )
    _current_scheduler_process.start()

    # Create a thread to read from the process pipe
    background_tasks.add_task(_update_heartbeat_from_pipe, read_pipe)

    return {
        f"Scheduler started with run_id: {heartbeat.payload.run_id} and process_id: {_current_scheduler_process.pid}."
    }


@optimizer.get("/output/")
def optimizer_output():
    """Returns the heartbeat information (like `/heartbeat/`) but includes the output
    of the last best step inside the fields `solution` and `schedule`"""
    return heartbeat.dict()


@optimizer.get("/cancel/{run_id}")
def cancel_scheduler(run_id: str):
    """If a scheduler run exists it terminates the process"""

    # Sanity check to prevent unwanted cancels
    if heartbeat.payload and heartbeat.payload.run_id != run_id:
        raise HTTPException(
            status_code=404,
            detail="The current heartbeat `run_id` is different from the one provided. Not cancelling it.",
        )

    global _current_scheduler_process
    if _current_scheduler_process is None:
        raise HTTPException(
            status_code=404,
            detail="No running scheduler execution detected.",
        )

    print("Trying to terminate the process")
    # Inside a while loop to flag it multiple times and prevent "confirmation" request
    while _current_scheduler_process.is_alive():
        _current_scheduler_process.kill()
    _current_scheduler_process = None

    return {"Scheduler execution terminated."}


@optimizer.get("/")
def health_check():
    return {"API deployed and running."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(optimizer, host="0.0.0.0", port="8000")
