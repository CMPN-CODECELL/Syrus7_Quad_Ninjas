import React from 'react';
import { Hospital, TrendingUp } from 'lucide-react';
import { FlowNode, SectionHeader } from '../components/ui/HospitalComponents';

export default function PatientFlow({ flowDepartment, setFlowDepartment, departments, flowData, departmentById }) {
  return <>
    <section className="card panel">
      <SectionHeader title="Branching patient flow" icon={<Hospital size={17} />} aside="Current queues with four-hour simulated demand" />
      <div className="control-row"><label htmlFor="flow-filter">Highlight department</label><select id="flow-filter" value={flowDepartment} onChange={(event) => setFlowDepartment(event.target.value)}><option>All</option>{departments.map((item) => <option key={item.id}>{item.id}</option>)}</select></div>
      <div className="branch-flow">
        <FlowNode title="Arrivals" count={flowData.arrivals} unit="expected patients / 4h" highlighted={flowDepartment === 'All' || flowDepartment === 'Emergency'} />
        <div className="flow-connector"><span>→ {flowData.edWaiting} waiting</span></div>
        <FlowNode title="Emergency" count={flowData.treatment} unit={`in treatment · ${flowData.edWaiting} waiting`} highlighted={flowDepartment === 'All' || flowDepartment === 'Emergency'} />
        <div className="flow-branches">
          <div className="flow-branch"><span className="branch-label">Treatment complete · modeled routing</span><div className="flow-branch-destinations">
            <FlowNode title="Discharge" count={flowData.discharges} unit="completed in demo" highlighted={flowDepartment === 'All'} />
            <FlowNode title="ICU" count={flowData.icu} unit={`${departmentById.ICU?.occupied || 0} occupied · boarding`} highlighted={flowDepartment === 'All' || flowDepartment === 'ICU'} />
            <FlowNode title="Ward" count={flowData.ward} unit={`${departmentById.Ward?.occupied || 0} occupied · boarding`} highlighted={flowDepartment === 'All' || flowDepartment === 'Ward'} />
          </div></div>
        </div>
        <div className="diagnostic-dependencies">
          <span>Diagnostic dependencies (parallel, not sequential)</span>
          <div className="flow-branch-destinations">
            <FlowNode title="Laboratory" count={flowData.lab} unit="pending tests" highlighted={flowDepartment === 'All' || flowDepartment === 'Laboratory'} />
            <FlowNode title="Radiology" count={flowData.radiology} unit="pending scans" highlighted={flowDepartment === 'All' || flowDepartment === 'Radiology'} />
          </div>
        </div>
      </div>
    </section>
    <section className="card panel">
      <SectionHeader title="Downstream impact" icon={<TrendingUp size={17} />} aside="Current snapshot vs simulated horizon" />
      <div className="impact-grid"><div><small>Emergency queue now</small><strong>{flowData.edWaiting}</strong><span>patients</span></div><div><small>Peak emergency queue</small><strong>{flowData.projectedBoarding}</strong><span>patients within 4h</span></div><div><small>Peak ICU boarding</small><strong>{flowData.projectedIcuBoarding}</strong><span>patients within 4h</span></div><div><small>Peak Ward boarding</small><strong>{flowData.projectedWardBoarding}</strong><span>patients within 4h</span></div></div>
      <div className="chart-note">Flow counts combine the current backend snapshot with a deterministic synthetic simulation; the engine exposes aggregate counts, not individual patient pathways. Lab and Radiology queues are independent diagnostic dependencies.</div>
    </section>
  </>;
}
