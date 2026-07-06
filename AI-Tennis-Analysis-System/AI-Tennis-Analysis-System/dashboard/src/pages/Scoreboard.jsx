import { useEffect, useState } from "react";
const API = import.meta.env.VITE_API ?? "http://localhost:8003";

// Spectator scoreboard with live score + line-call ticker over WebSocket.
export default function Scoreboard({ matchId = "demo" }) {
  const [score, setScore] = useState(null);
  const [calls, setCalls] = useState([]);
  useEffect(() => {
    const ws = new WebSocket(`${API.replace("http","ws")}/api/v1/ws/match/${matchId}`);
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.type === "call") setCalls((c) => [m, ...c].slice(0, 20));
      else setScore(m);
    };
    return () => ws.close();
  }, [matchId]);
  return (
    <div className="p-4 md:p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Match {matchId}</h1>
      {score ? (
        <div className="bg-black text-white rounded-2xl p-6 grid grid-cols-3 gap-2 text-center">
          <div className="text-left col-span-1">
            <div className={score.server==="a"?"font-bold":""}>Player A {score.server==="a"?"•":""}</div>
            <div className={score.server==="b"?"font-bold":""}>Player B {score.server==="b"?"•":""}</div>
          </div>
          <div className="col-span-1">
            <div className="text-xs opacity-60">SETS / GAMES</div>
            <div>{score.sets[0]} · {score.games[0]}</div>
            <div>{score.sets[1]} · {score.games[1]}</div>
          </div>
          <div className="col-span-1">
            <div className="text-xs opacity-60">POINTS</div>
            <div className="text-3xl font-mono">{score.points}</div>
          </div>
          {score.finished && <div className="col-span-3 text-green-400 font-bold mt-2">
            Winner: Player {score.winner.toUpperCase()}</div>}
        </div>
      ) : <p className="text-gray-500">Waiting for match…</p>}
      <h2 className="font-semibold mt-6 mb-2">Line calls</h2>
      <ul className="text-sm space-y-1">
        {calls.map((c,i)=>(<li key={i} className={c.call==="out"?"text-red-600":"text-green-700"}>
          {c.call.toUpperCase()} · margin {c.margin_cm}cm {c.close?"· CLOSE (review)":""}</li>))}
      </ul>
    </div>
  );
}
