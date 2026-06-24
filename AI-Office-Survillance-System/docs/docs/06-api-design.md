# 06 — API Design (Office)

Base: `/api/v1`. Auth: OAuth2 password → JWT (Bearer). Edge ingest uses a static
bearer token. All times ISO-8601 UTC. Full OpenAPI at `/docs`.

| Method | Path | Role | Purpose |
|--------|------|------|---------|
| POST | `/auth/login` | – | obtain JWT |
| POST | `/ingest/events` | edge token | event ingest (edge→backend) |
| GET/POST | `/employees` | hr/admin | list / create employees |
| POST | `/employees/{id}/enroll` | hr/admin | upload face image(s) → ArcFace embedding |
| DELETE | `/employees/{id}` | admin | deactivate |
| GET | `/attendance?work_date=` | hr/security | roster + work hours |
| GET | `/productivity/daily?work_date=` | hr | scores + ranking |
| GET | `/productivity/{emp}/trend?range=` | hr | weekly/monthly trend |
| GET | `/security/incidents?status=` | security | intrusion/safety incidents |
| POST | `/security/incidents/{id}/verify` | security | confirm / mark false alarm |
| GET | `/security/incidents/{id}/clip` | security | signed evidence URL (audited) |
| GET | `/cameras` / `GET /cameras/{id}/stream` | viewer+ | list / live feed (WebRTC/HLS) |
| POST | `/subjects/{id}/erase` | admin | GDPR right-to-erasure |
| WS | `/ws/live` | token | live events + alerts |

Conventions: cursor pagination (`?limit=&cursor=`), `4xx` problem+json errors, rate
limiting on auth + ingest, idempotent ingest via `event_id`.
