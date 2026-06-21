# 05 — Security & Compliance (READ BEFORE DEPLOYING)

Projects 1 & 2 process **biometric identifiers** (faces). This is among the most
regulated categories of personal data. Treat the items below as **requirements**.

## Legal / regulatory
- **GDPR (EU/UK):** faces = special-category biometric data. Need a lawful basis,
  explicit consent (often), purpose limitation, retention limits, and a **DPIA**
  (Data Protection Impact Assessment) before go-live. Data-subject rights (access,
  erasure) must be technically supported.
- **BIPA (Illinois) & US state laws:** require **written consent** before collecting
  face geometry, a published retention/destruction schedule, and a ban on selling
  biometric data. Statutory damages are per-violation and have produced 9-figure
  settlements — do not skip consent.
- **Employee monitoring (Project 1):** many jurisdictions require notice, proportionality,
  works-council/union consultation, and prohibit covert monitoring. Productivity
  scoring of individuals can be unlawful or create liability — prefer **aggregate,
  role-level** analytics and disclose clearly.
- **Restaurant customers (Project 2):** prefer **anonymous** counting/dwell (no identity).
  If you do returning-customer recognition, you need signage + consent + opt-out, and
  should store only irreversible embeddings/hashes, never raw face galleries of the public.
- **CCTV signage & registration:** post notices; register with the local DPA where required.

## Privacy-by-design controls (build these in)
- **Edge-only raw frames:** faces/video processed on-site; only embeddings + metadata
  leave the edge by default. Make cloud upload of raw media opt-in per camera.
- **Consent + enrollment gating:** recognition only runs against **enrolled, consented**
  identities (employees). Unknown faces are *not* identified, only flagged as "unknown".
- **Retention & auto-deletion:** configurable TTL per data class (events vs clips vs
  embeddings); cron/job enforces destruction. Default short (e.g. clips 30–90 days).
- **Pseudonymization:** customers → rotating salted hashes, not durable IDs.
- **Right-to-erasure:** an API + admin action that purges a subject across DB + storage.
- **Redaction:** option to blur non-enrolled faces in stored/live media.

## Application & infrastructure security
- **AuthN:** OAuth2 + short-lived JWT (refresh rotation); optional SSO/Keycloak + MFA.
- **AuthZ:** RBAC roles — `admin`, `security`, `hr`/`manager`, `viewer` — least privilege.
  Audit log every sensitive read (who viewed which footage/identity, when).
- **Transport:** TLS 1.3 everywhere; edge→cloud over mTLS or VPN/WireGuard.
- **Secrets:** never in code; use env + Docker/K8s secrets or Vault. `.env` is gitignored.
- **Storage:** encrypt at rest (DB + object storage SSE); signed, expiring URLs for clips.
- **Network:** cameras on isolated VLAN; backend not exposed directly — reverse proxy
  (Traefik/Nginx) + WAF; rate limiting; CORS allowlist.
- **Hardening:** non-root containers, pinned base images, image scanning (Trivy),
  dependency scanning, SBOM, least-capability.
- **Edge device security:** disk encryption, secure boot where possible, no default
  passwords, automatic security updates, remote wipe via fleet manager.
- **Tamper/evidence integrity:** hash + timestamp evidence clips (chain-of-custody) for
  security investigations.

## Safety-detector responsibility
Fire/smoke/weapon/violence/fall/intrusion outputs are **decision-support**. Require
human verification before irreversible actions (e.g. calling authorities), log all
auto-actions, and provide an easy override. Validate detectors on-site; document
false-positive/negative rates.

## Compliance checklist (per deployment)
- [ ] DPIA completed & signed off  
- [ ] Lawful basis + consent flow live (employees/customers as applicable)  
- [ ] Signage posted; DPA registration (if required)  
- [ ] Retention schedule configured + automated deletion verified  
- [ ] RBAC + audit logging enabled  
- [ ] TLS/mTLS + encryption at rest verified  
- [ ] Erasure (right-to-be-forgotten) tested end-to-end  
- [ ] Pen-test / vuln scan passed before production
