export function formatTime(value) {
  if (!value) return 'Time unavailable';
  return new Date(value).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export function formatAxisTime(value) {
  if (!value) return '';
  return new Date(value).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

export function riskFor(department, risks) {
  return risks.find((item) => item.department.toLowerCase() === department.toLowerCase());
}
