# Landing Page Service Packages Integration

## Overview

Landing pages now automatically detect fixed-price clients and display service packages for selection. This integration enables customers to browse and select packages directly on the landing page.

## Architecture

### Flow Diagram

```
Publish Page
  ↓
Content Adapter detects business_model="fixed_price"
  ↓
Publisher adds package selection HTML section
  ↓
JavaScript fetches packages from /v1/service-packages
  ↓
Packages displayed as cards
  ↓
User selects package → Creates lead → Redirects to chat
```

## Components

### 1. Public API Endpoint

**File**: `src/ae/console_routes_service_packages_public.py`

**Endpoint**: `GET /v1/service-packages?client_id={client_id}&active=true`

**Features**:
- Public access (no authentication required)
- Rate limited for abuse protection
- Returns active packages for specified client

**Example Response**:
```json
{
  "count": 3,
  "items": [
    {
      "package_id": "pkg1",
      "client_id": "massage-spa-cm",
      "name": "60-Minute Relaxation Massage",
      "price": 1500.0,
      "duration_min": 60,
      "addons": ["Aromatherapy", "Hot stones"],
      "active": true
    }
  ]
}
```

### 2. Content Adapter Extension

**File**: `src/ae/adapters/content_stub.py`

**Changes**:
- Detects `business_model="fixed_price"` from client
- Adds `show_packages: true` to payload
- Includes `client_id` for package fetching

**Payload Structure**:
```python
{
    "page_id": "p1",
    "headline": "...",
    "show_packages": True,  # NEW
    "client_id": "massage-spa-cm",  # NEW
    ...
}
```

### 3. Publisher Updates

**File**: `src/ae/adapters/publisher_tailwind_static.py`

**Changes**:
- Adds package selection HTML section (conditionally rendered)
- Includes JavaScript to fetch and display packages
- Handles package selection events

**HTML Structure**:
```html
<div id="packages-section" class="pt-10">
  <h2 class="h2 mb-6">Choose Your Service Package</h2>
  <div id="packages-container" class="grid grid-3 gap-4">
    <!-- Packages loaded dynamically -->
  </div>
</div>
```

### 4. JavaScript Functionality

**Features**:
- Fetches packages on page load
- Renders package cards with:
  - Package name
  - Price
  - Duration
  - Add-ons (if any)
  - Select button
- Handles package selection:
  - Tracks `package_selected` event
  - Creates lead with package metadata
  - Redirects to chat with package ID

**Package Card Structure**:
```javascript
{
  package_id: "pkg1",
  name: "60-Minute Relaxation Massage",
  price: 1500.0,
  duration_min: 60,
  addons: ["Aromatherapy", "Hot stones"]
}
```

## Usage

### Setting Up a Fixed-Price Client

1. **Create client with fixed_price business model**:
```python
Client(
    client_id="massage-spa-cm",
    business_model=BusinessModel.fixed_price,
    trade=Trade.massage,
    ...
)
```

2. **Create service packages**:
```python
ServicePackage(
    package_id="pkg1",
    client_id="massage-spa-cm",
    name="60-Minute Relaxation Massage",
    price=1500.0,
    duration_min=60,
    addons=["Aromatherapy", "Hot stones"],
    active=True
)
```

3. **Publish landing page**:
```bash
python -m ae.cli publish-page --db acq.db --page-id p1
```

### Result

When the landing page loads:
1. JavaScript detects `show_packages=true`
2. Fetches packages from `/v1/service-packages?client_id=massage-spa-cm`
3. Displays package cards
4. User can select a package
5. Selection creates lead and redirects to chat

## API Integration

### Fetching Packages

**Request**:
```
GET /v1/service-packages?client_id=massage-spa-cm&active=true&db=acq.db
```

**Response**:
```json
{
  "count": 2,
  "items": [
    {
      "package_id": "pkg1",
      "client_id": "massage-spa-cm",
      "name": "60-Minute Relaxation Massage",
      "price": 1500.0,
      "duration_min": 60,
      "addons": ["Aromatherapy"],
      "active": true,
      "meta_json": {},
      "created_at": "2026-02-06T10:00:00Z",
      "updated_at": "2026-02-06T10:00:00Z"
    }
  ]
}
```

### Package Selection Flow

1. **User clicks "Select Package"**
2. **Event tracked**: `package_selected` with package details
3. **Lead created**:
   ```json
   {
     "source": "landing_page",
     "page_id": "p1",
     "client_id": "massage-spa-cm",
     "message": "Package selected: 60-Minute Relaxation Massage",
     "meta": {
       "package_id": "pkg1",
       "package_name": "60-Minute Relaxation Massage",
       "package_price": 1500.0
     }
   }
   ```
4. **Redirect**: To chat URL with `?package=pkg1` parameter

## Styling

Packages use existing Tailwind CSS classes:
- `grid grid-3 gap-4` - 3-column grid layout
- `rounded-2xl border border-zinc-800` - Card styling
- `btn btn-primary` - Button styling
- Responsive design (grid adapts to screen size)

## Error Handling

- **No packages found**: Package section hidden
- **API error**: Package section hidden, error logged to console
- **Missing client_id**: Package section not rendered
- **Network failure**: Graceful degradation, section hidden

## Future Enhancements

Potential improvements:
1. **Package filtering**: Filter by price range, duration, etc.
2. **Package details modal**: Show full details before selection
3. **Add-on selection**: Allow users to customize add-ons
4. **Booking calendar**: Integrate time slot selection
5. **Package comparison**: Side-by-side comparison view

## Testing

To test the integration:

1. **Create test client**:
```bash
python -m ae.cli create-client \
  --db acq.db \
  --client-id test-massage \
  --name "Test Massage Spa" \
  --trade massage \
  --business-model fixed_price \
  --city "chiang mai" \
  --phone "+66-80-000-0000" \
  --email "test@example.com"
```

2. **Create test package**:
```bash
curl -X POST http://localhost:8000/api/service-packages \
  -H "X-AE-SECRET: your-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "test-pkg1",
    "client_id": "test-massage",
    "name": "Test Package",
    "price": 1000.0,
    "duration_min": 60,
    "addons": ["Test addon"]
  }'
```

3. **Create and publish page**:
```bash
python -m ae.cli create-page \
  --db acq.db \
  --page-id test-page \
  --client-id test-massage \
  --template-id trade_lp

python -m ae.cli publish-page --db acq.db --page-id test-page
```

4. **View published page**:
```bash
# Open: exports/static_site/test-page/index.html
# Or serve: cd exports/static_site/test-page && python -m http.server 8080
```

## Configuration

**Environment Variables**:
- `AE_PUBLIC_API_URL` - Public API base URL (default: `http://localhost:8001`)
- `AE_STATIC_OUT_DIR` - Output directory for static sites (default: `exports/static_site`)

## Notes

- Packages are fetched client-side (no server-side rendering)
- Package section only appears for `business_model="fixed_price"` clients
- All package data is fetched from the public API endpoint
- Rate limiting applies to package API requests
- Package selection creates leads with package metadata for tracking
