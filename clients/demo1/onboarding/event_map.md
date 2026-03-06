# Event Map — demo1

Goal: measure funnel health without collecting personal data.

## Funnel stages (v1)
1) **Landing**: `page_view`
2) **Intent**: `view_content` (scrolled, engaged, or viewed pricing/offer block)
3) **Lead**: `generate_lead` (form submit, WhatsApp click, call click)
4) **Booking**: `booking` (appointment confirmed / deposit / calendar)

## Event definitions
- `page_view`
  - fires on page load
- `view_content`
  - fires when user reaches offer section (e.g. 50% scroll) OR clicks “Pricing”
- `generate_lead`
  - fires on: form submit OR click-to-call OR click WhatsApp/LINE
- `booking`
  - fires when booking confirmed (server-side preferred)

## Notes
- We optimize the **funnel as a system**: CTR → CVR (lead) → booking rate.
- If tracking breaks, decisions become noise. Always QA events after edits.
