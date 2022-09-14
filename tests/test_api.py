import json

from fastapi.testclient import TestClient

from api.main import optimizer
from api.objects import HeartbeatStatus, OptimizerInput

client = TestClient(optimizer)


def test_read_root():
    """Tests that the healtcheck endpoint returns fine."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == ["API deployed and running."]


def test_heartbeat_not_init():
    """Tests the returned status of the heartbeat if no execution was ran"""
    response = client.get("/heartbeat/")
    assert response.status_code == 200
    assert response.json() == {
        "run_id": None,
        "version": 1.8,
        "stage_id": 0,
        "stage": "No Stage Set",
        "step": 0,
        "total_score": 0,
        "real_score": 0,
        "constraint_score": 0,
    }


def test_output_not_init(mocker):
    """Tests the returned status of the output if no execution was ran but input was provided"""
    with open("./api/payloads/input.json", "r") as f:
        json_input = json.load(f)
    mocker.patch("fastapi.BackgroundTasks.add_task", return_value=None)
    mocker.patch("multiprocessing.Process.start", return_value=None)
    response = client.post("/input/", json=json_input)

    response = client.get("/output/")
    assert response.status_code == 200
    data = response.json()
    # Remove large or time variables
    del data["start_time"]
    del data["end_time"]
    del data["payload"]["dynamic_variables"]
    assert data == {
        "version": 1.8,
        "stage_id": 0,
        "stage": "No Stage Set",
        "step": 0,
        "total_score": 0,
        "score_real": 0,
        "score_constraints": 0,
        "scores_over_time": [],
        "error_message": None,
        "payload": {
            "run_id": "2878898c-263f-4a32-9c14-ff15b60f91e3",
            "num_search_workers": 4,
            "static_variables": {
                "num_hours": 24,
                "num_vehicles": 77,
                "min_duration": 4,
                "max_duration": 10,
                "cost_vehicle_per_15min": 2,
                "revenue_passenger": 50,
                "max_starts_per_slot": 5,
                "max_ends_per_slot": 5,
                "enable_rush_hour_constraint": False,
                "enable_market_hour_constraint": True,
                "enable_min_shift_constraint": False,
                "rush_hour_soft_constraint_cost": 50,
                "minimum_shifts_soft_constraint_cost": 50,
                "min_time_between_shifts": 30,
            },
        },
        "solution": None,
        "schedule": None,
    }


def test_valid_input(mocker):
    """Tests that the scheduler is called when providing a valid input"""
    with open("./api/payloads/input.json", "r") as f:
        json_input = json.load(f)

    m = mocker.patch("fastapi.BackgroundTasks.add_task", return_value=None)
    n = mocker.patch("multiprocessing.Process.start", return_value=None)

    response = client.post("/input/", json=json_input)
    assert response.status_code == 200
    assert response.json() == [
        "Scheduler started with run_id: 2878898c-263f-4a32-9c14-ff15b60f91e3 and process_id: None."
    ]
    m.assert_called_once()
    n.assert_called_once()


def test_invalid_input(mocker):
    """Tests that the scheduler is not called when providing an invalid input"""
    m = mocker.patch("fastapi.BackgroundTasks.add_task", return_value=None)
    n = mocker.patch("multiprocessing.Process.start", return_value=None)

    response = client.post(
        "/input/",
        json={"unknown_field": 1, "run_id": "2878898c-263f-4a32-9c14-ff15b60f91e3"},
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "static_variables"],
                "msg": "field required",
                "type": "value_error.missing",
            },
            {
                "loc": ["body", "dynamic_variables"],
                "msg": "field required",
                "type": "value_error.missing",
            },
        ]
    }
    m.assert_not_called()
    n.assert_not_called()


def test_already_running_input(mocker):
    """Tests that the scheduler is not called when it is already running."""
    with open("./api/payloads/input.json", "r") as f:
        json_input = json.load(f)

    mocker.patch("api.main._current_scheduler_process", return_value=True)

    response = client.post("/input/", json=json_input)
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Cannot start a scheduler run while a previous run is still running. Check `/heartbeat/`"
    }


# def test_cancel_valid(mocker):
#     """Tests that the healtcheck endpoint returns fine."""

#     with open("./api/payloads/input.json", "r") as f:
#         json_input = json.load(f)

#     test_heartbeat = HeartbeatStatus()
#     test_heartbeat.version = 1.8
#     test_heartbeat.payload = OptimizerInput(**json_input)
#     mocker.patch("api.main.heartbeat", return_value=test_heartbeat)
#     mocker.patch("api.main.heartbeat.payload", return_value=test_heartbeat.payload)
#     mocker.patch(
#         "api.main.heartbeat.payload.run_id", return_value=test_heartbeat.payload.run_id
#     )
#     mocker.patch("api.main._current_scheduler_process", return_value=True)
#     mocker.patch("api.main._current_scheduler_process.is_alive", return_value=True)
#     mocker.patch("api.main._current_scheduler_process.kill", return_value=True)

#     response = client.get("/cancel/2878898c-263f-4a32-9c14-ff15b60f91e3")

#     assert response.status_code == 200
#     assert response.json() == ["Scheduler execution terminated."]
