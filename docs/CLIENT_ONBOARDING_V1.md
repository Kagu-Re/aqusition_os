# Client Onboarding v1 (manual)

Goal: create a repeatable “operator-first” onboarding flow for a new client, so you can run acquisition experiments with traceability and low cognitive load.

## Minimum data to collect
- **Client ID** (slug): stable identifier (e.g., `plumber-cm-oldtown`)
- **Trade**: pick from your allowed trade enum (engine constraint)
- **Geo**: country + city
- **Contact**: primary phone + lead email
- **Service area**: list of served areas (at least city)

## Day 0 — Setup
1) Create/confirm **client registry record** (where you store:
   - offer statement
   - geo + target radius
   - contact info
   - operator notes)
2) Define **campaign naming convention**:
   - `source_medium_campaign_content_term`
   - store in one place (SSOT) so you can audit later
3) Define **event map** (what you measure):
   - view_content
   - lead (form submit / whatsapp click)
   - booking (call / appointment)
4) Tracking install checklist:
   - GA4 / pixels
   - UTM passthrough
   - basic QA run (events fire)

## Days 1–7 — Learning loop
Daily:
- Check spend / pacing guardrails
- Review CTR, CPC, CVR (lead), cost/lead
- Record 1–3 observations + decision

Decisions:
- if CTR low → creative / angle changes
- if CVR low → landing copy / offer / friction
- if cost too high → narrow geo / adjust targeting

## Artifacts (next)
- onboarding JSON template
- console surface (/console/clients)
- API endpoints (/api/clients)
- operator script (“first 7 days”)

