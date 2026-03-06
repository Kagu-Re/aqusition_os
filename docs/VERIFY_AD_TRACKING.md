# How to Verify Google & Meta Ad Tracking

## Overview

To confirm Google/Meta ad tracking is working, you need to verify that **UTM parameters** from ad URLs are being captured and stored in event tracking.

## Current State

Looking at your events, the UTM parameters are present in the schema but showing `null`:
```json
{
  "utm_source": null,
  "utm_medium": null,
  "utm_campaign": null,
  "utm_content": null,
  "utm_term": null
}
```

This means:
- ✅ UTM parameter capture is **implemented** in the tracking code
- ❌ UTM parameters are **not present** in the current test events (no UTM params in URL)

## How UTM Parameters Work

### Google Ads UTM Format

When users click Google Ads, URLs typically include:
```
?utm_source=google
&utm_medium=cpc
&utm_campaign=your-campaign-name
&utm_content=ad-variant
&utm_term=keyword
```

### Meta Ads UTM Format

When users click Meta/Facebook Ads, URLs typically include:
```
?utm_source=facebook
&utm_medium=cpc
&utm_campaign=your-campaign-name
&utm_content=ad-creative-id
```

Or:
```
?utm_source=meta
&utm_medium=paid
&utm_campaign=your-campaign-name
```

## How to Verify Tracking

### Step 1: Test with UTM Parameters

1. **Serve your HTML page**:
   ```powershell
   cd exports\static_site\p1
   python -m http.server 8080
   ```

2. **Open page with Google Ads UTM parameters**:
   ```
   http://localhost:8080/index.html?utm_source=google&utm_medium=cpc&utm_campaign=test-campaign&utm_content=ad-a&utm_term=plumber
   ```

3. **Click buttons** to trigger events:
   - Click "Book now" → triggers `call_click`
   - Click "Get a quote" → triggers `quote_submit`

4. **Check events in console**:
   - Load events in admin console
   - Look for new events with populated UTM fields:
     ```json
     {
       "utm_source": "google",
       "utm_medium": "cpc",
       "utm_campaign": "test-campaign",
       "utm_content": "ad-a",
       "utm_term": "plumber"
     }
     ```

### Step 2: Test Meta Ads UTM Parameters

1. **Open page with Meta Ads UTM parameters**:
   ```
   http://localhost:8080/index.html?utm_source=facebook&utm_medium=cpc&utm_campaign=meta-test&utm_content=creative-1
   ```

2. **Click buttons** to trigger events

3. **Verify events show Meta UTM values**:
   ```json
   {
     "utm_source": "facebook",
     "utm_medium": "cpc",
     "utm_campaign": "meta-test",
     "utm_content": "creative-1"
   }
   ```

## What to Look For

### ✅ Google Ads Tracking Confirmed If:

- `utm_source` = `"google"` or `"googleads"`
- `utm_medium` = `"cpc"` (cost-per-click) or `"paid"`
- `utm_campaign` = your campaign name
- `utm_term` = keyword (for search ads)

**Example**:
```json
{
  "event_name": "call_click",
  "params_json": {
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "plumber-cm-feb",
    "utm_content": "headline-a",
    "utm_term": "plumber-near-me"
  }
}
```

### ✅ Meta Ads Tracking Confirmed If:

- `utm_source` = `"facebook"` or `"meta"` or `"instagram"`
- `utm_medium` = `"cpc"` or `"paid"` or `"social"`
- `utm_campaign` = your campaign name
- `utm_content` = ad creative ID or variant

**Example**:
```json
{
  "event_name": "quote_submit",
  "params_json": {
    "utm_source": "facebook",
    "utm_medium": "cpc",
    "utm_campaign": "plumber-cm-feb",
    "utm_content": "video-ad-v1"
  }
}
```

## Testing Checklist

### Manual Test

- [ ] Open page with Google UTM parameters
- [ ] Trigger events (click buttons)
- [ ] Verify events show `utm_source: "google"`
- [ ] Open page with Meta UTM parameters
- [ ] Trigger events
- [ ] Verify events show `utm_source: "facebook"` or `"meta"`

### In Console

- [ ] Load events in admin console
- [ ] Filter by `page_id` if needed
- [ ] Check `params_json` for UTM values
- [ ] Verify `utm_source` matches ad platform
- [ ] Verify `utm_campaign` matches campaign name

## How UTM Parameters Are Captured

The tracking JavaScript automatically extracts UTM parameters from the URL:

```javascript
function getUTMParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    utm_source: params.get('utm_source') || null,
    utm_medium: params.get('utm_medium') || null,
    utm_campaign: params.get('utm_campaign') || null,
    utm_content: params.get('utm_content') || null,
    utm_term: params.get('utm_term') || null
  };
}
```

These are included in every event's `params_json`.

## Real-World Ad Setup

### Google Ads

1. **Set up tracking template** in Google Ads:
   ```
   {lpurl}?utm_source=google&utm_medium=cpc&utm_campaign={campaign}&utm_content={adgroup}&utm_term={keyword}
   ```

2. **Verify in events**: Check that events show these UTM values

### Meta Ads

1. **Set up URL parameters** in Meta Ads Manager:
   ```
   ?utm_source=facebook&utm_medium=cpc&utm_campaign={campaign.name}&utm_content={ad.name}
   ```

2. **Verify in events**: Check that events show these UTM values

## Troubleshooting

### UTM Parameters Are Null

**Cause**: No UTM parameters in the URL when page was visited.

**Fix**: 
- Test with UTM parameters in URL (see Step 1 above)
- Ensure ads are configured with UTM parameters
- Check that UTM parameters persist through redirects

### UTM Parameters Not Matching Ads

**Cause**: UTM parameters not configured correctly in ad platform.

**Fix**:
- Review UTM policy in client onboarding templates
- Ensure ad platform uses correct UTM structure
- Verify UTM parameters in ad preview/URL builder

### Events Don't Show UTM Values

**Cause**: Events recorded before UTM capture was implemented, or URL didn't have UTM params.

**Fix**:
- Record new events with UTM parameters in URL
- Clear old test events if needed
- Verify tracking JavaScript includes `getUTMParams()`

## Summary

**To confirm Google/Meta ad tracking**:

1. ✅ **UTM capture is implemented** (already done)
2. ⚠️ **Test with UTM parameters** (needs testing)
3. ✅ **Check events show UTM values** (verify in console)
4. ✅ **Match UTM values to ad campaigns** (verify attribution)

**Current status**: UTM capture is working, but you need to test with actual UTM parameters in the URL to see them populated in events.
