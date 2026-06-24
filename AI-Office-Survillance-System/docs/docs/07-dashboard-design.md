# 07 — Dashboard Design (Office)

React 18 + Vite + Tailwind, mobile-responsive (single-column < 768px). Recharts for
charts; live data over `/ws/live`. Grafana embedded for ops/BI deep-dives.

**Pages**
- **Live** — multi-camera grid (WebRTC/HLS), real-time event overlay, alert ticker,
  quick actions (acknowledge, trigger lights/alarm).
- **Attendance** — date picker, roster table (entry/exit/hours/status), CSV export,
  per-employee calendar.
- **Productivity** — score cards, ranking bar chart, activity breakdown (working/idle/
  phone/meeting), mobile-usage hours, day/zone heatmaps, weekly/monthly trends.
- **Security** — intrusion timeline, incident list + evidence clip player, visitor
  history, verify/false-alarm controls.
- **Admin** — employees + enrollment wizard, cameras + zone editor (draw polygons),
  users/RBAC, retention & consent settings.

Design system: rounded-2xl cards, neutral palette, severity colors (green/amber/red),
accessible (WCAG AA), dark-mode optional. Component lib in `dashboard/src/components`.
