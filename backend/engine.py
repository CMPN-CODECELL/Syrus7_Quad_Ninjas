"""HospAI Operational Decision-Support Engine.

Integrates real historical operational data from hackathon_hospital_bottleneck_dataset.xlsx.
Provides data loading, ML model training across 4 predictive tasks, demand forecasting,
patient flow simulation, and bottleneck detection.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
import math
import numpy as np
import pandas as pd

from data_loader import load_dataset, get_dataset_info, validate_dataset_exists, get_dataset_path


@dataclass
class HospitalState:
    ed_waiting: int = 12
    ed_in_treatment: int = 12
    ed_boarding_icu: int = 2
    ed_boarding_ward: int = 3
    icu_occupied: int = 18
    icu_staffed: int = 20
    icu_physical: int = 24
    ward_occupied: int = 32
    ward_staffed: int = 40
    ward_physical: int = 45
    lab_pending: int = 17
    radiology_pending: int = 9
    total_discharged: int = 0
    total_external_arrivals: int = 0
    lab_completed_total: int = 0
    radiology_completed_total: int = 0
    lab_new_last_step: int = 0
    radiology_new_last_step: int = 0
    clock_step: int = 0

    def active_patients(self):
        return (
            self.ed_waiting
            + self.ed_in_treatment
            + self.ed_boarding_icu
            + self.ed_boarding_ward
            + self.icu_occupied
            + self.ward_occupied
        )


DAY_MAP = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6
}

FEATURES = [
    "hour_of_day",
    "day_of_week_num",
    "month",
    "is_weekend",
    "is_public_holiday",
    "arrivals_last_hour",
    "arrivals_last_3h",
    "arrivals_last_6h",
    "arrivals_last_24h",
    "arrivals_same_hour_prev_week",
    "occupied_beds",
    "doctors_on_duty",
    "nurses_on_duty",
    "patients_awaiting_lab",
    "patients_awaiting_imaging",
]


@lru_cache(maxsize=1)
def model_artifacts():
    """Trains 4 machine learning models on hackathon_hospital_bottleneck_dataset.xlsx.

    Tasks:
    1. Four-hour arrival forecasting (Regression: actual_arrivals_next_4h)
    2. Four-hour peak occupancy prediction (Regression: actual_peak_occupancy_next_4h_pct)
    3. Four-hour max wait time prediction (Regression: actual_max_wait_next_4h_minutes)
    4. Four-hour overload risk classification (Classification: actual_overload_next_4h)

    Returns:
        tuple: (models_dict, hourly_dataframe, metrics_dictionary)
    """
    from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
    from sklearn.metrics import (
        mean_absolute_error, root_mean_squared_error,
        precision_score, recall_score, f1_score, confusion_matrix,
        precision_recall_curve, auc, roc_auc_score
    )

    hourly_df, sheets_dict = load_dataset()
    dataset_path = get_dataset_path()

    df = hourly_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    if "day_of_week" in df.columns:
        df["day_of_week_num"] = df["day_of_week"].map(DAY_MAP).fillna(0).astype(int)

    target_cols = [
        "actual_arrivals_next_4h",
        "actual_peak_occupancy_next_4h_pct",
        "actual_max_wait_next_4h_minutes",
        "actual_overload_next_4h"
    ]

    clean_df = df.dropna(subset=target_cols).copy()

    # Chronological Split: 70% Train, 15% Validation, 15% Test
    n = len(clean_df)
    train_end = int(0.70 * n)
    val_end = int(0.85 * n)

    train = clean_df.iloc[:train_end]
    val = clean_df.iloc[train_end:val_end]
    test = clean_df.iloc[val_end:]

    # Model 1: 4-Hour Arrivals Forecast (Regression)
    m_arrivals = HistGradientBoostingRegressor(random_state=42)
    m_arrivals.fit(train[FEATURES], train["actual_arrivals_next_4h"])
    pred_arrivals = np.maximum(0, m_arrivals.predict(test[FEATURES]))
    target_arrivals = test["actual_arrivals_next_4h"].values

    mae_arrivals = float(mean_absolute_error(target_arrivals, pred_arrivals))
    rmse_arrivals = float(root_mean_squared_error(target_arrivals, pred_arrivals))

    base_arrivals_rates = train.groupby(["hour_of_day", "day_of_week_num"])["actual_arrivals_next_4h"].mean()
    base_arrivals_fallback = train["actual_arrivals_next_4h"].mean()
    base_pred_arrivals = np.array([
        base_arrivals_rates.get((row.hour_of_day, row.day_of_week_num), base_arrivals_fallback)
        for row in test.itertuples()
    ])
    base_mae_arrivals = float(mean_absolute_error(target_arrivals, base_pred_arrivals))
    base_rmse_arrivals = float(root_mean_squared_error(target_arrivals, base_pred_arrivals))

    # Model 2: 4-Hour Peak Occupancy % (Regression)
    m_occupancy = HistGradientBoostingRegressor(random_state=42)
    m_occupancy.fit(train[FEATURES], train["actual_peak_occupancy_next_4h_pct"])
    pred_occupancy = m_occupancy.predict(test[FEATURES])
    target_occupancy = test["actual_peak_occupancy_next_4h_pct"].values

    mae_occupancy = float(mean_absolute_error(target_occupancy, pred_occupancy))
    rmse_occupancy = float(root_mean_squared_error(target_occupancy, pred_occupancy))

    base_occ_rates = train.groupby(["hour_of_day", "day_of_week_num"])["actual_peak_occupancy_next_4h_pct"].mean()
    base_occ_fallback = train["actual_peak_occupancy_next_4h_pct"].mean()
    base_pred_occ = np.array([
        base_occ_rates.get((row.hour_of_day, row.day_of_week_num), base_occ_fallback)
        for row in test.itertuples()
    ])
    base_mae_occ = float(mean_absolute_error(target_occupancy, base_pred_occ))
    base_rmse_occ = float(root_mean_squared_error(target_occupancy, base_pred_occ))

    # Model 3: 4-Hour Max Wait Time (Regression)
    m_wait = HistGradientBoostingRegressor(random_state=42)
    m_wait.fit(train[FEATURES], train["actual_max_wait_next_4h_minutes"])
    pred_wait = np.maximum(0, m_wait.predict(test[FEATURES]))
    target_wait = test["actual_max_wait_next_4h_minutes"].values

    mae_wait = float(mean_absolute_error(target_wait, pred_wait))
    rmse_wait = float(root_mean_squared_error(target_wait, pred_wait))

    base_wait_rates = train.groupby(["hour_of_day", "day_of_week_num"])["actual_max_wait_next_4h_minutes"].mean()
    base_wait_fallback = train["actual_max_wait_next_4h_minutes"].mean()
    base_pred_wait = np.array([
        base_wait_rates.get((row.hour_of_day, row.day_of_week_num), base_wait_fallback)
        for row in test.itertuples()
    ])
    base_mae_wait = float(mean_absolute_error(target_wait, base_pred_wait))
    base_rmse_wait = float(root_mean_squared_error(target_wait, base_pred_wait))

    # Model 4: 4-Hour Overload Classification
    m_overload = HistGradientBoostingClassifier(random_state=42)
    m_overload.fit(train[FEATURES], train["actual_overload_next_4h"])
    pred_overload_prob = m_overload.predict_proba(test[FEATURES])[:, 1]
    pred_overload_class = (pred_overload_prob >= 0.5).astype(int)
    target_overload = test["actual_overload_next_4h"].values.astype(int)

    precision_overload = float(precision_score(target_overload, pred_overload_class, zero_division=0))
    recall_overload = float(recall_score(target_overload, pred_overload_class, zero_division=0))
    f1_overload = float(f1_score(target_overload, pred_overload_class, zero_division=0))
    cm_overload = confusion_matrix(target_overload, pred_overload_class).tolist()
    prec_curve, rec_curve, _ = precision_recall_curve(target_overload, pred_overload_prob)
    pr_auc_overload = float(auc(rec_curve, prec_curve))
    roc_auc_overload = float(roc_auc_score(target_overload, pred_overload_prob))

    models = {
        "arrivals": m_arrivals,
        "peak_occupancy": m_occupancy,
        "max_wait": m_wait,
        "overload": m_overload,
    }

    metrics = {
        "model_name": "HistGradientBoosting Suite",
        "data_type": "excel_dataset",
        "dataset_path": str(dataset_path),
        "filename": dataset_path.name,
        "worksheet": "Hourly_Data",
        "total_dataset_rows": len(hourly_df),
        "total_dataset_cols": len(hourly_df.columns),
        "clean_rows": n,
        "splits": {
            "train": {
                "count": len(train),
                "start": train["timestamp"].min().isoformat(),
                "end": train["timestamp"].max().isoformat()
            },
            "validation": {
                "count": len(val),
                "start": val["timestamp"].min().isoformat(),
                "end": val["timestamp"].max().isoformat()
            },
            "test": {
                "count": len(test),
                "start": test["timestamp"].min().isoformat(),
                "end": test["timestamp"].max().isoformat()
            }
        },
        "tasks": {
            "arrivals_4h": {
                "target": "actual_arrivals_next_4h",
                "units": "patients per 4 hours",
                "model_mae": round(mae_arrivals, 3),
                "model_rmse": round(rmse_arrivals, 3),
                "baseline_mae": round(base_mae_arrivals, 3),
                "baseline_rmse": round(base_rmse_arrivals, 3),
            },
            "peak_occupancy_4h": {
                "target": "actual_peak_occupancy_next_4h_pct",
                "units": "percentage (%)",
                "model_mae": round(mae_occupancy, 3),
                "model_rmse": round(rmse_occupancy, 3),
                "baseline_mae": round(base_mae_occ, 3),
                "baseline_rmse": round(base_rmse_occ, 3),
            },
            "max_wait_4h": {
                "target": "actual_max_wait_next_4h_minutes",
                "units": "minutes",
                "model_mae": round(mae_wait, 3),
                "model_rmse": round(rmse_wait, 3),
                "baseline_mae": round(base_mae_wait, 3),
                "baseline_rmse": round(base_rmse_wait, 3),
            },
            "overload_4h": {
                "target": "actual_overload_next_4h",
                "units": "binary classification (0/1)",
                "precision": round(precision_overload, 3),
                "recall": round(recall_overload, 3),
                "f1_score": round(f1_overload, 3),
                "pr_auc": round(pr_auc_overload, 3),
                "roc_auc": round(roc_auc_overload, 3),
                "confusion_matrix": cm_overload,
            }
        },
        "features_used": FEATURES,
        # Legacy backward-compatibility top-level keys for existing tests/UI
        "model_mae": round(mae_arrivals, 3),
        "baseline_mae": round(base_mae_arrivals, 3),
        "test_intervals": len(test),
    }

    return models, hourly_df, metrics


def forecast(
    step: int = 0, season: str = "normal", multiplier: float = 1.0, horizon: int = 16
):
    """Generates a 4-hour forecast using models trained on hackathon_hospital_bottleneck_dataset.xlsx."""
    models, hourly_df, metrics = model_artifacts()

    last_ts = pd.to_datetime(hourly_df["timestamp"].max())
    start = last_ts + pd.Timedelta(minutes=15 * step)

    latest_row = hourly_df.iloc[-1]
    recent_arrivals_1h = float(latest_row.get("arrivals_last_hour", 6.0))
    recent_arrivals_3h = float(latest_row.get("arrivals_last_3h", 18.0))
    recent_arrivals_6h = float(latest_row.get("arrivals_last_6h", 36.0))
    recent_arrivals_24h = float(latest_row.get("arrivals_last_24h", 146.0))
    occupied_beds = float(latest_row.get("occupied_beds", 19.0))
    doctors = float(latest_row.get("doctors_on_duty", 5.0))
    nurses = float(latest_row.get("nurses_on_duty", 8.0))
    lab = float(latest_row.get("patients_awaiting_lab", 1.0))
    imaging = float(latest_row.get("patients_awaiting_imaging", 1.0))

    feature_row = {
        "hour_of_day": start.hour,
        "day_of_week_num": start.weekday(),
        "month": start.month,
        "is_weekend": int(start.weekday() >= 5),
        "is_public_holiday": 0,
        "arrivals_last_hour": recent_arrivals_1h,
        "arrivals_last_3h": recent_arrivals_3h,
        "arrivals_last_6h": recent_arrivals_6h,
        "arrivals_last_24h": recent_arrivals_24h,
        "arrivals_same_hour_prev_week": recent_arrivals_1h,
        "occupied_beds": occupied_beds,
        "doctors_on_duty": doctors,
        "nurses_on_duty": nurses,
        "patients_awaiting_lab": lab,
        "patients_awaiting_imaging": imaging,
    }

    feature_df = pd.DataFrame([feature_row])[FEATURES]

    # Predict all 4 tasks
    predicted_4h_arrivals = float(max(0.0, models["arrivals"].predict(feature_df)[0]))
    predicted_peak_occ = float(models["peak_occupancy"].predict(feature_df)[0])
    predicted_max_wait = float(max(0.0, models["max_wait"].predict(feature_df)[0]))
    predicted_overload_prob = float(models["overload"].predict_proba(feature_df)[0, 1])

    season_factor = {"normal": 1.0, "monsoon": 1.15, "flu": 1.3, "outbreak": 1.5}.get(season, 1.0)
    total_expected = max(0.0, predicted_4h_arrivals * multiplier * season_factor)

    # Distribute total 4-hour expected arrivals across 16 intervals (15-min steps)
    results = []
    base_per_step = total_expected / 16.0

    for j in range(horizon):
        time = start + pd.Timedelta(minutes=15 * j)
        # Apply subtle diurnal curve variation across the 4-hour window
        hour = time.hour
        curve_factor = 1.1 if 9 <= hour <= 20 else 0.9
        step_expected = base_per_step * curve_factor
        results.append(
            {"time": time.isoformat(), "expected_arrivals": round(step_expected, 3)}
        )

    # Re-normalize so sum(expected_arrivals) equals total_expected
    raw_sum = sum(x["expected_arrivals"] for x in results)
    if raw_sum > 0:
        scale = total_expected / raw_sum
        for entry in results:
            entry["expected_arrivals"] = round(entry["expected_arrivals"] * scale, 3)

    return {
        "intervals": results,
        "predicted_4h_arrivals": round(total_expected, 2),
        "predicted_peak_occupancy_pct": round(predicted_peak_occ, 1),
        "predicted_max_wait_minutes": round(predicted_max_wait, 1),
        "predicted_overload_probability": round(predicted_overload_prob, 3),
        "predicted_overload": predicted_overload_prob >= 0.5,
    }


def _distribute_workload(arrivals: int, rng: np.random.Generator):
    icu = int(rng.binomial(arrivals, 0.08))
    ward = int(rng.binomial(arrivals - icu, 0.22))
    discharged = arrivals - icu - ward
    return icu, ward, discharged


def simulate(
    state: HospitalState,
    demand: list[dict],
    *,
    staff_delta: int = 0,
    bed_delta: int = 0,
    discharge_extra: int = 0,
    lab_delta: int = 0,
    radiology_delta: int = 0,
    seed: int = 51,
):
    rng = np.random.default_rng(seed)
    s = HospitalState(**asdict(state))
    s.icu_staffed = min(
        s.icu_physical,
        max(s.icu_occupied, s.icu_staffed + bed_delta + int(staff_delta / 2)),
    )
    timeline = []
    prev_active = s.active_patients()
    start_dis = s.total_discharged
    start_arrivals = s.total_external_arrivals
    for i, entry in enumerate(demand):
        arrivals = int(rng.poisson(max(0, entry["expected_arrivals"])))
        s.total_external_arrivals += arrivals
        s.ed_waiting += arrivals
        ed_served = min(s.ed_waiting, 8)
        s.ed_waiting -= ed_served
        s.ed_in_treatment += ed_served
        ed_finished = min(s.ed_in_treatment, 7)
        s.ed_in_treatment -= ed_finished
        to_icu, to_ward, home = _distribute_workload(ed_finished, rng)
        s.ed_boarding_icu += to_icu
        s.ed_boarding_ward += to_ward
        s.total_discharged += home
        icu_dis = min(
            s.icu_occupied, int(rng.binomial(s.icu_occupied, 0.018)) + discharge_extra
        )
        ward_dis = min(
            s.ward_occupied, int(rng.binomial(s.ward_occupied, 0.028)) + discharge_extra
        )
        s.icu_occupied -= icu_dis
        s.ward_occupied -= ward_dis
        s.total_discharged += icu_dis + ward_dis
        icu_admit = min(s.ed_boarding_icu, max(0, s.icu_staffed - s.icu_occupied))
        s.ed_boarding_icu -= icu_admit
        s.icu_occupied += icu_admit
        ward_admit = min(s.ed_boarding_ward, max(0, s.ward_staffed - s.ward_occupied))
        s.ed_boarding_ward -= ward_admit
        s.ward_occupied += ward_admit
        lab_created = int(rng.binomial(ed_served, 0.55))
        rad_created = int(rng.binomial(ed_served, 0.25))
        lab_capacity = max(0, 9 + lab_delta)
        rad_capacity = max(0, 4 + radiology_delta)
        lab_processed = min(s.lab_pending + lab_created, lab_capacity)
        rad_processed = min(s.radiology_pending + rad_created, rad_capacity)
        s.lab_pending = max(0, s.lab_pending + lab_created - lab_processed)
        s.radiology_pending = max(0, s.radiology_pending + rad_created - rad_processed)
        s.lab_completed_total += lab_processed
        s.radiology_completed_total += rad_processed
        s.lab_new_last_step = lab_created
        s.radiology_new_last_step = rad_created
        assert (
            s.active_patients() + s.total_discharged - start_dis
            == prev_active + s.total_external_arrivals - start_arrivals
        ), "Patient conservation failed"
        assert 0 <= s.icu_occupied <= s.icu_staffed <= s.icu_physical
        assert 0 <= s.ward_occupied <= s.ward_staffed <= s.ward_physical
        timeline.append(
            {
                "time": entry["time"],
                "icu_occupied": s.icu_occupied,
                "icu_capacity": s.icu_staffed,
                "icu_boarding": s.ed_boarding_icu,
                "ward_occupied": s.ward_occupied,
                "ward_capacity": s.ward_staffed,
                "ward_boarding": s.ed_boarding_ward,
                "ed_waiting": s.ed_waiting,
                "ed_boarding": s.ed_boarding_icu + s.ed_boarding_ward,
                "lab_pending": s.lab_pending,
                "radiology_pending": s.radiology_pending,
                "lab_created": lab_created,
                "lab_processed": lab_processed,
                "radiology_created": rad_created,
                "radiology_processed": rad_processed,
                "external_arrivals": arrivals,
                "discharged_cumulative": s.total_discharged,
            }
        )
    return {"timeline": timeline, "final_state": asdict(s)}


def summary(result):
    lines = result["timeline"]
    metrics = {
        "peak_icu_boarding": max(x["icu_boarding"] for x in lines),
        "peak_ward_boarding": max(x["ward_boarding"] for x in lines),
        "peak_ed_waiting": max(x["ed_waiting"] for x in lines),
        "peak_lab_pending": max(x["lab_pending"] for x in lines),
        "peak_radiology_pending": max(x["radiology_pending"] for x in lines),
        "total_new_arrivals": sum(x["external_arrivals"] for x in lines),
    }
    thresholds = {
        "ICU": ("icu_boarding", 1),
        "Ward": ("ward_boarding", 2),
        "Emergency": ("ed_waiting", 15),
        "Laboratory": ("lab_pending", 20),
        "Radiology": ("radiology_pending", 12),
    }
    warnings = []
    for name, (key, threshold) in thresholds.items():
        violations = [(i, x[key]) for i, x in enumerate(lines) if x[key] >= threshold]
        if violations:
            idx, value = violations[0]
            warnings.append(
                {
                    "department": name,
                    "severity": "HIGH" if value >= threshold * 2 else "MEDIUM",
                    "minutes_to_onset": (idx + 1) * 15,
                    "metric": key,
                    "first_observed_value": value,
                    "threshold": threshold,
                    "reason": f'Projected {key.replace("_"," ")} reaches {value} (warning threshold {threshold}).',
                }
            )
    return {"metrics": metrics, "bottlenecks": warnings}


def status(s: HospitalState):
    departments = [
        {
            "id": "Emergency",
            "occupied": s.ed_in_treatment,
            "capacity": 20,
            "waiting": s.ed_waiting,
            "boarding": s.ed_boarding_icu + s.ed_boarding_ward,
            "unit": "treatment spaces",
        },
        {
            "id": "ICU",
            "occupied": s.icu_occupied,
            "capacity": s.icu_staffed,
            "physical_capacity": s.icu_physical,
            "waiting": s.ed_boarding_icu,
            "unit": "staffed beds",
        },
        {
            "id": "Ward",
            "occupied": s.ward_occupied,
            "capacity": s.ward_staffed,
            "physical_capacity": s.ward_physical,
            "waiting": s.ed_boarding_ward,
            "unit": "staffed beds",
        },
        {
            "id": "Laboratory",
            "occupied": s.lab_pending,
            "capacity": 9,
            "waiting": s.lab_pending,
            "unit": "tests per 15 min",
        },
        {
            "id": "Radiology",
            "occupied": s.radiology_pending,
            "capacity": 4,
            "waiting": s.radiology_pending,
            "unit": "scans per 15 min",
        },
    ]
    doctor_allocation = {
        "Emergency": 4,
        "ICU": 4,
        "Ward": 6,
        "Laboratory": 2,
        "Radiology": 2,
    }
    nurse_allocation = {
        "Emergency": 12,
        "ICU": 12,
        "Ward": 18,
        "Laboratory": 4,
        "Radiology": 4,
    }
    diagnostic_load = lambda pending, completed, new, capacity: {
        "pending": pending,
        "completed_total": completed,
        "new_requests_last_15m": new,
        "processing_capacity_per_15m": capacity,
        "estimated_backlog_intervals": (
            round(pending / capacity, 1) if capacity else None
        ),
    }
    staffed_beds = s.icu_staffed + s.ward_staffed
    return {
        "timestamp": (
            datetime(2025, 12, 31, 23, 0) + timedelta(minutes=15 * s.clock_step)
        ).isoformat(),
        "clock_step": s.clock_step,
        "synthetic": False,
        "dataset_source": "hackathon_hospital_bottleneck_dataset.xlsx",
        "departments": [*departments],
        "resources": {
            "beds": {
                "physical": s.icu_physical + s.ward_physical,
                "staffed": staffed_beds,
                "occupied": s.icu_occupied + s.ward_occupied,
                "available_staffed": staffed_beds - s.icu_occupied - s.ward_occupied,
                "temporarily_unavailable": s.icu_physical
                + s.ward_physical
                - staffed_beds,
                "departments": [
                    {
                        "department": "ICU",
                        "physical": s.icu_physical,
                        "staffed": s.icu_staffed,
                        "occupied": s.icu_occupied,
                        "available_staffed": s.icu_staffed - s.icu_occupied,
                    },
                    {
                        "department": "Ward",
                        "physical": s.ward_physical,
                        "staffed": s.ward_staffed,
                        "occupied": s.ward_occupied,
                        "available_staffed": s.ward_staffed - s.ward_occupied,
                    },
                ],
            },
            "staffing": {
                "source": "synthetic_demo_assumption",
                "total_doctors": 24,
                "assigned_doctors": 18,
                "available_doctors": 6,
                "total_nurses": 60,
                "assigned_nurses": 50,
                "available_nurses": 10,
                "departments": [
                    {
                        "department": name,
                        "assigned_doctors": doctor_allocation[name],
                        "assigned_nurses": nurse_allocation[name],
                    }
                    for name in doctor_allocation
                ],
            },
            "diagnostics": {
                "laboratory": diagnostic_load(
                    s.lab_pending, s.lab_completed_total, s.lab_new_last_step, 9
                ),
                "radiology": diagnostic_load(
                    s.radiology_pending,
                    s.radiology_completed_total,
                    s.radiology_new_last_step,
                    4,
                ),
            },
        },
        "active_patients": s.active_patients(),
        "discharged_in_demo": s.total_discharged,
    }
