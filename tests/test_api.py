import json

from fastapi.testclient import TestClient

from api.main import optimizer
from api.objects import HeartbeatStatus, OptimizerInput
from scheduler.optimizer_v1_7 import compute_schedule

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
        "version": 1.7,
        "stage": "No Stage Set",
        "step": 0,
        "score": 0,
    }


def test_output_not_init(mocker):
    """Tests the returned status of the output if no execution was ran but input was provided"""
    with open("./api/payloads/input.json", "r") as f:
        json_input = json.load(f)
    mocker.patch("fastapi.BackgroundTasks.add_task", return_value=None)
    response = client.post("/input/", json=json_input)

    response = client.get("/output/")
    assert response.status_code == 200
    assert response.json() == {
        "version": 1.7,
        "stage": "No Stage Set",
        "step": 0,
        "score": 0,
        "payload": {
            "run_id": "2878898c-263f-4a32-9c14-ff15b60f91e3",
            "num_search_workers": 4,
            "static_variables": {
                "num_days": 1,
                "num_hours": 24,
                "num_minutes": 60,
                "minutes_interval": 15,
                "duration_step": 15,
                "num_vehicles": 2,
                "min_duration": 4,
                "max_duration": 10,
                "cost_vehicle_per_15min": 2,
                "revenue_passenger": 50,
                "max_starts_per_slot": 8,
                "max_ends_per_slot": 8,
                "enable_rush_hour_constraint": False,
                "enable_market_hour_constraint": True,
                "enable_min_shift_constraint": False,
            },
            "dynamic_variables": {
                "demand_forecast": {
                    "columns": ["day", "hour", "minute", "demand"],
                    "index": [
                        0,
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                        18,
                        19,
                        20,
                        21,
                        22,
                        23,
                        24,
                        25,
                        26,
                        27,
                        28,
                        29,
                        30,
                        31,
                        32,
                        33,
                        34,
                        35,
                        36,
                        37,
                        38,
                        39,
                        40,
                        41,
                        42,
                        43,
                        44,
                        45,
                        46,
                        47,
                        48,
                        49,
                        50,
                        51,
                        52,
                        53,
                        54,
                        55,
                        56,
                        57,
                        58,
                        59,
                        60,
                        61,
                        62,
                        63,
                        64,
                        65,
                        66,
                        67,
                        68,
                        69,
                        70,
                        71,
                        72,
                        73,
                        74,
                        75,
                        76,
                        77,
                        78,
                        79,
                        80,
                        81,
                        82,
                        83,
                        84,
                        85,
                        86,
                        87,
                        88,
                        89,
                        90,
                        91,
                        92,
                        93,
                        94,
                        95,
                    ],
                    "data": [
                        [0, 0, 0, 10],
                        [0, 0, 15, 10],
                        [0, 0, 30, 10],
                        [0, 0, 45, 10],
                        [0, 1, 0, 10],
                        [0, 1, 15, 10],
                        [0, 1, 30, 10],
                        [0, 1, 45, 10],
                        [0, 2, 0, 13],
                        [0, 2, 15, 13],
                        [0, 2, 30, 13],
                        [0, 2, 45, 13],
                        [0, 3, 0, 14],
                        [0, 3, 15, 14],
                        [0, 3, 30, 14],
                        [0, 3, 45, 14],
                        [0, 4, 0, 11],
                        [0, 4, 15, 11],
                        [0, 4, 30, 11],
                        [0, 4, 45, 11],
                        [0, 5, 0, 4],
                        [0, 5, 15, 4],
                        [0, 5, 30, 4],
                        [0, 5, 45, 4],
                        [0, 6, 0, 6],
                        [0, 6, 15, 6],
                        [0, 6, 30, 6],
                        [0, 6, 45, 6],
                        [0, 7, 0, 9],
                        [0, 7, 15, 9],
                        [0, 7, 30, 9],
                        [0, 7, 45, 9],
                        [0, 8, 0, 6],
                        [0, 8, 15, 6],
                        [0, 8, 30, 6],
                        [0, 8, 45, 6],
                        [0, 9, 0, 3],
                        [0, 9, 15, 3],
                        [0, 9, 30, 3],
                        [0, 9, 45, 3],
                        [0, 10, 0, 2],
                        [0, 10, 15, 2],
                        [0, 10, 30, 2],
                        [0, 10, 45, 2],
                        [0, 11, 0, 1],
                        [0, 11, 15, 1],
                        [0, 11, 30, 1],
                        [0, 11, 45, 1],
                        [0, 12, 0, 0],
                        [0, 12, 15, 0],
                        [0, 12, 30, 0],
                        [0, 12, 45, 0],
                        [0, 13, 0, 4],
                        [0, 13, 15, 4],
                        [0, 13, 30, 4],
                        [0, 13, 45, 4],
                        [0, 14, 0, 4],
                        [0, 14, 15, 4],
                        [0, 14, 30, 4],
                        [0, 14, 45, 4],
                        [0, 15, 0, 6],
                        [0, 15, 15, 6],
                        [0, 15, 30, 6],
                        [0, 15, 45, 6],
                        [0, 16, 0, 8],
                        [0, 16, 15, 8],
                        [0, 16, 30, 8],
                        [0, 16, 45, 8],
                        [0, 17, 0, 8],
                        [0, 17, 15, 8],
                        [0, 17, 30, 8],
                        [0, 17, 45, 8],
                        [0, 18, 0, 6],
                        [0, 18, 15, 6],
                        [0, 18, 30, 6],
                        [0, 18, 45, 6],
                        [0, 19, 0, 11],
                        [0, 19, 15, 11],
                        [0, 19, 30, 11],
                        [0, 19, 45, 11],
                        [0, 20, 0, 8],
                        [0, 20, 15, 8],
                        [0, 20, 30, 8],
                        [0, 20, 45, 8],
                        [0, 21, 0, 12],
                        [0, 21, 15, 12],
                        [0, 21, 30, 12],
                        [0, 21, 45, 12],
                        [0, 22, 0, 14],
                        [0, 22, 15, 14],
                        [0, 22, 30, 14],
                        [0, 22, 45, 14],
                        [0, 23, 0, 10],
                        [0, 23, 15, 10],
                        [0, 23, 30, 10],
                        [0, 23, 45, 10],
                    ],
                },
                "minimum_shifts": {
                    "columns": ["day", "hour", "minute", "min_shifts"],
                    "index": [
                        0,
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                        18,
                        19,
                        20,
                        21,
                        22,
                        23,
                        24,
                        25,
                        26,
                        27,
                        28,
                        29,
                        30,
                        31,
                        32,
                        33,
                        34,
                        35,
                        36,
                        37,
                        38,
                        39,
                        40,
                        41,
                        42,
                        43,
                        44,
                        45,
                        46,
                        47,
                        48,
                        49,
                        50,
                        51,
                        52,
                        53,
                        54,
                        55,
                        56,
                        57,
                        58,
                        59,
                        60,
                        61,
                        62,
                        63,
                        64,
                        65,
                        66,
                        67,
                        68,
                        69,
                        70,
                        71,
                        72,
                        73,
                        74,
                        75,
                        76,
                        77,
                        78,
                        79,
                        80,
                        81,
                        82,
                        83,
                        84,
                        85,
                        86,
                        87,
                        88,
                        89,
                        90,
                        91,
                        92,
                        93,
                        94,
                        95,
                    ],
                    "data": [
                        [0, 0, 0, 0],
                        [0, 0, 15, 0],
                        [0, 0, 30, 0],
                        [0, 0, 45, 0],
                        [0, 1, 0, 0],
                        [0, 1, 15, 0],
                        [0, 1, 30, 0],
                        [0, 1, 45, 0],
                        [0, 2, 0, 0],
                        [0, 2, 15, 0],
                        [0, 2, 30, 0],
                        [0, 2, 45, 0],
                        [0, 3, 0, 0],
                        [0, 3, 15, 0],
                        [0, 3, 30, 0],
                        [0, 3, 45, 0],
                        [0, 4, 0, 0],
                        [0, 4, 15, 0],
                        [0, 4, 30, 5],
                        [0, 4, 45, 5],
                        [0, 5, 0, 5],
                        [0, 5, 15, 6],
                        [0, 5, 30, 6],
                        [0, 5, 45, 8],
                        [0, 6, 0, 0],
                        [0, 6, 15, 0],
                        [0, 6, 30, 0],
                        [0, 6, 45, 0],
                        [0, 7, 0, 0],
                        [0, 7, 15, 0],
                        [0, 7, 30, 0],
                        [0, 7, 45, 0],
                        [0, 8, 0, 0],
                        [0, 8, 15, 0],
                        [0, 8, 30, 0],
                        [0, 8, 45, 0],
                        [0, 9, 0, 0],
                        [0, 9, 15, 0],
                        [0, 9, 30, 0],
                        [0, 9, 45, 0],
                        [0, 10, 0, 0],
                        [0, 10, 15, 0],
                        [0, 10, 30, 0],
                        [0, 10, 45, 0],
                        [0, 11, 0, 0],
                        [0, 11, 15, 0],
                        [0, 11, 30, 0],
                        [0, 11, 45, 0],
                        [0, 12, 0, 11],
                        [0, 12, 15, 11],
                        [0, 12, 30, 11],
                        [0, 12, 45, 11],
                        [0, 13, 0, 11],
                        [0, 13, 15, 11],
                        [0, 13, 30, 11],
                        [0, 13, 45, 11],
                        [0, 14, 0, 11],
                        [0, 14, 15, 11],
                        [0, 14, 30, 11],
                        [0, 14, 45, 11],
                        [0, 15, 0, 0],
                        [0, 15, 15, 0],
                        [0, 15, 30, 0],
                        [0, 15, 45, 0],
                        [0, 16, 0, 0],
                        [0, 16, 15, 0],
                        [0, 16, 30, 0],
                        [0, 16, 45, 0],
                        [0, 17, 0, 0],
                        [0, 17, 15, 0],
                        [0, 17, 30, 0],
                        [0, 17, 45, 0],
                        [0, 18, 0, 0],
                        [0, 18, 15, 0],
                        [0, 18, 30, 0],
                        [0, 18, 45, 0],
                        [0, 19, 0, 0],
                        [0, 19, 15, 0],
                        [0, 19, 30, 0],
                        [0, 19, 45, 0],
                        [0, 20, 0, 5],
                        [0, 20, 15, 8],
                        [0, 20, 30, 8],
                        [0, 20, 45, 8],
                        [0, 21, 0, 8],
                        [0, 21, 15, 7],
                        [0, 21, 30, 7],
                        [0, 21, 45, 7],
                        [0, 22, 0, 0],
                        [0, 22, 15, 0],
                        [0, 22, 30, 0],
                        [0, 22, 45, 0],
                        [0, 23, 0, 0],
                        [0, 23, 15, 0],
                        [0, 23, 30, 0],
                        [0, 23, 45, 0],
                    ],
                },
                "rush_hours": {
                    "columns": ["hour", "minute", "rush_hour"],
                    "index": [
                        0,
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                        18,
                        19,
                        20,
                        21,
                        22,
                        23,
                        24,
                        25,
                        26,
                        27,
                        28,
                        29,
                        30,
                        31,
                        32,
                        33,
                        34,
                        35,
                        36,
                        37,
                        38,
                        39,
                        40,
                        41,
                        42,
                        43,
                        44,
                        45,
                        46,
                        47,
                        48,
                        49,
                        50,
                        51,
                        52,
                        53,
                        54,
                        55,
                        56,
                        57,
                        58,
                        59,
                        60,
                        61,
                        62,
                        63,
                        64,
                        65,
                        66,
                        67,
                        68,
                        69,
                        70,
                        71,
                        72,
                        73,
                        74,
                        75,
                        76,
                        77,
                        78,
                        79,
                        80,
                        81,
                        82,
                        83,
                        84,
                        85,
                        86,
                        87,
                        88,
                        89,
                        90,
                        91,
                        92,
                        93,
                        94,
                        95,
                    ],
                    "data": [
                        [0, 0, 0],
                        [0, 15, 0],
                        [0, 30, 0],
                        [0, 45, 0],
                        [1, 0, 0],
                        [1, 15, 0],
                        [1, 30, 0],
                        [1, 45, 0],
                        [2, 0, 0],
                        [2, 15, 0],
                        [2, 30, 0],
                        [2, 45, 0],
                        [3, 0, 0],
                        [3, 15, 0],
                        [3, 30, 0],
                        [3, 45, 0],
                        [4, 0, 0],
                        [4, 15, 0],
                        [4, 30, 0],
                        [4, 45, 0],
                        [5, 0, 0],
                        [5, 15, 0],
                        [5, 30, 0],
                        [5, 45, 0],
                        [6, 0, 1],
                        [6, 15, 1],
                        [6, 30, 1],
                        [6, 45, 1],
                        [7, 0, 1],
                        [7, 15, 1],
                        [7, 30, 1],
                        [7, 45, 1],
                        [8, 0, 1],
                        [8, 15, 1],
                        [8, 30, 1],
                        [8, 45, 1],
                        [9, 0, 1],
                        [9, 15, 1],
                        [9, 30, 1],
                        [9, 45, 1],
                        [10, 0, 0],
                        [10, 15, 0],
                        [10, 30, 0],
                        [10, 45, 0],
                        [11, 0, 0],
                        [11, 15, 0],
                        [11, 30, 0],
                        [11, 45, 0],
                        [12, 0, 0],
                        [12, 15, 0],
                        [12, 30, 0],
                        [12, 45, 0],
                        [13, 0, 0],
                        [13, 15, 0],
                        [13, 30, 0],
                        [13, 45, 0],
                        [14, 0, 0],
                        [14, 15, 0],
                        [14, 30, 0],
                        [14, 45, 0],
                        [15, 0, 0],
                        [15, 15, 0],
                        [15, 30, 1],
                        [15, 45, 1],
                        [16, 0, 1],
                        [16, 15, 1],
                        [16, 30, 1],
                        [16, 45, 1],
                        [17, 0, 1],
                        [17, 15, 1],
                        [17, 30, 1],
                        [17, 45, 1],
                        [18, 0, 1],
                        [18, 15, 1],
                        [18, 30, 1],
                        [18, 45, 0],
                        [19, 0, 0],
                        [19, 15, 0],
                        [19, 30, 0],
                        [19, 45, 0],
                        [20, 0, 0],
                        [20, 15, 0],
                        [20, 30, 0],
                        [20, 45, 0],
                        [21, 0, 0],
                        [21, 15, 0],
                        [21, 30, 0],
                        [21, 45, 0],
                        [22, 0, 0],
                        [22, 15, 0],
                        [22, 30, 0],
                        [22, 45, 0],
                        [23, 0, 0],
                        [23, 15, 0],
                        [23, 30, 0],
                        [23, 45, 0],
                    ],
                },
                "market_hours": {
                    "columns": ["day", "hour", "minute", "open"],
                    "index": [
                        0,
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                        18,
                        19,
                        20,
                        21,
                        22,
                        23,
                        24,
                        25,
                        26,
                        27,
                        28,
                        29,
                        30,
                        31,
                        32,
                        33,
                        34,
                        35,
                        36,
                        37,
                        38,
                        39,
                        40,
                        41,
                        42,
                        43,
                        44,
                        45,
                        46,
                        47,
                        48,
                        49,
                        50,
                        51,
                        52,
                        53,
                        54,
                        55,
                        56,
                        57,
                        58,
                        59,
                        60,
                        61,
                        62,
                        63,
                        64,
                        65,
                        66,
                        67,
                        68,
                        69,
                        70,
                        71,
                        72,
                        73,
                        74,
                        75,
                        76,
                        77,
                        78,
                        79,
                        80,
                        81,
                        82,
                        83,
                        84,
                        85,
                        86,
                        87,
                        88,
                        89,
                        90,
                        91,
                        92,
                        93,
                        94,
                        95,
                    ],
                    "data": [
                        [0, 0, 0, 0],
                        [0, 0, 15, 0],
                        [0, 0, 30, 0],
                        [0, 0, 45, 0],
                        [0, 1, 0, 0],
                        [0, 1, 15, 0],
                        [0, 1, 30, 0],
                        [0, 1, 45, 0],
                        [0, 2, 0, 0],
                        [0, 2, 15, 0],
                        [0, 2, 30, 0],
                        [0, 2, 45, 0],
                        [0, 3, 0, 0],
                        [0, 3, 15, 0],
                        [0, 3, 30, 0],
                        [0, 3, 45, 0],
                        [0, 4, 0, 0],
                        [0, 4, 15, 0],
                        [0, 4, 30, 1],
                        [0, 4, 45, 1],
                        [0, 5, 0, 1],
                        [0, 5, 15, 1],
                        [0, 5, 30, 1],
                        [0, 5, 45, 1],
                        [0, 6, 0, 1],
                        [0, 6, 15, 1],
                        [0, 6, 30, 1],
                        [0, 6, 45, 1],
                        [0, 7, 0, 1],
                        [0, 7, 15, 1],
                        [0, 7, 30, 1],
                        [0, 7, 45, 1],
                        [0, 8, 0, 1],
                        [0, 8, 15, 1],
                        [0, 8, 30, 1],
                        [0, 8, 45, 1],
                        [0, 9, 0, 1],
                        [0, 9, 15, 1],
                        [0, 9, 30, 1],
                        [0, 9, 45, 1],
                        [0, 10, 0, 1],
                        [0, 10, 15, 1],
                        [0, 10, 30, 1],
                        [0, 10, 45, 1],
                        [0, 11, 0, 1],
                        [0, 11, 15, 1],
                        [0, 11, 30, 1],
                        [0, 11, 45, 1],
                        [0, 12, 0, 1],
                        [0, 12, 15, 1],
                        [0, 12, 30, 1],
                        [0, 12, 45, 1],
                        [0, 13, 0, 1],
                        [0, 13, 15, 1],
                        [0, 13, 30, 1],
                        [0, 13, 45, 1],
                        [0, 14, 0, 1],
                        [0, 14, 15, 1],
                        [0, 14, 30, 1],
                        [0, 14, 45, 1],
                        [0, 15, 0, 1],
                        [0, 15, 15, 1],
                        [0, 15, 30, 1],
                        [0, 15, 45, 1],
                        [0, 16, 0, 1],
                        [0, 16, 15, 1],
                        [0, 16, 30, 1],
                        [0, 16, 45, 1],
                        [0, 17, 0, 1],
                        [0, 17, 15, 1],
                        [0, 17, 30, 1],
                        [0, 17, 45, 1],
                        [0, 18, 0, 1],
                        [0, 18, 15, 1],
                        [0, 18, 30, 1],
                        [0, 18, 45, 1],
                        [0, 19, 0, 1],
                        [0, 19, 15, 1],
                        [0, 19, 30, 1],
                        [0, 19, 45, 1],
                        [0, 20, 0, 1],
                        [0, 20, 15, 1],
                        [0, 20, 30, 1],
                        [0, 20, 45, 1],
                        [0, 21, 0, 1],
                        [0, 21, 15, 1],
                        [0, 21, 30, 1],
                        [0, 21, 45, 1],
                        [0, 22, 0, 1],
                        [0, 22, 15, 1],
                        [0, 22, 30, 1],
                        [0, 22, 45, 1],
                        [0, 23, 0, 1],
                        [0, 23, 15, 1],
                        [0, 23, 30, 1],
                        [0, 23, 45, 1],
                    ],
                },
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

    response = client.post("/input/", json=json_input)
    assert response.status_code == 200
    assert response.json() == [
        "Scheduler started with run_id: 2878898c-263f-4a32-9c14-ff15b60f91e3."
    ]
    test_heartbeat = HeartbeatStatus()
    test_heartbeat.version = 1.7
    test_heartbeat.payload = OptimizerInput(**json_input)
    test_heartbeat.reset()
    m.assert_called_once_with(compute_schedule, test_heartbeat)


def test_invalid_input(mocker):
    """Tests that the scheduler is not called when providing an invalid input"""
    m = mocker.patch("fastapi.BackgroundTasks.add_task", return_value=None)

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
