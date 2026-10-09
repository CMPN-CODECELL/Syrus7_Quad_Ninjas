import React from 'react';
import { AlertTriangle, BedDouble, BrainCircuit, Building2, TrendingUp } from 'lucide-react';
import { ForecastChart } from '../components/charts/HospitalCharts';
import { FlowNode, Progress, SectionHeader, StatCard } from '../components/ui/HospitalComponents';
import { NAV_ITEMS } from '../constants/dashboard';
import { riskFor } from '../utils/hospital';

export default function OperationsDashboard({ overview, inpatientBeds, departments, bottlenecks, forecast, forecastData, setTab }) {
  return <>
    <div className="stats-grid">
      <StatCard label="Inpatient bed occupancy" value={`${overview.occupancy}%`} detail={`${inpatientBeds?.occupied ?? 0} of ${inpatientBeds?.staffed ?? 0} staffed beds`} />
      <StatCard label="Available staffed beds" value={overview.available} detail="ICU and Ward combined" />
      <StatCard label="Emergency patients waiting" value={overview.waiting} detail="Patients, not minutes" />
      <StatCard label="Predicted bottlenecks" value={overview.alertCount} detail="First threshold crossings · 4h" warning={overview.alertCount > 0} />
    </div>
    <div className="dashboard-grid">
      <section className="card panel dashboard-departments">
        <SectionHeader title="Department health" icon={<Building2 size={17} />} aside="Current snapshot" />
        <div className="department-grid">
          {departments.map((department) => {
            const utilization = department.capacity ? Math.min(100, Math.round(department.occupied / department.capacity * 100)) : 0;
            const risk = riskFor(department.id, bottlenecks?.bottlenecks || []);
            return <div key={department.id} className="department-card">
              <div className="row-between"><strong>{department.id}</strong><span className={`status-chip ${risk ? 'risk' : 'good'}`}>{risk?.severity || 'Within threshold'}</span></div>
              <strong className="department-value">{department.occupied} <small>/ {department.capacity} {department.unit}</small></strong>
              <Progress value={utilization} tone={risk ? 'warning' : 'good'} />
              <small>{department.id === 'Emergency' ? `${department.waiting} waiting · ${department.boarding} boarding` : `${department.waiting} queued`}</small>
            </div>;
          })}
        </div>
      </section>
      <section className="card panel">
        <SectionHeader title="Early warning center" icon={<AlertTriangle size={17} />} aside="Projected threshold" />
        {bottlenecks?.bottlenecks?.length ? bottlenecks.bottlenecks.map((risk) => (
          <div key={risk.department} className="alert-row">
            <div className="alert-header"><strong>{risk.department}</strong><span className={`severity ${risk.severity.toLowerCase()}`}>{risk.severity}</span></div>
            <p>{risk.minutes_to_onset} min · {risk.reason}</p>
          </div>
        )) : <p className="empty-text">No threshold crossing in the four-hour simulation.</p>}
      </section>
    </div>
    <section className="card panel">
      <SectionHeader title="Four-hour arrivals forecast" icon={<TrendingUp size={17} />} aside={`${forecast?.season || 'normal'} · ${forecast?.horizon_hours || 4} hours`} />
      <ForecastChart data={forecastData} />
    </section>
    <section className="quick-actions">
      <button onClick={() => setTab(NAV_ITEMS[2])}><TrendingUp size={15} />View Predictions</button>
      <button onClick={() => setTab(NAV_ITEMS[4])}><BrainCircuit size={15} />Open Scenario Lab</button>
      <button onClick={() => setTab(NAV_ITEMS[1])}><BedDouble size={15} />Review Resources</button>
    </section>
  </>;
}
