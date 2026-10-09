import React from 'react';

export function StatCard({ label, value, detail, warning = false }) {
  return <div className={`stat-card${warning ? ' warning' : ''}`}><small>{label}</small><strong>{value}</strong><span>{detail}</span></div>;
}

export function SectionHeader({ title, icon, aside }) {
  return <div className="section-header"><div className="section-title">{icon}<h2>{title}</h2></div>{aside && <span className="section-aside">{aside}</span>}</div>;
}

export function Progress({ value, tone = 'good' }) {
  return <div className="progress-track"><span className={`progress-fill ${tone}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>;
}

export function DiagnosticCard({ title, item, color }) {
  const pending = item?.pending || 0;
  const capacity = item?.processing_capacity_per_15m || 0;
  const pressure = capacity ? Math.min(100, pending / capacity * 100) : 0;
  return <div className="diagnostic-card"><div className="row-between"><strong>{title}</strong><i style={{ background: color }} /></div><div className="diagnostic-metrics"><span>Pending<strong>{pending}</strong></span><span>Completed<strong>{item?.completed_total ?? 0}</strong></span><span>New / 15m<strong>{item?.new_requests_last_15m ?? 0}</strong></span><span>Capacity / 15m<strong>{capacity}</strong></span></div><Progress value={pressure} tone={pressure >= 100 ? 'warning' : 'good'} /><small>{item?.estimated_backlog_intervals === null ? 'No throughput capacity' : `${item?.estimated_backlog_intervals ?? 0} processing intervals of backlog`}</small></div>;
}

export function RangeControl({ label, value, min, max, step = 1, suffix = '', onChange }) {
  return <label>{label}<input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} /><span className="range-value">{value > 0 && min < 0 ? '+' : ''}{value}{suffix}</span></label>;
}

export function FlowNode({ title, count, unit, highlighted }) {
  return <div className={`flow-node${highlighted ? ' highlighted' : ' dimmed'}`}><strong>{title}</strong><b>{count}</b><span>{unit}</span></div>;
}
