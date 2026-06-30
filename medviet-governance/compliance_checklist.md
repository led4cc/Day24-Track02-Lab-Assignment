# NĐ13/2023 Compliance Checklist - MedViet AI Platform

## A. Data Localization
- [x] Tất cả patient data lưu trên servers đặt tại Việt Nam.
- [x] Backup cũng phải ở trong lãnh thổ Việt Nam.
- [x] Log việc transfer data ra ngoài nếu có.

Implementation:
- Primary database, object storage, and backup buckets are provisioned in Vietnam-hosted infrastructure.
- OPA policy blocks restricted data export when `destination_country != "VN"`.
- Any exceptional data transfer must create an audit event with requester, approver, destination, purpose, timestamp, and data classification.

## B. Explicit Consent
- [x] Thu thập consent trước khi dùng data cho AI training.
- [x] Có mechanism để user rút consent (Right to Erasure).
- [x] Lưu consent record với timestamp.

Implementation:
- Store consent records in a dedicated `consent_records` table keyed by `patient_id`.
- Each record includes purpose, consent status, collection channel, timestamp, and policy version.
- Training jobs must filter out patients with withdrawn or missing AI-training consent before dataset generation.
- Withdrawal requests trigger deletion or exclusion from downstream training datasets and future exports.

## C. Breach Notification (72h)
- [x] Có incident response plan.
- [x] Alert tự động khi phát hiện breach.
- [x] Quy trình báo cáo đến cơ quan có thẩm quyền trong 72h.

Implementation:
- Security alerts are routed to the on-call security owner and DPO.
- Incident runbook defines triage, containment, evidence collection, impact assessment, and notification steps.
- Breach clock starts when an incident is confirmed; notification package must be prepared within 72 hours.

## D. DPO Appointment
- [x] Đã bổ nhiệm Data Protection Officer.
- [x] DPO có thể liên hệ tại: dpo@medviet.example

Responsibilities:
- Review DPIA/data protection impact assessments for new AI use cases.
- Approve cross-border transfer exceptions.
- Own breach notification coordination and consent withdrawal escalation.

## E. Technical Controls
| NĐ13 Requirement | Technical Control | Status | Owner |
|------------------|-------------------|--------|-------|
| Data minimization | PII anonymization pipeline using Presidio custom recognizers for Vietnamese CCCD, phone, email, and person names | Done | AI Team |
| Access control | RBAC with Casbin for API permissions and ABAC with OPA for policy-level data access constraints | Done | Platform Team |
| Encryption | AES-256-GCM envelope encryption for sensitive fields; TLS 1.3 required for service-to-service traffic | Done | Infra Team |
| Audit logging | Structured API audit logs for authentication, authorization decisions, data reads/deletes, exports, and admin actions | Planned | Platform Team |
| Breach detection | Prometheus/Grafana monitoring plus alert rules for suspicious access patterns and failed authorization spikes | Planned | Security Team |

## F. Technical Solutions For Planned Controls

### Audit Logging
- Add FastAPI middleware to emit one JSON audit event per request.
- Log fields: `request_id`, `timestamp`, `user`, `role`, `method`, `path`, `resource`, `action`, `decision`, `status_code`, `client_ip`, and `latency_ms`.
- Log RBAC/OPA denials explicitly with the denied resource and action.
- Store logs in append-only storage with retention policy of at least 12 months.
- Mask or hash direct PII in logs; never log raw CCCD, phone, plaintext tokens, or encryption keys.
- Add daily integrity checks for audit log files or object storage prefixes.

### Breach Detection
- Export API metrics to Prometheus: request count, status code count, 401/403 count, delete attempts, export attempts, and latency.
- Create Grafana dashboards for authentication failures, access denials, admin actions, and unusual data-read volume.
- Add alert rules for:
  - More than 10 failed auth attempts from one IP in 5 minutes.
  - More than 5 denied access attempts by one user in 10 minutes.
  - Any restricted-data export attempt to a non-VN destination.
  - Any spike in raw patient-data reads outside business hours.
- Route critical alerts to Security Team and DPO.
- Link each alert to an incident response playbook with 72-hour notification checkpoints.

## G. Evidence
- PII detection/anonymization tests: `pytest tests/test_pii.py -q`.
- RBAC behavior verified with API curl tests for `token-alice`, `token-bob`, `token-carol`, and `token-dave`.
- Envelope encryption round-trip verified with `SimpleVault.encrypt_data()` and `SimpleVault.decrypt_data()`.
- OPA policy tested with `opa eval` for admin, ML engineer, data analyst, intern, and restricted export cases.
- Pre-commit security hook blocks fake AWS credentials through `git-secrets`.
