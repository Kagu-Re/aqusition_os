# Acquisition & Operations Engine

## Pilot Operator Manual --- v1.1

------------------------------------------------------------------------

## 1. Purpose

This system manages the full service lifecycle:

**Ads / QR → Landing → Lead → Chat → Booking → Payment → SLA → Export →
Audit**

It enforces:

-   Operational discipline\
-   Financial integrity\
-   Traceability\
-   Governance\
-   Recovery from failures

This is an **operations platform**, not just software.

Designed for:

-   Local businesses\
-   Service providers\
-   NGOs\
-   Small agencies

Who need **control, transparency, and reliability**.

------------------------------------------------------------------------

## 2. System Overview

### End-to-End Flow

    Google/Meta Ads ─┐
    QR / Offline ────┼→ Landing Page → Lead → Chat → Booking → Payment → Export
                     │                    ↓
                     └────────────── Timeline
                                           ↓
                                      Governance
                                           ↓
                                      Reliability

------------------------------------------------------------------------

## 3. Requirements

-   Python 3.11+
-   SQLite3
-   Linux / macOS / Windows

------------------------------------------------------------------------

## 4. Installation

``` bash
git clone <repo_url>
cd acq_engine
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Initialize DB:

``` bash
python -m ae.db.init --db data.db
```

------------------------------------------------------------------------

## 5. Run Console

``` bash
python -m ae.console_app --db data.db
```

Open http://localhost:8000

------------------------------------------------------------------------

## 6. Pilot Checklist

### Step 1: Client Configuration ✓

**Status**: Ready to configure

**Quick Start**:
```bash
# Interactive configuration
python ops/scripts/pilot_client_config.py --db acq.db

# Or use CLI directly
python -m ae.cli create-client \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --name "CM Oldtown Plumbing" \
  --trade plumber \
  --city "chiang mai" \
  --phone "+66-80-000-0000" \
  --email "leads@example.com" \
  --service-area "Chiang Mai Old Town"

# Initialize onboarding templates
python -m ae.cli onboarding-init --db acq.db --client-id plumber-cm-oldtown
```

**Documentation**: See `docs/PILOT_CLIENT_CONFIGURATION.md` for detailed guide.

---

### Remaining Steps

□ Landing published\
□ Ads/QR tested\
□ Attribution verified\
□ Lead validated\
□ Chat linked\
□ Booking tested\
□ Payment tested\
□ Reconciliation tested\
□ SLA running\
□ Export scheduled\
□ Backup enabled

------------------------------------------------------------------------

# End of README
