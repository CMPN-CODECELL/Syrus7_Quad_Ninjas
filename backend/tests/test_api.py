from datetime import datetime
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_reports_excel_dataset():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["mode"] == "excel_dataset"
    assert data["dataset_found"] is True


def test_dataset_info_endpoint():
    res = client.get("/api/dataset/info")
    assert res.status_code == 200
    data = res.json()
    assert data["exists"] is True
    assert data["filename"] == "hackathon_hospital_bottleneck_dataset.xlsx"
    assert data["row_count"] == 17544
    assert data["column_count"] == 55
    assert "Hourly_Data" in data["worksheets"]
    assert data["data_quality_status"] == "VALID"


def test_snapshot_returns_coherent_resource_and_forecast_data():
    client.post("/api/reset")
    response = client.get("/api/snapshot?season=normal")

    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["snapshot_reference"] == "step-0"
    assert snapshot["status"]["clock_step"] == 0
    assert len(snapshot["forecast"]["intervals"]) == 16
    assert snapshot["forecast"]["season"] == "normal"
    assert (
        snapshot["bottlenecks"]["snapshot_reference"] == snapshot["snapshot_reference"]
    )
    assert snapshot["status"]["resources"]["beds"]["physical"] == 69
    assert snapshot["status"]["resources"]["beds"]["staffed"] == 60
    assert snapshot["dataset_info"]["exists"] is True
    assert snapshot["dataset_info"]["row_count"] == 17544


def test_season_options_change_forecast():
    normal = client.get("/api/forecast?season=normal").json()
    flu = client.get("/api/forecast?season=flu").json()
    outbreak = client.get("/api/forecast?season=outbreak").json()

    assert flu["expected_total_arrivals"] > normal["expected_total_arrivals"]
    assert outbreak["expected_total_arrivals"] > flu["expected_total_arrivals"]
    assert client.get("/api/forecast?season=unsupported").status_code == 422


def test_advance_increments_clock_by_one_interval_and_reset_restores_it():
    client.post("/api/reset")
    before = client.get("/api/status").json()
    after = client.post("/api/advance").json()

    before_time = datetime.fromisoformat(before["timestamp"])
    after_time = datetime.fromisoformat(after["timestamp"])
    assert after["clock_step"] == before["clock_step"] + 1
    assert (after_time - before_time).total_seconds() == 15 * 60

    second = client.post("/api/advance?season=flu")
    assert second.status_code == 200
    second_time = datetime.fromisoformat(second.json()["timestamp"])
    assert second.json()["clock_step"] == after["clock_step"] + 1
    assert (second_time - after_time).total_seconds() == 15 * 60

    reset = client.post("/api/reset").json()
    assert reset["clock_step"] == 0
    assert reset["timestamp"] == before["timestamp"]


def test_decision_log_keeps_scenario_reference_and_reset_clears_it():
    client.post("/api/reset")
    response = client.post(
        "/api/decision",
        json={
            "action": "Review simulated discharge proposal",
            "approved": True,
            "scenario_reference": "step-0",
        },
    )

    assert response.status_code == 200
    entry = response.json()
    assert entry["scenario_reference"] == "step-0"
    assert entry["approved"] is True
    assert entry["timestamp"]
    assert client.get("/api/decisions").json()["items"] == [entry]

    client.post("/api/reset")
    assert client.get("/api/decisions").json()["items"] == []
