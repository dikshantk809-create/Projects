const BASE = import.meta.env.VITE_API ?? "http://localhost:8001";
// Demo fallback token (role=admin) so the dashboard renders seeded data without a login UI.
const DEMO_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZW1vLWFkbWluIiwicm9sZSI6ImFkbWluIiwiZXhwIjoyMDk3NDA0NjA2fQ.STqimnH6rRIc7Zvji9MpXuV_JlyBE_lP_zAdRGvxw8A";
export async function api(path, opts = {}) {
  const token = localStorage.getItem("token") || DEMO_TOKEN;
  const r = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json",
               ...(token ? { Authorization: `Bearer ${token}` } : {}), ...opts.headers },
  });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}
export function liveSocket(onMsg) {
  const ws = new WebSocket((BASE.replace("http", "ws")) + "/ws/live");
  ws.onmessage = (e) => onMsg(JSON.parse(e.data));
  return ws;
}
