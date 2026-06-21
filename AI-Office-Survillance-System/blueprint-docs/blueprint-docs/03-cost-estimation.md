# 03 — Cost Estimation

Two cost views: **(A)** one-time + recurring infra per deployment, and **(B)**
build/engineering cost. All figures 2026 USD, planning-grade.

## A. Deployment cost (per customer site)

### Tier A — Raspberry Pi edge (small site)
| Bucket | One-time | Monthly |
|--------|---------:|--------:|
| Edge hardware (Pi5 + Hailo + cam + SSD + UPS) | $350–450 | — |
| Server (small cloud VM 4 vCPU/8 GB, or on-prem mini-PC) | $0–500 | $25–60 |
| Object storage (clips, ~50–200 GB) | — | $5–20 |
| Notifications (Twilio SMS/WhatsApp + FCM) | — | $5–40 (usage) |
| Domain/TLS, monitoring | — | $0–15 |
| **Total** | **~$400–950** | **~$40–135/mo** |

### Tier B — Jetson multi-camera site
| Bucket | One-time | Monthly |
|--------|---------:|--------:|
| Jetson + 6–12 cams + switch + UPS + SSD | $1.5k–3k | — |
| Server/cluster share | — | $80–200 |
| Storage (0.5–2 TB clips) | — | $20–80 |
| Notifications | — | $20–100 |
| **Total** | **~$1.5k–3k** | **~$120–380/mo** |

### Tier C — Enterprise GPU server (many streams / tennis venue)
| Bucket | One-time | Monthly |
|--------|---------:|--------:|
| GPU server + cameras + network + UPS | $10k–30k | — |
| Cloud GPU alternative (rent) | — | $400–1,500 |
| Storage 50–100 TB tiered | — | $150–600 |
| **Total** | **~$10k–30k** or rent | **~$600–2,500/mo** |

## B. Cloud cost drivers (rule of thumb)
- **Inference at the edge ≈ \$0 marginal cloud GPU.** This is the biggest saving vs.
  streaming all video to a cloud model.
- **Storage** dominates recurring cost: 1080p H.265 ≈ 1–2 GB/camera/day continuous;
  use **event-triggered clip recording** (pre/post-roll) to cut this 10–50×.
- **Notifications:** WhatsApp/SMS are per-message; push (FCM) is effectively free.
  Throttle + batch to control spend.
- Use **TimescaleDB retention + continuous aggregates** to keep the hot DB small;
  downsample raw events after 30–90 days.

## C. Engineering / build cost (to take one project to production)
| Phase | Effort (1–2 eng) | Indicative cost @ blended \$60–120/hr |
|-------|------------------|--------------------------------------|
| MVP (single camera, core pipeline + minimal dashboard) | 4–6 weeks | \$15k–45k |
| Beta (multi-cam, full analytics, alerts, auth, Grafana) | 6–10 weeks | \$25k–80k |
| Production hardening (fleet, HA, security, compliance, accuracy validation) | 8–12 weeks | \$35k–110k |
| **Per project total** | **~4–7 months** | **~\$75k–235k** |

Building all three on the shared platform is **far cheaper than 3×** because the
platform layer (≈60–70% of code) is reused. Realistic blended estimate for all three
to production: **~9–15 months** with a 2–3 person team, not 3× a single project.

## D. Unit economics example (Restaurant SaaS)
- Cost to serve one site (Tier A): ~\$60–120/mo infra + support.
- Target price: \$99–299/mo per location → healthy gross margin once support is
  productized. Hardware sold/leased separately (\$400–600 kit).
