# UTM Policy — demo1

This policy keeps attribution consistent across Meta + Google.

## Canonical params (v1)
- `utm_source`: platform source (`meta`, `google`)
- `utm_medium`: traffic type (`cpc`, `paid_social`)
- `utm_campaign`: stable campaign key (snake/kebab; no spaces)
- `utm_content`: creative/adset identifier
- `utm_term`: keyword (Google) or audience/angle (Meta)

## Rules
1) **Never change** `utm_campaign` mid-flight. Create a new campaign key instead.
2) `utm_content` should map to **one creative variant**.
3) Use the same `utm_campaign` across platforms only if it is truly the same experiment.

## Example (Meta)
`utm_source=meta&utm_medium=paid_social&utm_campaign=demo1-plumber-brisbane-leadgen&utm_content=vid1-angleA&utm_term=aud-broad`

## Example (Google Search)
`utm_source=google&utm_medium=cpc&utm_campaign=demo1-plumber-brisbane-search&utm_content=rsag1&utm_term={keyword}`
