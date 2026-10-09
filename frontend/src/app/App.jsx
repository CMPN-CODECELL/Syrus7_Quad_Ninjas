import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity, Clock3, PanelLeftClose, PanelLeftOpen, Play, RefreshCw, RotateCcw, ShieldCheck,
} from 'lucide-react';
import BottleneckPrediction from '../pages/BottleneckPrediction';
import OperationsDashboard from '../pages/OperationsDashboard';
import PatientFlow from '../pages/PatientFlow';
import ResourceCapacity from '../pages/ResourceCapacity';
import ScenarioLab from '../pages/ScenarioLab';
import { call, API } from '../services/api';
import { COLORS, NAV_ICONS, NAV_ITEMS } from '../constants/dashboard';
import { formatAxisTime, formatTime, riskFor } from '../utils/hospital';

export default function App() {
  const [tab, setTab] = useState(NAV_ITEMS[0]);
  const [status, setStatus] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [bottlenecks, setBottlenecks] = useState(null);
  const [model, setModel] = useState(null);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [results, setResults] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [season, setSeason] = useState('normal');
  const [arrivals, setArrivals] = useState(1);
  const [bedDelta, setBedDelta] = useState(0);
  const [discharges, setDischarges] = useState(0);
  const [staffDelta, setStaffDelta] = useState(0);
  const [labDelta, setLabDelta] = useState(0);
  const [radiologyDelta, setRadiologyDelta] = useState(0);
  const [departmentFilter, setDepartmentFilter] = useState('All Inpatient Departments');
  const [highlight, setHighlight] = useState(null);
  const [flowDepartment, setFlowDepartment] = useState('All');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  async function load() {
    setBusy(true);
    setError('');
    try {
      const snapshot = await call(`/api/snapshot?season=${season}`);
      setStatus(snapshot.status);
      setForecast(snapshot.forecast);
      setBottlenecks(snapshot.bottlenecks);
      setModel(snapshot.model);
      setDatasetInfo(snapshot.dataset_info);
      setDecisions(snapshot.decisions.items || []);
    } catch (exception) {
      setError(exception.message || 'Unable to load hospital data.');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { load(); }, [season]);

  async function runScenario() {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const request = {
        season,
        arrival_multiplier: arrivals,
        bed_delta: bedDelta,
        discharge_extra: discharges,
        staff_delta: staffDelta,
        lab_delta: labDelta,
        radiology_delta: radiologyDelta,
      };
      const [simulation, suggestionResponse] = await Promise.all([
        call('/api/simulate', 'POST', request),
        call('/api/recommend', 'POST', request),
      ]);
      setResults(simulation);
      const sameSnapshot = simulation.snapshot_reference === suggestionResponse.snapshot_reference;
      setRecommendations(sameSnapshot ? suggestionResponse.recommendations || [] : []);
      setTab(NAV_ITEMS[4]);
      setNotice(sameSnapshot
        ? 'Scenario evaluated against the current synthetic snapshot. No live hospital resources were changed.'
        : 'The shared simulation advanced while this scenario was running. Results are tied to their snapshot; rerun to refresh recommendations.');
    } catch (exception) {
      setError(exception.message || 'Scenario could not be evaluated.');
    } finally {
      setBusy(false);
    }
  }

  async function advance() {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await call(`/api/advance?season=${season}`, 'POST');
      setResults(null);
      setRecommendations([]);
      setNotice('Simulation advanced by 15 minutes. Scenario results were cleared because they refer to the previous snapshot.');
      await load();
    } catch (exception) {
      setError(exception.message || 'Simulation could not advance.');
      setBusy(false);
    }
  }

  async function resetDemo() {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const seasonChanged = season !== 'normal';
      const resetStatus = await call('/api/reset', 'POST');
      setStatus(resetStatus);
      setResults(null);
      setRecommendations([]);
      setSeason('normal');
      setArrivals(1);
      setBedDelta(0);
      setDischarges(0);
      setStaffDelta(0);
      setLabDelta(0);
      setRadiologyDelta(0);
      setNotice('Demo state, clock, and in-memory decision log have been reset.');
      if (!seasonChanged) await load();
    } catch (exception) {
      setError(exception.message || 'Demo could not be reset.');
      setBusy(false);
    }
  }

  async function decide(action, approved, scenarioReference) {
    setBusy(true);
    setError('');
    try {
      await call('/api/decision', 'POST', {
        action, approved, operator: 'Demo operator', scenario_reference: scenarioReference || null,
      });
      setNotice(`Decision recorded as ${approved ? 'approved' : 'rejected'} in the demo log. No real-world action was executed.`);
      await load();
    } catch (exception) {
      setError(exception.message || 'Decision could not be recorded.');
      setBusy(false);
    }
  }

  const departments = status?.departments || [];
  const departmentById = Object.fromEntries(departments.map((department) => [department.id, department]));
  const resources = status?.resources;
  const inpatientBeds = resources?.beds;
  const filteredBeds = useMemo(() => {
    const bedDepartments = inpatientBeds?.departments || [];
    return departmentFilter === 'All Inpatient Departments'
      ? bedDepartments
      : bedDepartments.filter((item) => item.department === departmentFilter);
  }, [inpatientBeds, departmentFilter]);
  const bedSummary = filteredBeds.reduce((total, item) => ({
    physical: total.physical + item.physical,
    staffed: total.staffed + item.staffed,
    occupied: total.occupied + item.occupied,
    available: total.available + item.available_staffed,
  }), { physical: 0, staffed: 0, occupied: 0, available: 0 });
  const bedDonut = [
    { name: 'Occupied staffed beds', value: bedSummary.occupied, color: COLORS.occupied },
    { name: 'Available staffed beds', value: bedSummary.available, color: COLORS.available },
  ].filter((item) => item.value > 0);
  const overview = {
    occupancy: inpatientBeds?.staffed ? Math.round(inpatientBeds.occupied / inpatientBeds.staffed * 100) : 0,
    available: inpatientBeds?.available_staffed || 0,
    waiting: departmentById.Emergency?.waiting || 0,
    alertCount: bottlenecks?.bottlenecks?.length || 0,
  };
  const forecastData = (forecast?.intervals || []).map((item) => ({ ...item, label: formatAxisTime(item.time) }));
  const riskRows = departments.map((department) => {
    const projected = (bottlenecks?.timeline || []).reduce((peak, row) => {
      const value = department.id === 'Emergency' ? row.ed_waiting
        : department.id === 'ICU' ? row.icu_occupied + row.icu_boarding
          : department.id === 'Ward' ? row.ward_occupied + row.ward_boarding
            : department.id === 'Laboratory' ? row.lab_pending
              : row.radiology_pending;
      return Math.max(peak, value || 0);
    }, department.occupied);
    return { department, risk: riskFor(department.id, bottlenecks?.bottlenecks || []), projected };
  });
  const flowData = {
    arrivals: forecast?.expected_total_arrivals ?? 0,
    edWaiting: departmentById.Emergency?.waiting || 0,
    treatment: departmentById.Emergency?.occupied || 0,
    icu: departmentById.ICU?.waiting || 0,
    ward: departmentById.Ward?.waiting || 0,
    lab: departmentById.Laboratory?.waiting || 0,
    radiology: departmentById.Radiology?.waiting || 0,
    discharges: status?.discharged_in_demo || 0,
    projectedBoarding: bottlenecks?.metrics?.peak_ed_waiting || 0,
    projectedIcuBoarding: bottlenecks?.metrics?.peak_icu_boarding || 0,
    projectedWardBoarding: bottlenecks?.metrics?.peak_ward_boarding || 0,
  };
  const scenarioReference = results?.snapshot_reference || null;
  const currentScenarioRequest = {
    season, arrival_multiplier: arrivals, bed_delta: bedDelta, discharge_extra: discharges,
    staff_delta: staffDelta, lab_delta: labDelta, radiology_delta: radiologyDelta,
  };
  const scenarioResultsCurrent = Boolean(results
    && results.snapshot_reference === `step-${status?.clock_step ?? 'unknown'}`
    && Object.entries(currentScenarioRequest).every(([key, value]) => results.request?.[key] === value));
  const inpatientCapacityRows = (inpatientBeds?.departments || []).map((department) => {
    const projected = (bottlenecks?.timeline || []).reduce((peak, row) => {
      const occupancy = department.department === 'ICU' ? row.icu_occupied : row.ward_occupied;
      const boarding = department.department === 'ICU' ? row.icu_boarding : row.ward_boarding;
      return Math.max(peak, occupancy + boarding);
    }, department.occupied);
    const utilization = department.staffed ? Math.round(department.occupied / department.staffed * 100) : 0;
    const risk = riskFor(department.department, bottlenecks?.bottlenecks || []);
    return { ...department, utilization, projected, risk };
  });

  function evaluateResourceReallocation() {
    const icu = departmentById.ICU;
    const ward = departmentById.Ward;
    const lab = departmentById.Laboratory;
    const radiology = departmentById.Radiology;
    setBedDelta(icu && icu.physical_capacity > icu.capacity ? 1 : 0);
    setDischarges((icu?.waiting || 0) + (ward?.waiting || 0) > 0 ? 1 : 0);
    setLabDelta(lab && lab.waiting > lab.capacity ? 1 : 0);
    setRadiologyDelta(radiology && radiology.waiting > radiology.capacity ? 1 : 0);
    setStaffDelta(0);
    setArrivals(1);
    setResults(null);
    setRecommendations([]);
    setTab(NAV_ITEMS[4]);
    setNotice('Resource what-if controls were prepared from the current snapshot. Review and run the simulation; no resource has been reallocated.');
  }

  return (
    <div className={`app-shell${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
      <aside className="sidebar">
        <div className="brand-wrap">
          <div className="brand-mark"><Activity size={20} /></div>
          <div><div className="brand-title">HospAI</div><small>OPERATIONS PLATFORM</small></div>
        </div>
        <nav className="nav" aria-label="Main navigation">
          {NAV_ITEMS.map((item, index) => {
            const Icon = NAV_ICONS[index];
            return <button key={item} className={tab === item ? 'nav-item active' : 'nav-item'} onClick={() => setTab(item)} aria-current={tab === item ? 'page' : undefined} title={sidebarCollapsed ? item : undefined}>
              <Icon size={16} aria-hidden="true" /><span>{item}</span>
            </button>;
          })}
        </nav>
        <div className="sidebar-note"><ShieldCheck size={16} />Hospital Operational Dataset<span>hackathon_hospital_bottleneck_dataset.xlsx</span></div>
      </aside>

      <main className="content-area">
        <header className="topbar">
          <div>
            <button className="sidebar-toggle" onClick={() => setSidebarCollapsed((collapsed) => !collapsed)} aria-label={sidebarCollapsed ? 'Expand navigation' : 'Collapse navigation'} title={sidebarCollapsed ? 'Expand navigation' : 'Collapse navigation'}>
              {sidebarCollapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
            </button>
            <p className="eyebrow">PREDICTIVE HOSPITAL OPERATIONS</p>
            <h1>{tab}</h1>
            <div className="sim-time"><Clock3 size={14} />Simulated time: {status ? formatTime(status.timestamp) : 'Loading'}</div>
          </div>
          <div className="toolbar">
            <span className="badge">EXCEL DATASET ACTIVE</span>
            <button onClick={load} disabled={busy}><RefreshCw size={15} /> Refresh</button>
            <button className="primary" onClick={advance} disabled={busy}><Play size={15} /> +15 min</button>
            <button className="reset-button" onClick={resetDemo} disabled={busy}><RotateCcw size={15} /> Reset</button>
          </div>
        </header>
        {error && <div className="error-banner" role="alert">API error: {error}. Confirm the FastAPI service is running at {API}.</div>}
        {notice && <div className="notice-banner" role="status">{notice}</div>}
        {busy && !status ? <div className="card empty">Loading hospital data...</div> : null}
        {!status && !busy && !error ? <div className="card empty">No hospital snapshot is available.</div> : null}

        {status && <>
          {tab === NAV_ITEMS[0] && <OperationsDashboard overview={overview} inpatientBeds={inpatientBeds} departments={departments} bottlenecks={bottlenecks} forecast={forecast} forecastData={forecastData} setTab={setTab} />}
          {tab === NAV_ITEMS[1] && <ResourceCapacity inpatientBeds={inpatientBeds} resources={resources} departmentFilter={departmentFilter} setDepartmentFilter={setDepartmentFilter} highlight={highlight} setHighlight={setHighlight} bedDonut={bedDonut} bedSummary={bedSummary} inpatientCapacityRows={inpatientCapacityRows} departmentById={departmentById} evaluateResourceReallocation={evaluateResourceReallocation} />}
          {tab === NAV_ITEMS[2] && <BottleneckPrediction forecast={forecast} forecastData={forecastData} model={model} bottlenecks={bottlenecks} riskRows={riskRows} season={season} setSeason={setSeason} datasetInfo={datasetInfo} />}
          {tab === NAV_ITEMS[3] && <PatientFlow flowDepartment={flowDepartment} setFlowDepartment={setFlowDepartment} departments={departments} flowData={flowData} departmentById={departmentById} />}
          {tab === NAV_ITEMS[4] && <ScenarioLab season={season} setSeason={setSeason} arrivals={arrivals} setArrivals={setArrivals} bedDelta={bedDelta} setBedDelta={setBedDelta} discharges={discharges} setDischarges={setDischarges} staffDelta={staffDelta} setStaffDelta={setStaffDelta} labDelta={labDelta} setLabDelta={setLabDelta} radiologyDelta={radiologyDelta} setRadiologyDelta={setRadiologyDelta} busy={busy} runScenario={runScenario} setNotice={setNotice} results={results} scenarioResultsCurrent={scenarioResultsCurrent} scenarioReference={scenarioReference} recommendations={recommendations} decide={decide} decisions={decisions} />}
        </>}
      </main>
    </div>
  );
}
