# 06 — API Design (Tennis)
Base `/api/v1`. JWT for users; bearer token for edge. OpenAPI at `/docs`.
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/matches` | create a match (best_of) |
| GET | `/matches/{id}/score` | current live score |
| POST | `/matches/{id}/point` | award a point (manual or auto from rally end) |
| POST | `/matches/{id}/call` | edge → line call (in/out/close) |
| POST | `/ingest/events` | ball/player/line-call time-series |
| GET | `/matches/{id}/stats` | rally count, serve speed, winners, errors |
| GET | `/players/{id}/analytics` | speed, distance, heatmap, shot distribution |
| GET | `/matches/{id}/highlights` | aces, winners, long rallies |
| WS | `/ws/match/{id}` | live score + line-call stream |
