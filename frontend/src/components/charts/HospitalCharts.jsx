import React from 'react';
import {
  Area, AreaChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { COLORS } from '../../constants/dashboard';

export function ForecastChart({ data }) {
  if (!data?.length) return <div className="chart-empty">No forecast intervals available.</div>;
  return <div className="chart-wrap" role="img" aria-label="Four-hour expected emergency arrivals forecast, shown in 15-minute intervals"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -14 }}>
    <defs><linearGradient id="arrivalFill" x1="0" x2="0" y1="0" y2="1"><stop offset="5%" stopColor={COLORS.occupied} stopOpacity={0.3} /><stop offset="95%" stopColor={COLORS.occupied} stopOpacity={0.02} /></linearGradient></defs>
    <CartesianGrid strokeDasharray="3 3" stroke="#e7eeeb" /><XAxis dataKey="label" tick={{ fontSize: 10 }} interval={3} /><YAxis allowDecimals={false} label={{ value: 'Expected patients / 15 min', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fontSize: 10 } }} /><Tooltip formatter={(value) => [`${value} expected patients`, 'Arrivals']} /><Legend /><Area type="monotone" dataKey="expected_arrivals" name="Expected arrivals" stroke={COLORS.occupied} fill="url(#arrivalFill)" strokeWidth={2} activeDot={{ r: 5 }} />
  </AreaChart></ResponsiveContainer></div>;
}

export function StaffDonut({ title, available, assigned }) {
  const data = [{ name: 'Available', value: available, color: COLORS.available }, { name: 'Assigned', value: assigned, color: COLORS.occupied }];
  return <div className="staff-donut"><strong>{title}</strong><div><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data} dataKey="value" nameKey="name" innerRadius="60%" outerRadius="86%"><Cell fill={COLORS.available} /><Cell fill={COLORS.occupied} /></Pie><Tooltip formatter={(value, name) => [`${value} people`, name]} /></PieChart></ResponsiveContainer><span>{available} available</span></div><small>{assigned} assigned · {available + assigned} total</small></div>;
}
