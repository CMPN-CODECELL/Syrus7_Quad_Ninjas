from engine import HospitalState, forecast, model_artifacts, simulate, status, summary


def test_forecast_length_and_nonnegative():
    fc = forecast()
    intervals = fc["intervals"]
    assert len(intervals) == 16
    assert all(x["expected_arrivals"] >= 0 for x in intervals)
    assert fc["predicted_4h_arrivals"] >= 0
    assert "predicted_peak_occupancy_pct" in fc
    assert "predicted_max_wait_minutes" in fc
    assert "predicted_overload_probability" in fc


def test_conservation_and_capacity():
    s = HospitalState()
    fc = forecast()
    result = simulate(s, fc["intervals"], seed=51)
    assert len(result["timeline"]) == 16
    for row in result["timeline"]:
        assert row["icu_occupied"] <= row["icu_capacity"]
        assert row["ward_occupied"] <= row["ward_capacity"]


def test_deterministic():
    fc = forecast()
    a = simulate(HospitalState(), fc["intervals"], seed=51)
    b = simulate(HospitalState(), fc["intervals"], seed=51)
    assert a == b


def test_model_artifacts_has_all_4_prediction_tasks():
    models, df, metrics = model_artifacts()
    assert len(models) == 4
    assert set(models.keys()) == {"arrivals", "peak_occupancy", "max_wait", "overload"}

    tasks = metrics["tasks"]
    assert "arrivals_4h" in tasks
    assert "peak_occupancy_4h" in tasks
    assert "max_wait_4h" in tasks
    assert "overload_4h" in tasks

    # Regression metrics
    for key in ["arrivals_4h", "peak_occupancy_4h", "max_wait_4h"]:
        t = tasks[key]
        assert "model_mae" in t
        assert "model_rmse" in t
        assert "baseline_mae" in t
        assert "baseline_rmse" in t

    # Classification metrics
    t_overload = tasks["overload_4h"]
    assert "precision" in t_overload
    assert "recall" in t_overload
    assert "f1_score" in t_overload
    assert "pr_auc" in t_overload
    assert "roc_auc" in t_overload
    assert len(t_overload["confusion_matrix"]) == 2


def test_chronological_split_date_ranges():
    _, _, metrics = model_artifacts()
    splits = metrics["splits"]

    train_end = splits["train"]["end"]
    val_start = splits["validation"]["start"]
    val_end = splits["validation"]["end"]
    test_start = splits["test"]["start"]

    assert train_end < val_start
    assert val_end < test_start
    assert splits["train"]["count"] + splits["validation"]["count"] + splits["test"]["count"] == metrics["clean_rows"]


def test_resource_snapshot_separates_physical_and_staffed_beds():
    snapshot = status(HospitalState())
    beds = snapshot["resources"]["beds"]
    assert beds["physical"] == 69
    assert beds["staffed"] == 60
    assert beds["occupied"] == 50
    assert beds["available_staffed"] == 10
    assert beds["temporarily_unavailable"] == 9
    assert snapshot["resources"]["staffing"]["source"] == "synthetic_demo_assumption"


def test_negative_icu_capacity_delta_cannot_go_below_occupied_beds():
    state = HospitalState()
    result = simulate(
        state, [{"time": "2026-10-09T10:15:00", "expected_arrivals": 0}], bed_delta=-10
    )
    final = result["final_state"]
    assert final["icu_staffed"] >= final["icu_occupied"]
    assert final["icu_staffed"] <= final["icu_physical"]
