import React from 'react';
import { BrainCircuit, Clock3, Play, RotateCcw, ShieldCheck } from 'lucide-react';
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { SectionHeader, RangeControl } from '../components/ui/HospitalComponents';
import { COLORS } from '../constants/dashboard';

export default function ScenarioLab({
  season, setSeason, arrivals, setArrivals, bedDelta, setBedDelta,
  discharges, setDischarges, staffDelta, setStaffDelta, labDelta, setLabDelta,
  radiologyDelta, setRadiologyDelta, busy, runScenario, setNotice, results,
  scenarioResultsCurrent, scenarioReference, recommendations, decide, decisions,
}) {
  function resetScenario() {
    setSeason('normal');
    setArrivals(1);
    setBedDelta(0);
    setDischarges(0);
    setStaffDelta(0);
    setLabDelta(0);
    setRadiologyDelta(0);
    setNotice('Scenario controls reset to baseline values.');
  }

  return <>
    <section className="card panel">
      <SectionHeader title="What-if simulation" icon={<BrainCircuit size={17} />} aside="Scenario runs do not mutate current state" />
      <div className="form-grid">
        <label className="scenario-season">Seasonal demand<select value={season} onChange={(event) => setSeason(event.target.value)}><option value="normal">Normal</option><option value="monsoon">Monsoon</option><option value="flu">Flu season</option><option value="outbreak">Outbreak (stress case)</option></select></label>
        <RangeControl label="Arrival multiplier" value={arrivals} min={0.25} max={3} step={0.05} suffix="×" onChange={setArrivals} />
        <RangeControl label="ICU staffed-bed delta" value={bedDelta} min={-10} max={4} onChange={setBedDelta} />
        <RangeControl label="Discharge throughput uplift" value={discharges} min={0} max={3} onChange={setDischarges} />
        <RangeControl label="Staff delta (2 staff per bed equivalent)" value={staffDelta} min={-8} max={8} onChange={setStaffDelta} />
        <RangeControl label="Lab processing delta / 15 min" value={labDelta} min={-8} max={8} onChange={setLabDelta} />
        <RangeControl label="Radiology processing delta / 15 min" value={radiologyDelta} min={-3} max={5} onChange={setRadiologyDelta} />
      </div>
      <div className="scenario-actions"><button className="primary" onClick={runScenario} disabled={busy}><Play size={15} />Run Simulation</button><button onClick={resetScenario} disabled={busy}><RotateCcw size={15} />Reset Scenario</button></div>
      {results && !scenarioResultsCurrent && <div className="notice-banner">Scenario controls changed after the last run. Run Simulation again to refresh the comparison and recommendations.</div>}
      {scenarioResultsCurrent && <>
        <div className="scenario-context"><strong>Snapshot {scenarioReference}</strong><span>{results.note}</span></div>
        <div className="comparison-table-wrap"><table className="data-table"><thead><tr><th>Outcome over 4h</th><th>Baseline</th><th>Scenario</th><th>Change</th></tr></thead><tbody>
          {[['ICU peak boarding','peak_icu_boarding'],['Ward peak boarding','peak_ward_boarding'],['Emergency peak waiting','peak_ed_waiting'],['Lab peak pending','peak_lab_pending'],['Radiology peak pending','peak_radiology_pending']].map(([label,key]) => { const change = results.scenario.metrics[key] - results.baseline.metrics[key]; return <tr key={key}><td>{label}</td><td>{results.baseline.metrics[key]}</td><td>{results.scenario.metrics[key]}</td><td><strong className={`delta-value ${change < 0 ? 'improved' : change > 0 ? 'worsened' : 'unchanged'}`}>{change > 0 ? '+' : ''}{change}</strong></td></tr>; })}
        </tbody></table></div>
        <div className="comparison-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={results.baseline.timeline.map((row,index) => ({ interval: `${(index+1)*15}m`, baseline: row.icu_boarding, scenario: results.scenario.timeline[index]?.icu_boarding || 0 }))}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="interval" interval={3} /><YAxis allowDecimals={false} label={{ value: 'ICU boarding (patients)', angle: -90, position: 'insideLeft' }} /><Tooltip /><Legend /><Line dataKey="baseline" name="Baseline ICU boarding" stroke={COLORS.icu} strokeWidth={2} dot={false} /><Line dataKey="scenario" name="Scenario ICU boarding" stroke={COLORS.emergency} strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div>
        {results.scenario.bottlenecks.length ? <div className="alert-row"><strong>Feasibility / pressure warning</strong><p>{results.scenario.bottlenecks.map((risk) => `${risk.department}: ${risk.reason}`).join(' ')}</p></div> : <div className="notice-banner">No configured bottleneck threshold was crossed in this scenario horizon.</div>}
      </>}
    </section>
    <section className="card panel">
      <SectionHeader title="AI action center" icon={<ShieldCheck size={17} />} aside="Simulated proposals require human review" />
      {scenarioResultsCurrent && recommendations.length ? recommendations.map((item) => <div className="recommendation-card" key={item.action}>
        <div className="row-between"><div><span className="eyebrow">{item.priority} · {item.department}</span><strong>{item.action}</strong></div><span className="pill">Score {item.modeled_score_improvement}</span></div>
        <p>{item.expected_benefit}</p><small>{item.feasibility_conditions}</small>
        <div className="decision-actions"><button className="primary" onClick={() => decide(item.action,true,scenarioReference)} disabled={busy}>Approve for demo log</button><button onClick={() => decide(item.action,false,scenarioReference)} disabled={busy}>Reject</button></div>
      </div>) : <p className="empty-text">Run the scenario model to generate proposals from simulated outcomes.</p>}
    </section>
    <section className="card panel">
      <SectionHeader title="Decision log" icon={<Clock3 size={17} />} aside="In-memory demo records" />
      {decisions.length ? decisions.slice().reverse().map((item) => <div className="decision-row" key={item.id}><span>#{item.id}</span><strong>{item.action}</strong><span>{item.scenario_reference || 'No scenario reference'}</span><time>{new Date(item.timestamp).toLocaleString()}</time><span className={item.approved ? 'status ok' : 'status warn'}>{item.approved ? 'Approved · not executed' : 'Rejected'}</span></div>) : <p className="empty-text">No decisions have been recorded.</p>}
    </section>
  </>;
}
