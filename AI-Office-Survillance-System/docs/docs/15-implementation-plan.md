# 15 — Step-by-Step Implementation Plan (Office)

## Phase 0 — Compliance & setup (week 0)
- DPIA, employee consent flow, signage, retention policy. Provision repo, CI, registry.

## Phase 1 — MVP: attendance, one camera (weeks 1–4)
1. Stand up docker-compose (db schema, backend, dashboard).
2. Enroll a few employees (`POST /employees/{id}/enroll`).
3. Run `office_pipeline.py` on one entry camera → attendance events.
4. Dashboard: today's roster + work hours. **Exit criteria:** correct entry/exit for
   enrolled staff on one camera.

## Phase 2 — Beta: productivity + security + multi-cam (weeks 5–12)
5. Add behavior sampling + productivity_daily aggregation worker.
6. Add zones (desks/meeting rooms) and break detection.
7. Night intrusion + evidence clips + alert fan-out (push/SMS/WhatsApp/email).
8. Fine-tune + deploy fire/smoke/weapon model; add fall + violence.
9. Multi-camera per floor; Grafana dashboards; RBAC + audit log.

## Phase 3 — Production hardening (weeks 13–24)
10. Edge fleet (k3s/Balena), OTA model rollout, HA Postgres, backups.
11. Security: TLS/mTLS, secrets vault, pen-test, retention automation, erasure API.
12. Accuracy validation per class on-site; tune thresholds; sign-off.
13. Runbooks, on-call, SLOs, load test.

## Suggested team
1–2 CV/ML eng, 1 backend, 1 frontend (part-time), 1 DevOps (part-time). ~4–6 months.
