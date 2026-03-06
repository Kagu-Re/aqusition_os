# Queue Overview

This file summarizes major horizon items and gives a coarse completeness %.

## Major items (Horizon)
| ID | Title | Status |
|---|---|---|
| P-20260201-0007 | Bulk operation runner (publish) | ✅ done |
| P-20260201-0008 | KPI normalization + export | ✅ done |
| P-20260201-0015 | validate-aliases + --aliases-path override | ✅ done |
| P-20260201-0016 | ops/checks runner | ✅ done |
| P-20260201-0017 | Bulk selectors + bulk validate/pause | ✅ done |
| P-20260201-0018 | bulk-run generic command | ✅ done |
| P-20260201-0022 | Operator Console v0 skeleton | ✅ done |
| P-20260201-0023 | Activity log stream | ✅ done |
| P-20260201-0024 | Preview + diff counters + validate gate | ✅ done |
| P-20260201-0025 | Lead intake + leads view | ✅ done |
| P-20260201-0026 | Lead outcome + revenue stats | ✅ done |
| P-20260201-0027 | Console UI: secret + lead outcome controls | ✅ done |
| P-20260201-0028 | Spend import + ROAS stats | ✅ done |
| P-20260201-0029 | Spend table + upsert/edit/delete | ✅ done |
| P-20260201-0030 | KPI window stats + daily series | ✅ done |
| P-20260201-0031 | KPI UI cards + presets + sparklines | ✅ done |
| P-20260201-0032 | Campaign intelligence scorecard | ✅ done |
| P-20260201-0033 | Budget simulator (what-if) | ✅ done |
| P-20260201-0034 | Alerts + thresholds engine | ✅ done |
| P-20260201-0035 | Playbooks (alerts → actions) | ✅ done |
| P-20260201-0036 | Notifier adapters (telegram/webhook/file) | ✅ done |
| P-20260201-0037 | Alert lifecycle (ack/resolve) | ✅ done |
| P-20260201-0019 | Operator Console v0 | ✅ done |
| P-20260201-0020 | Tailwind Static primary surface | ✅ done |
| P-20260201-0021 | Lead intake integration | ⬜ planned |
| P-20260201-0038 | Deployment hardening: require secret in prod | ✅ done |
| P-20260201-0039 | Deployment hardening: disable /lead db routing | ✅ done |
| P-20260201-0040 | Public surface guardrails: rate limit + payload caps | ✅ done |
| P-20260201-0041 | Health + smoke checks endpoint and script | ✅ done |
| P-20260201-0042 | Deployment artifacts: Dockerfile + compose OR systemd + nginx | ✅ done |
| P-20260201-0043 | Runbook: DEPLOYMENT.md (backup/restore, env, ops) | ✅ done |

## Completeness
- Done: 63
- Planned/Open: 0
- Deferred: 0 (major items)

**Queue completeness (done / (done + open)) = 63 / 63 = 100.00%**

## Client Onboarding

| ID | Item | Status |
|---|---|---|
| P-20260201-0050 | Client registry (DB + API + console page) | ✅ done |
| P-20260201-0051 | Onboarding templates (UTM policy + naming + event map) | ✅ done |
| P-20260201-0052 | “First 7 days” operator script (daily checks + decisions) | ⬜ open |


## Deployment Readiness

| ID | Item | Status |
|---|---|---|
| P-20260202-0001 | Deployment runbook (docs/DEPLOYMENT.md) | ✅ done |


## Ads Integration (Sim)

| ID | Item | Status |
|---|---|---|
| P-20260202-0003 | Ads adapter interface + deterministic stubs (meta/google) | ✅ done |


## Ads Data Plane

| ID | Item | Status |
|---|---|---|
| P-20260202-0004 | Wire ads simulate into DB (insert ad_stats + activity log) | ✅ done |


## Reporting

| ID | Item | Status |
|---|---|---|
| P-20260202-0005 | KPI report v1 (per-page totals + derived rates) | ✅ done |


