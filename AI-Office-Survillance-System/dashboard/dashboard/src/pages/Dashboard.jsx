import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { api, liveSocket } from "../lib/api";

// Mobile-responsive office overview: attendance, productivity ranking, live alerts.
export default function Dashboard() {
  const [attendance, setAttendance] = useState([]);
  const [ranking, setRanking] = useState([]);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    api("/api/v1/attendance").then((d) => setAttendance(d.rows)).catch(() => {});
    api("/api/v1/productivity/daily").then((d) => setRanking(d.ranking)).catch(() => {});
    const ws = liveSocket((m) => setAlerts((a) => [m, ...a].slice(0, 50)));
    return () => ws.close();
  }, []);

  return (
    <div className="p-4 md:p-8 grid gap-6 md:grid-cols-2 max-w-7xl mx-auto">
      <header className="md:col-span-2 flex items-center justify-between">
        <h1 className="text-2xl font-bold">AI Office Surveillance</h1>
        <span className="text-sm text-gray-500">{new Date().toLocaleString()}</span>
      </header>

      <section className="bg-white rounded-2xl shadow p-4">
        <h2 className="font-semibold mb-2">Today&apos;s Attendance</h2>
        <ul className="divide-y text-sm max-h-64 overflow-auto">
          {attendance.map((r) => (
            <li key={r.employee_id} className="py-2 flex justify-between">
              <span>{r.full_name}</span>
              <span className={r.status === "late" ? "text-amber-600" : "text-green-600"}>
                {r.status} · {(r.work_seconds/3600).toFixed(1)}h
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="bg-white rounded-2xl shadow p-4">
        <h2 className="font-semibold mb-2">Productivity Ranking</h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={ranking.slice(0, 10)}>
            <XAxis dataKey="full_name" hide /><YAxis domain={[0, 100]} />
            <Tooltip /><Bar dataKey="productivity_score" />
          </BarChart>
        </ResponsiveContainer>
      </section>

      <section className="md:col-span-2 bg-white rounded-2xl shadow p-4">
        <h2 className="font-semibold mb-2">Live Security Alerts</h2>
        <ul className="text-sm space-y-1 max-h-48 overflow-auto">
          {alerts.length === 0 && <li className="text-gray-400">No alerts.</li>}
          {alerts.map((a, i) => (
            <li key={i} className="text-red-600">⚠ {a.type} · {a.camera_id} · {a.ts}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
