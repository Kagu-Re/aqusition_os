# How Onboarding Works

## Overview

The onboarding system establishes **operational guardrails** and **measurement vocabulary** for each client. It's designed to prevent data entropy and ensure consistent attribution across all channels (Meta, Google, organic, QR codes).

## Core Concept

**Onboarding templates** are client-specific documents that define:
1. **UTM Policy** - How to structure UTM parameters for attribution
2. **Naming Policy** - Conventions for IDs, slugs, and campaign names
3. **Event Map** - What events to track and their definitions

These templates serve as the **single source of truth (SSOT)** for how you measure and attribute traffic, leads, and conversions.

## Why It Matters

Without consistent onboarding:
- ❌ UTM parameters vary across campaigns → attribution breaks
- ❌ Campaign names change mid-flight → historical data becomes unreliable
- ❌ Events fire inconsistently → funnel metrics are meaningless
- ❌ Different naming conventions → data reconciliation fails

With proper onboarding:
- ✅ Consistent attribution across all channels
- ✅ Reliable historical data for decision-making
- ✅ Clear funnel metrics (CTR → CVR → booking rate)
- ✅ Auditable campaign performance

## The Three Templates

### 1. UTM Policy (`utm_policy_md`)

**Purpose**: Define how UTM parameters are structured for consistent attribution.

**Key Rules**:
- `utm_source`: Platform (`meta`, `google`, `tiktok`, `organic`, `referral`)
- `utm_medium`: Traffic type (`paid`, `organic`, `referral`, `email`, `social`)
- `utm_campaign`: **Stable** campaign slug (lowercase, dash-separated)
- `utm_content`: Creative/ad variant identifier
- `utm_term`: Keyword (Google) or audience segment (Meta)

**Critical Rule**: **Never change `utm_campaign` mid-flight**. Create a new campaign key instead.

**Example**:
```
?utm_source=google&utm_medium=paid&utm_campaign=plumber-cm-oldtown-feb&utm_content=headline-a&utm_term=plumber-near-me
```

### 2. Naming Policy (`naming_policy_md`)

**Purpose**: Prevent data entropy through consistent naming conventions.

**Key Objects**:
- `client_id`: Stable identifier (e.g., `plumber-cm-oldtown`)
- `page_id`: Stable slug (e.g., `p-plumber-cm-oldtown-v1`)
- `campaign_id`: Stable slug (e.g., `c-plumber-cm-search-v1`)

**Conventions**:
- Lowercase, dash-separated
- Include geo when it matters (city/area)
- Avoid dates in IDs unless time-boxed
- Recommended prefixes: `p-` (pages), `c-` (campaigns), `a-` (alerts)

**Why**: Consistent naming makes it easy to:
- Query historical data
- Reconcile reports across platforms
- Audit campaign performance
- Debug attribution issues

### 3. Event Map (`event_map_md`)

**Purpose**: Define what events to track and their meanings.

**Core Events**:
1. `page_view` - Page load
2. `view_content` - User engaged (scrolled, viewed pricing)
3. `generate_lead` - Form submit, WhatsApp click, call click
4. `booking` - Appointment confirmed / deposit / calendar

**Properties** (non-PII):
- `page_id`, `client_id`, `offer_id` (if relevant)
- `channel` (meta/google/organic/referral)
- `value_bucket` (low|mid|high) - optional

**Why**: Consistent events enable:
- Reliable funnel metrics
- Cross-platform comparison
- A/B testing validity
- Performance optimization

## Workflow

### Step 1: Create Client

When you create a client, the system stores basic information:
- Client ID, name, trade, geo, contact info
- Service areas, status, optional metadata

### Step 2: Initialize Templates

**Automatic**: When you access onboarding templates for a client, the system automatically ensures default templates exist via `ensure_default_onboarding_templates()`.

**Manual**: You can also initialize explicitly:
```bash
python -m ae.cli onboarding-init --db acq.db --client-id plumber-cm-oldtown
```

This creates three default templates with best-practice content.

### Step 3: Customize Templates

**Via Console UI** (Recommended):
1. Navigate to: `http://localhost:8000/console/onboarding?client_id=plumber-cm-oldtown`
2. Review the three templates
3. Customize them for your client's specific needs
4. Click "Save all"

**Via CLI**:
```bash
# Templates are stored in the database
# You can query/edit via SQL or use Python API
```

