from dataclasses import asdict
from threading import Lock
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

from data_loader import get_dataset_info, DatasetNotFoundError, get_dataset_path
from engine import HospitalState, forecast, model_artifacts, simulate, summary, status

from supabase_client import check_supabase_health

app = FastAPI(title="HospAI Operations API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DatasetNotFoundError)
async def dataset_not_found_handler(request: Request, exc: DatasetNotFoundError):
    """Guarantees clear error reporting if hackathon_hospital_bottleneck_dataset.xlsx is missing."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "DatasetNotFoundError",
            "message": str(exc),
            "expected_filename": "hackathon_hospital_bottleneck_dataset.xlsx",
            "resolved_path": str(get_dataset_path()),
            "status": "DATASET_MISSING"
        },
    )


state = HospitalState()
lock = Lock()
decisions = []


class Scenario(BaseModel):
    arrival_multiplier: float = Field(1, ge=0.25, le=3)
    season: Literal["normal", "monsoon", "flu", "outbreak"] = "normal"
    staff_delta: int = Field(0, ge=-8, le=8)
    bed_delta: int = Field(0, ge=-10, le=4)
    discharge_extra: int = Field(0, ge=0, le=3)
    lab_delta: int = Field(0, ge=-8, le=8)
    radiology_delta: int = Field(0, ge=-3, le=5)


class Decision(BaseModel):
    action: str = Field(min_length=1, max_length=200)
    approved: bool
    operator: str = Field(default="Demo operator", max_length=100)
    scenario_reference: str | None = Field(default=None, max_length=100)


@app.get("/api/health")
def health():
    info = get_dataset_info()
    sb_health = check_supabase_health()
    return {
        "ok": True,
        "mode": "excel_dataset",
        "dataset_found": info.get("exists", False),
        "dataset_path": info.get("resolved_path"),
        "filename": info.get("filename"),
        "supabase": sb_health
    }


@app.get("/api/supabase/health")
def supabase_health():
    """Minimal backend-only Supabase connectivity check without exposing secret credentials."""
    return check_supabase_health()


@app.get("/api/dataset/info")
def dataset_info():
    return get_dataset_info()


@app.get("/api/status")
def get_status():
    with lock:
        return status(state)


@app.get("/api/snapshot")
def get_snapshot(season: Literal["normal", "monsoon", "flu", "outbreak"] = "normal"):
    with lock:
        snapshot = HospitalState(**asdict(state))
        decision_items = list(decisions)
    fc_res = forecast(step=snapshot.clock_step, season=season)
    intervals = fc_res["intervals"]
    risk_result = simulate(snapshot, intervals, seed=51)
    risk_summary = summary(risk_result)
    ds_info = get_dataset_info()

    return {
        "status": status(snapshot),
        "forecast": {
            "horizon_hours": 4,
            "season": season,
            "expected_total_arrivals": fc_res["predicted_4h_arrivals"],
            "predicted_peak_occupancy_pct": fc_res["predicted_peak_occupancy_pct"],
            "predicted_max_wait_minutes": fc_res["predicted_max_wait_minutes"],
            "predicted_overload_probability": fc_res["predicted_overload_probability"],
            "predicted_overload": fc_res["predicted_overload"],
            "intervals": intervals,
            "synthetic": False,
            "dataset_source": "hackathon_hospital_bottleneck_dataset.xlsx"
        },
        "bottlenecks": {
            "bottlenecks": risk_summary["bottlenecks"],
            "metrics": risk_summary["metrics"],
            "timeline": risk_result["timeline"],
            "season": season,
            "snapshot_reference": f"step-{snapshot.clock_step}",
            "synthetic": False,
        },
        "model": model_artifacts()[2],
        "dataset_info": ds_info,
        "decisions": {"items": decision_items},
        "snapshot_reference": f"step-{snapshot.clock_step}",
    }


@app.get("/api/model")
def get_model():
    return model_artifacts()[2]


@app.get("/api/forecast")
def get_forecast(season: Literal["normal", "monsoon", "flu", "outbreak"] = "normal"):
    with lock:
        step = state.clock_step
    fc_res = forecast(step=step, season=season)
    return {
        "horizon_hours": 4,
        "season": season,
        "expected_total_arrivals": fc_res["predicted_4h_arrivals"],
        "predicted_peak_occupancy_pct": fc_res["predicted_peak_occupancy_pct"],
        "predicted_max_wait_minutes": fc_res["predicted_max_wait_minutes"],
        "predicted_overload_probability": fc_res["predicted_overload_probability"],
        "predicted_overload": fc_res["predicted_overload"],
        "intervals": fc_res["intervals"],
        "synthetic": False,
        "dataset_source": "hackathon_hospital_bottleneck_dataset.xlsx"
    }


@app.post("/api/simulate")
def run_simulation(request: Scenario):
    with lock:
        s = HospitalState(**asdict(state))
    fc_res = forecast(
        step=s.clock_step, season=request.season, multiplier=request.arrival_multiplier
    )
    common = fc_res["intervals"]
    baseline = simulate(s, common, seed=51)
    changed = simulate(
        s,
        common,
        seed=51,
        staff_delta=request.staff_delta,
        bed_delta=request.bed_delta,
        discharge_extra=request.discharge_extra,
        lab_delta=request.lab_delta,
        radiology_delta=request.radiology_delta,
    )
    bs, cs = summary(baseline), summary(changed)
    return {
        "synthetic": False,
        "dataset_source": "hackathon_hospital_bottleneck_dataset.xlsx",
        "snapshot_reference": f"step-{s.clock_step}",
        "request": request.model_dump(),
        "baseline": {"timeline": baseline["timeline"], **bs},
        "scenario": {"timeline": changed["timeline"], **cs},
        "note": "Simulated scenario using ML models trained on hackathon_hospital_bottleneck_dataset.xlsx.",
    }


@app.get("/api/bottlenecks")
def bottlenecks(season: Literal["normal", "monsoon", "flu", "outbreak"] = "normal"):
    with lock:
        s = HospitalState(**asdict(state))
    fc_res = forecast(step=s.clock_step, season=season)
    result = simulate(s, fc_res["intervals"], seed=51)
    return {
        "bottlenecks": summary(result)["bottlenecks"],
        "metrics": summary(result)["metrics"],
        "timeline": result["timeline"],
        "season": season,
        "snapshot_reference": f"step-{s.clock_step}",
        "synthetic": False,
    }


@app.post("/api/recommend")
def recommend(request: Scenario):
    with lock:
        s = HospitalState(**asdict(state))
    fc_res = forecast(
        step=s.clock_step, season=request.season, multiplier=request.arrival_multiplier
    )
    demands = fc_res["intervals"]
    selected = {
        key: value
        for key, value in request.model_dump().items()
        if key not in ("season", "arrival_multiplier")
    }
    base = summary(simulate(s, demands, seed=51, **selected))["metrics"]
    proposals = [
        ("Expedite eligible discharges", {"discharge_extra": 1}),
        ("Activate 2 staffed ICU beds", {"bed_delta": 2}),
        ("Expand laboratory throughput", {"lab_delta": 3}),
    ]
    result = []
    for name, adjust in proposals:
        if (
            ("discharge_extra" in adjust and selected["discharge_extra"] >= 3)
            or (
                "lab_delta" in adjust
                and selected["lab_delta"] + adjust["lab_delta"] > 8
            )
            or (
                "bed_delta" in adjust
                and selected["bed_delta"] + adjust["bed_delta"] > 4
            )
        ):
            continue
        combined = {
            **selected,
            **{key: selected.get(key, 0) + value for key, value in adjust.items()},
        }
        baseline_icu_capacity = min(
            s.icu_physical,
            max(
                s.icu_occupied,
                s.icu_staffed
                + selected["bed_delta"]
                + int(selected["staff_delta"] / 2),
            ),
        )
        proposed_icu_capacity = min(
            s.icu_physical,
            max(
                s.icu_occupied,
                s.icu_staffed
                + combined["bed_delta"]
                + int(combined["staff_delta"] / 2),
            ),
        )
        if "bed_delta" in adjust and proposed_icu_capacity <= baseline_icu_capacity:
            continue
        vals = summary(simulate(s, demands, seed=51, **combined))["metrics"]
        gain = (
            (base["peak_icu_boarding"] - vals["peak_icu_boarding"]) * 4
            + (base["peak_ward_boarding"] - vals["peak_ward_boarding"]) * 2
            + (base["peak_lab_pending"] - vals["peak_lab_pending"]) * 0.2
        )
        result.append(
            {
                "action": name,
                "priority": "High" if gain >= 4 else "Review",
                "department": {
                    "Expedite eligible discharges": "Ward",
                    "Activate 2 staffed ICU beds": "ICU",
                    "Expand laboratory throughput": "Laboratory",
                }[name],
                "modeled_score_improvement": round(gain, 2),
                "baseline": base,
                "outcome": vals,
                "expected_benefit": f"Modeled score change: {round(gain,2)}; positive values indicate lower modeled bottleneck pressure.",
                "feasibility_conditions": "Requires operational staffing and resource verification before any real-world action.",
                "requires_human_approval": True,
                "assumptions": "Illustrative scenario simulation using ML models trained on hackathon_hospital_bottleneck_dataset.xlsx.",
            }
        )
    return {
        "recommendations": sorted(
            result, key=lambda x: x["modeled_score_improvement"], reverse=True
        ),
        "snapshot_reference": f"step-{s.clock_step}",
        "note": "Actions are illustrative proposals.",
    }


@app.post("/api/decision")
def decision(d: Decision):
    from datetime import datetime, timezone

    with lock:
        item = {
            **d.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "id": len(decisions) + 1,
        }
        decisions.append(item)
    return item


@app.get("/api/decisions")
def get_decisions():
    with lock:
        return {"items": list(decisions)}


@app.post("/api/advance")
def advance(season: Literal["normal", "monsoon", "flu", "outbreak"] = "normal"):
    global state
    with lock:
        s = HospitalState(**asdict(state))
        fc_res = forecast(step=s.clock_step, season=season, horizon=1)
        one = simulate(
            s,
            fc_res["intervals"],
            seed=51 + s.clock_step,
        )
        state = HospitalState(**one["final_state"])
        state.clock_step += 1
        return status(state)


@app.post("/api/reset")
def reset():
    global state
    with lock:
        state = HospitalState()
        decisions.clear()
        return status(state)
