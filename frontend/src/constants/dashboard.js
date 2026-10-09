import {
  Activity, BedDouble, BrainCircuit, Hospital, LayoutDashboard, TrendingUp,
} from 'lucide-react';

export const NAV_ITEMS = [
  'Operations Dashboard',
  'Resource & Capacity Management',
  'Bottleneck Prediction',
  'Patient Flow',
  'AI Recommendations & Scenario Lab',
];

export const NAV_ICONS = [LayoutDashboard, BedDouble, TrendingUp, Hospital, BrainCircuit];

export const COLORS = {
  occupied: '#3b7f71',
  available: '#b9d6ce',
  emergency: '#df8756',
  icu: '#4c83c3',
  ward: '#65a48a',
  lab: '#d69c4d',
  radiology: '#8b83b8',
};