**Via Python API**:
```python
from ae import repo

# Update a template
repo.upsert_onboarding_template(
    db_path="acq.db",
    client_id="plumber-cm-oldtown",
    template_key="utm_policy_md",
    content="# Your custom UTM policy..."
)
```

### Step 4: Use Templates

**During Campaign Setup**:
- Reference UTM policy when creating ads
- Follow naming policy for campaign/page IDs
- Implement events according to event map

**During Operations**:
- Use templates to verify UTM parameters are correct
- Check that campaign names follow conventions
- Ensure events fire as defined

**During Reporting**:
- Templates help interpret data consistently
- Cross-reference actual UTM params with policy
- Validate event tracking matches event map

### Step 5: Generate Onboarding Pack (Optional)

Generate a complete onboarding pack with all templates plus a "First 7 Days" checklist:

```bash
python -m ae.cli generate-onboarding \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --out-root clients
```

This creates markdown files in `clients/plumber-cm-oldtown/onboarding/`:
- `utm_policy.md`
- `event_map.md`
- `naming_convention.md`
- `first_7_days.md` (operator checklist)

## How Templates Are Stored

Templates are stored in the `onboarding_templates` table:
- `client_id` + `template_key` = primary key
- `content` = markdown text
- `updated_utc` = timestamp

Each client has their own set of templates, so you can customize per client while maintaining defaults.

## Integration Points

### Console UI
- `/console/onboarding` - View/edit templates
- `/console/clients` - List clients (links to onboarding)

### CLI Commands
- `onboarding-init` - Initialize templates
- `generate-onboarding` - Generate onboarding pack

### Python API
- `repo.ensure_default_onboarding_templates()` - Ensure defaults exist
- `repo.upsert_onboarding_template()` - Update a template
- `repo.get_onboarding_template()` - Retrieve a template
- `repo.list_onboarding_templates()` - List all templates for a client

### REST API
- `GET /api/onboarding/{client_id}` - Get all templates
- `PUT /api/onboarding/{client_id}/{template_key}` - Update a template

## Best Practices

### 1. Customize Early
Don't wait until you have campaigns running. Set up templates right after creating the client.

### 2. Keep It Simple
Start with defaults and only customize what's necessary. Over-customization leads to inconsistency.

### 3. Document Decisions
If you deviate from defaults, document why in the template itself (as markdown comments).

### 4. Review Regularly
Periodically review templates to ensure they still match your actual usage.

### 5. Version Control
Consider exporting templates to files and version-controlling them:
```bash
python -m ae.cli generate-onboarding --db acq.db --client-id plumber-cm-oldtown
# Then commit clients/plumber-cm-oldtown/onboarding/ to git
```

## Example: Complete Onboarding Flow

```bash
# 1. Create client
python -m ae.cli create-client \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --name "CM Oldtown Plumbing" \
  --trade plumber \
  --city "chiang mai" \
  --phone "+66-80-000-0000" \
  --email "leads@example.com" \
  --service-area "Chiang Mai Old Town"

# 2. Initialize templates (automatic, but can do explicitly)
python -m ae.cli onboarding-init --db acq.db --client-id plumber-cm-oldtown

# 3. Review/customize via console
# Open: http://localhost:8000/console/onboarding?client_id=plumber-cm-oldtown

# 4. Generate onboarding pack
python -m ae.cli generate-onboarding \
  --db acq.db \
  --client-id plumber-cm-oldtown \
  --out-root clients

# 5. Use templates when creating campaigns/pages
# Reference UTM policy, follow naming conventions, implement events
```

## Troubleshooting

### Templates Not Found
**Symptom**: Console shows empty templates or error.

**Solution**:
```bash
python -m ae.cli onboarding-init --db acq.db --client-id YOUR_CLIENT_ID
```

### Templates Overwritten
**Symptom**: Customizations lost.

**Solution**: Use `--overwrite` flag only when you want to reset to defaults:
```bash
python -m ae.cli onboarding-init --db acq.db --client-id YOUR_CLIENT_ID --overwrite
```

### Inconsistent Attribution
**Symptom**: UTM parameters don't match policy.

**Solution**: 
1. Review actual UTM params in your ads platform
2. Compare with UTM policy template
3. Update either ads or template to match
4. Document the decision

## Summary

Onboarding templates are **operational guardrails** that ensure:
- ✅ Consistent attribution across channels
- ✅ Reliable historical data
- ✅ Clear measurement vocabulary
- ✅ Auditable campaign performance

They're not just documentation—they're the foundation for reliable acquisition operations.
