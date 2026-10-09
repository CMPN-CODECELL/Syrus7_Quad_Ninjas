import React from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import { Activity, AlertTriangle, BedDouble, BrainCircuit, Hospital, Users } from 'lucide-react';
import { StaffDonut } from '../components/charts/HospitalCharts';
import { DiagnosticCard, Progress, SectionHeader, StatCard } from '../components/ui/HospitalComponents';
import { COLORS } from '../constants/dashboard';

export default function ResourceCapacity({
  inpatientBeds, resources, departmentFilter, setDepartmentFilter, highlight, setHighlight,
  bedDonut, bedSummary, inpatientCapacityRows, departmentById, evaluateResourceReallocation,
}) {
  return <>
    <div className="stats-grid resource-kpis">
      <StatCard label="Total physical beds" value={inpatientBeds?.physical ?? '—'} detail="ICU + Ward beds" />
      <StatCard label="Staffed beds" value={inpatientBeds?.staffed ?? '—'} detail="Open for inpatient use" />
      <StatCard label="Occupied beds" value={inpatientBeds?.occupied ?? '—'} detail="Current inpatient count" />
      <StatCard label="Available staffed beds" value={inpatientBeds?.available_staffed ?? '—'} detail="Staffed less occupied" />
      <StatCard label="Doctors available" value={resources?.staffing?.available_doctors ?? '—'} detail="Synthetic staffing assumption" />
      <StatCard label="Nurses available" value={resources?.staffing?.available_nurses ?? '—'} detail="Synthetic staffing assumption" />
      <StatCard label="Pending lab tests" value={resources?.diagnostics?.laboratory?.pending ?? '—'} detail="Queue items" />
      <StatCard label="Pending radiology scans" value={resources?.diagnostics?.radiology?.pending ?? '—'} detail="Queue items" />
    </div>
    <div className="resource-layout">
      <section className="card panel">
        <SectionHeader title="Bed occupancy distribution" icon={<BedDouble size={17} />} />
        <div className="control-row"><label htmlFor="bed-filter">Department</label><select id="bed-filter" value={departmentFilter} onChange={(event) => { setDepartmentFilter(event.target.value); setHighlight(null); }}>
          <option>All Inpatient Departments</option><option>ICU</option><option>Ward</option>
        </select></div>
        {bedDonut.length ? <div className="donut-layout">
          <div className="donut-chart"><ResponsiveContainer width="100%" height="100%"><PieChart>
            <Pie data={bedDonut} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="88%" paddingAngle={3} onClick={(entry) => setHighlight(entry.name)}>
              {bedDonut.map((entry) => <Cell key={entry.name} fill={entry.color} opacity={highlight && highlight !== entry.name ? 0.35 : 1} />)}
            </Pie>
            <Tooltip formatter={(value, name) => [`${value} beds (${bedSummary.staffed ? Math.round(value / bedSummary.staffed * 100) : 0}%)`, name]} />
            <Legend verticalAlign="bottom" height={34} />
          </PieChart></ResponsiveContainer><div className="donut-center"><strong>{bedSummary.staffed ? Math.round(bedSummary.occupied / bedSummary.staffed * 100) : 0}%</strong><span>occupied</span></div></div>
          <div className="bed-breakdown">
            <button className={highlight === 'Occupied staffed beds' ? 'breakdown-item selected' : 'breakdown-item'} onClick={() => setHighlight('Occupied staffed beds')}><i style={{ background: COLORS.occupied }} /><span>Occupied</span><strong>{bedSummary.occupied}</strong></button>
            <button className={highlight === 'Available staffed beds' ? 'breakdown-item selected' : 'breakdown-item'} onClick={() => setHighlight('Available staffed beds')}><i style={{ background: COLORS.available }} /><span>Available</span><strong>{bedSummary.available}</strong></button>
            <div className="capacity-facts"><span>Physical beds<strong>{bedSummary.physical}</strong></span><span>Temporarily unavailable<strong>{Math.max(0, bedSummary.physical - bedSummary.staffed)}</strong></span><span>Staffed beds<strong>{bedSummary.staffed}</strong></span></div>
          </div>
        </div> : <p className="empty-text">No bed capacity data is available.</p>}
      </section>
      <section className="card panel">
        <SectionHeader title="Department capacity" icon={<Hospital size={17} />} aside="Current and projected" />
        <div className="capacity-grid">
          {inpatientCapacityRows.map((department) => <div key={department.department} className="capacity-card">
            <div className="row-between"><strong>{department.department}</strong><span className={`status-chip ${department.risk ? 'risk' : 'good'}`}>{department.risk?.severity || 'Within threshold'}</span></div>
            <Progress value={department.utilization} tone={department.risk ? 'warning' : 'good'} />
            <div className="capacity-detail-grid"><span>Physical<strong>{department.physical}</strong></span><span>Staffed<strong>{department.staffed}</strong></span><span>Occupied<strong>{department.occupied}</strong></span><span>Available<strong>{department.available_staffed}</strong></span></div>
            <small>{department.utilization}% utilized · projected peak occupancy + boarding: {department.projected}</small>
          </div>)}
        </div>
      </section>
    </div>
    <div className="resource-layout">
      <section className="card panel">
        <SectionHeader title="Staff availability" icon={<Users size={17} />} aside="Synthetic allocation assumption" />
        <div className="staff-summary"><StaffDonut title="Doctors" available={resources?.staffing?.available_doctors || 0} assigned={resources?.staffing?.assigned_doctors || 0} /><StaffDonut title="Nurses" available={resources?.staffing?.available_nurses || 0} assigned={resources?.staffing?.assigned_nurses || 0} /></div>
        <ResponsiveContainer width="100%" height={210}><BarChart data={resources?.staffing?.departments || []} margin={{ left: -16, right: 8, top: 12 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="department" tick={{ fontSize: 10 }} /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Bar dataKey="assigned_doctors" name="Doctors assigned" fill={COLORS.icu} radius={[4, 4, 0, 0]} /><Bar dataKey="assigned_nurses" name="Nurses assigned" fill={COLORS.occupied} radius={[4, 4, 0, 0]} />
        </BarChart></ResponsiveContainer>
      </section>
      <section className="card panel">
        <SectionHeader title="Diagnostic processing" icon={<Activity size={17} />} aside="Queues are not bed occupancy" />
        <div className="diagnostic-grid"><DiagnosticCard title="Laboratory" item={resources?.diagnostics?.laboratory} color={COLORS.lab} /><DiagnosticCard title="Radiology" item={resources?.diagnostics?.radiology} color={COLORS.radiology} /></div>
        <div className="queue-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={[
          { name: 'Laboratory', pending: resources?.diagnostics?.laboratory?.pending || 0, capacity: resources?.diagnostics?.laboratory?.processing_capacity_per_15m || 0 },
          { name: 'Radiology', pending: resources?.diagnostics?.radiology?.pending || 0, capacity: resources?.diagnostics?.radiology?.processing_capacity_per_15m || 0 },
        ]}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Bar dataKey="pending" name="Pending items" fill={COLORS.lab} /><Bar dataKey="capacity" name="Capacity per 15 min" fill={COLORS.icu} /></BarChart></ResponsiveContainer></div>
      </section>
    </div>
    <section className="card panel">
      <SectionHeader title="Resource allocation insights" icon={<AlertTriangle size={17} />} />
      <div className="insight-list">
        {inpatientCapacityRows.filter((item) => item.risk || item.utilization >= 85).map((item) => <div key={item.department}><strong>{item.department} approaching effective capacity</strong><span>{item.utilization}% occupied · projected {item.projected} including simulated boarding</span></div>)}
        {(resources?.diagnostics?.laboratory?.pending > resources?.diagnostics?.laboratory?.processing_capacity_per_15m) && <div><strong>Laboratory queue exceeds one interval of capacity</strong><span>{resources.diagnostics.laboratory.pending} pending · {resources.diagnostics.laboratory.processing_capacity_per_15m} processed per 15 min</span></div>}
        {(resources?.diagnostics?.radiology?.pending > resources?.diagnostics?.radiology?.processing_capacity_per_15m) && <div><strong>Radiology queue exceeds one interval of capacity</strong><span>{resources.diagnostics.radiology.pending} pending · {resources.diagnostics.radiology.processing_capacity_per_15m} processed per 15 min</span></div>}
        {((departmentById.ICU?.waiting || 0) + (departmentById.Ward?.waiting || 0) > 0) && <div><strong>Inpatient transfers pending</strong><span>ICU {departmentById.ICU?.waiting || 0} · Ward {departmentById.Ward?.waiting || 0} awaiting staffed beds</span></div>}
        {!inpatientCapacityRows.some((item) => item.risk || item.utilization >= 85) && <p className="empty-text">No inpatient department is currently at 85% occupancy or flagged by the simulated threshold model.</p>}
        <div className="synthetic-note">Staff and department allocation figures are fixed synthetic demo assumptions, not live rosters. Pending transfers are represented by ICU and Ward boarding counts.</div>
      </div>
      <button className="primary inline-action" onClick={evaluateResourceReallocation}><BrainCircuit size={15} />Evaluate Resource Reallocation</button>
    </section>
  </>;
}
