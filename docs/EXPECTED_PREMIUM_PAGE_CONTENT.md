# Expected Content for Premium Page
## URL: `http://localhost:8080/test-massage-spa-premium/index.html#book`

### Page Configuration
- **Page ID**: `test-massage-spa-premium`
- **Page service_focus**: `"premium"`
- **Client ID**: `test-massage-spa`

---

## 1. STATIC CONTENT (from Client + Page data)

### Headline
**Expected**: `"Test Massage Spa — Premium Massage Services"`
- Uses: `client_name` + `service_focus="premium"` + `trade`

### Subheadline
**Expected**: `"Luxury experience. Premium quality. Exceptional service."`
- Uses: `service_focus="premium"` specific messaging
- May include hours if available: `"Open {hours}. Luxury experience..."`

### CTAs
- **Primary CTA**: `"View Premium Packages"`
- **Secondary CTA**: `"Book Premium Service"`
- Uses: `service_focus="premium"` specific CTAs

### Amenities Section
**Expected items** (in order):
1. `"Licensed & Insured"` (if `license_badges` has 2+ items)
   OR `"Certified {badge}"` (if single badge)
2. `"Serving {service_area[0]}"` (e.g., "Serving Chiang Mai City")
3. `"Premium Facilities"`
4. `"Luxury Experience"`
5. `"Expert Therapists"`
6. `"VIP Treatment"` (if space allows)

**Uses**: `license_badges`, `service_area`, `service_focus="premium"` specific amenities

### Testimonials/Proof Section
**Expected items** (in order):
1. `"Starting from {price_anchor}"` (if `price_anchor` exists)
   OR just `"{price_anchor}"` (if already contains "Starting from")
2. `"Serving {service_area[0]} and surrounding areas"`
3. `"5★ luxury rating"`
4. `"Premium clientele"`
5. `"Exclusive packages available"` (if space allows)

**Uses**: `price_anchor`, `service_area`, `service_focus="premium"` specific proof points

### FAQ Section
**Expected questions**:
1. `"What are your operating hours?"` (if `hours` exists)
2. `"What areas do you serve?"` (if `service_area` exists)
3. `"What makes your premium service different?"`
4. `"Do you offer gift packages?"`

**Uses**: `hours`, `service_area`, `service_focus="premium"` specific FAQs

---

## 2. DYNAMIC PACKAGES (from API: `/v1/service-packages`)

### Package Filtering Logic
**CRITICAL**: Only packages with `meta_json.service_focus == "premium"` should appear.

### Expected Packages (based on `assign_package_focus.py`)

#### ✅ Package 1: Should APPEAR
- **Package ID**: `pkg-deep-90`
- **Name**: `"90-Minute Deep Tissue Massage"`
- **Price**: `$2200.00`
- **Duration**: `1h 30m` (90 minutes)
- **Addons**: `["Hot stones"]`
- **service_focus**: `"premium"` ✅

#### ✅ Package 2: Should APPEAR
- **Package ID**: `pkg-couple-60`
- **Name**: `"Couples Massage (60 min)"`
- **Price**: `$2800.00`
- **Duration**: `1h` (60 minutes)
- **Addons**: `["Champagne", "Private room"]`
- **service_focus**: `"premium"` ✅

#### ❌ Package 3: Should NOT APPEAR
- **Package ID**: `pkg-relax-60`
- **Name**: `"60-Minute Relaxation Massage"`
- **Price**: `$1500.00`
- **Duration**: `1h` (60 minutes)
- **Addons**: `["Aromatherapy", "Hot stones"]`
- **service_focus**: `None` ❌ (belongs to main page only)

---

## 3. AVAILABILITY BADGES (if available_slots calculated)

Each package card should display availability based on `available_slots`:

- **0 slots**: Red badge `"Fully booked"`, disabled button `"Fully Booked"`
- **1 slot**: Red badge `"Only 1 slot left!"`, button `"Book Now - Only 1 Left"`
- **2-3 slots**: Orange badge `"Only X slots left"`, button `"Book Now - Only X Left"`
- **4+ slots**: Green badge `"Available"` or no badge, button `"Select Package"`

**Calculation**: `max_capacity - active_bookings` (from Money Board)
**Fallback order**: 
1. Calculated from `max_capacity`
2. `meta_json.available_slots` (explicit)
3. `client.service_config_json.default_available_slots` (client default)

---

## SUMMARY

### What SHOULD appear:
- ✅ **2 packages**: `pkg-deep-90` and `pkg-couple-60`
- ✅ Premium-specific content (headlines, CTAs, amenities, testimonials, FAQ)
- ✅ Availability badges (if `available_slots` is calculated)

### What should NOT appear:
- ❌ **Package `pkg-relax-60`** (belongs to main page only)
- ❌ Standard/main page content

---

## CURRENT ISSUE

**Observed**: All 3 packages are appearing on the premium page.

**Expected**: Only 2 packages (`pkg-deep-90` and `pkg-couple-60`) should appear.

**Root Cause**: Package filtering logic in `/v1/service-packages` API is not correctly excluding packages with `service_focus=None` when `page.service_focus="premium"`.