## Guardrails

| ID | Item | Status |
|---|---|---|
| P-20260202-0006 | Diagnostics report v1 (tracking gaps + funnel friction) | ✅ done |


## Budget Control

| ID | Item | Status |
|---|---|---|
| P-20260202-0007 | Guardrails evaluate v1 (PASS/WARN/FAIL + actions) | ✅ done |


## Operations

| ID | Item | Status |
|---|---|---|
| P-20260202-0008 | Guardrails dashboard v1 (stoplight across clients) | ✅ done |


## Automation

| ID | Item | Status |
|---|---|---|
| P-20260202-0009 | Guardrails AutoPlan + time windows | ✅ done |


## Ops Automation

| ID | Item | Status |
|---|---|---|
| P-20260202-0009 | Autoplan v1 (findings -> checklist) + --window support | ✅ done |


## Ops Automation

| ID | Item | Status |
|---|---|---|
| P-20260202-0010 | AutoPlan → PATCH_QUEUE writer (deterministic IDs + dedup) | ✅ done |


## Ops Automation

| ID | Item | Status |
|---|---|---|
| P-20260202-0011 | PATCH_QUEUE → WORK_QUEUE promotion command | ✅ done |


## Ops Automation

| ID | Item | Status |
|---|---|---|
| P-20260202-0012 | WORK_QUEUE lifecycle commands (start/done) + LOG_HORIZON writes | ✅ done |


## Ops Automation

| ID | Item | Status |
|---|---|---|
| P-20260202-0013 | Ops macro: ops-run (autoplan→patch→work, optional start) | ✅ done |


## Ops Automation

| ID | Item | Status |
|---|---|---|
| P-20260202-0014 | WORK_QUEUE notes + blocked status with reasons | ✅ done |


## Ops Automation

| ID | Item | Status |
|---|---|---|
| P-20260202-0015 | WORK_QUEUE unblock/resume commands | ✅ done |


## Ops Automation

| ID | Item | Status |
|---|---|---|
| P-20260202-0016 | Visibility commands: work-list/work-show/ops-status | ✅ done |


## Ops Automation

| ID | Item | Status |
|---|---|---|
| P-20260202-0017 | Reporting: ops-report, work-stale, work-search | ✅ done |


## Ops Automation

| ID | Item | Status |
|---|---|---|
| P-20260202-0018 | Client snapshot: client-status | ✅ done |

| P-20260202-0019 | WORK_QUEUE schema v2: add client_id column + safe migration | ✅ done |

| P-20260202-0020 | Backfill client_id in WORK_QUEUE from PATCH_QUEUE | ✅ done |

| P-20260202-0021 | Enforce client_id in patch promotion + add work-validate | ✅ done |

| P-20260202-0022 | Deterministic autoplan patch_id seed (dedup stable) | ✅ done |

| P-20260202-0023 | Add work-fix (repair + validate + actionable list) | ✅ done |

| P-20260202-0024 | Add preflight gate + optional require-clean on work-start | ✅ done |

| P-20260202-0025 | Add preflight policy file + CI gate check in run_all | ✅ done |

| P-20260202-0026 | Add environment profiles (ENV.json + PREFLIGHT_PROFILES.json) + ae env command | ✅ done |

| P-20260202-0027 | Add capacity guardrails (caps) + ae capacity command | ✅ done |

| P-20260202-0028 | Flow + bottleneck analysis (ae flow, warnings, metrics history) | ✅ done |

| P-20260202-0029 | SLA policy + report (ae sla) + optional preflight blocking | ✅ done |

| P-20260202-0030 | SLA remediation utility (ae sla-plan -> SLA_PATCH_LIST.md) | ✅ done |

| P-20260202-0031 | Auto-emit SLA breaches into PATCH_QUEUE (ae sla-to-patch-queue) | ✅ done |

| P-20260202-0032 | Promote PATCH_QUEUE planned items into WORK_QUEUE (ae patch-to-work) | ✅ done |
