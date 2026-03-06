# Content Personalization Implementation Summary

## What Was Fixed

### 1. Page Content Personalization
Pages now have **different content** based on their `service_focus`:

#### Main Page (`service_focus=None`)
- **Headline**: "Test Massage Spa in Chiang Mai City"
- **Subheadline**: "Book your appointment today. Transparent pricing. Professional service."
- **CTAs**: "View Packages" / "Book Now"
- **Amenities**: Professional Staff, Clean Facilities, Flexible Booking
- **Testimonials**: Standard proof points
- **FAQ**: General booking questions

#### Premium Page (`service_focus='premium'`)
- **Headline**: "Test Massage Spa — Premium Massage Services"
- **Subheadline**: "Luxury experience. Premium quality. Exceptional service."
- **CTAs**: "View Premium Packages" / "Book Premium Service"
- **Amenities**: Premium Facilities, Luxury Experience, Expert Therapists
- **Testimonials**: "5★ luxury rating", "Premium clientele"
- **FAQ**: "What makes your premium service different?", "Do you offer gift packages?"

#### Express Page (`service_focus='express'`)
- **Headline**: "Test Massage Spa — Express Booking"
- **Subheadline**: "Fast booking. Quick service. Same-day availability."
- **CTAs**: "Book Now" / "Quick Booking"
- **Amenities**: Fast Booking, Quick Service, Same-Day Availability
- **Testimonials**: "Fast booking process", "Quick service turnaround"
- **FAQ**: "How fast can I book?", "Do you offer same-day appointments?"

### 2. Package Filtering
Packages can now be filtered by `service_focus`:

- **Main page**: Shows packages with `service_focus=None` or missing
- **Premium page**: Shows packages with `service_focus='premium'`
- **Express page**: Shows packages with `service_focus='express'`

**Current Package Assignments:**
- `pkg-relax-60`: Main page (service_focus=None)
- `pkg-deep-90`: Premium page (service_focus='premium')
- `pkg-couple-60`: Premium page (service_focus='premium')

### 3. API Enhancements
- `/v1/service-packages` endpoint now accepts `page_id` or `service_focus` parameter
- Automatically filters packages based on page's service_focus
- Landing pages pass `page_id` to API for automatic filtering

## How to View Personalized Pages

1. **Start Public API** (for packages):
   ```powershell
   start_public_api.bat
   ```

2. **Start Static Server**:
   ```powershell
   serve_pages.bat
   ```

3. **Visit Pages**:
   - Main: http://localhost:8080/test-massage-spa-main/index.html
   - Premium: http://localhost:8080/test-massage-spa-premium/index.html
   - Express: http://localhost:8080/test-massage-spa-express/index.html

## Customizing Package Assignments

To assign packages to specific pages, update package `meta_json`:

```python
from ae import repo

# Assign to premium page
pkg = repo.get_package('acq.db', 'pkg-id')
pkg.meta_json['service_focus'] = 'premium'
repo.update_package('acq.db', pkg)

# Assign to express page
pkg.meta_json['service_focus'] = 'express'
repo.update_package('acq.db', pkg)

# Assign to main page (or all pages)
pkg.meta_json['service_focus'] = None
repo.update_package('acq.db', pkg)
```

## Files Modified

1. `src/ae/adapters/content_stub.py` - Added service_focus-based personalization
2. `src/ae/console_routes_service_packages_public.py` - Added package filtering by service_focus
3. `src/ae/adapters/publisher_tailwind_static.py` - Pass page_id to packages API

## Next Steps

1. **Republish pages** after making changes: `python republish_pages.py`
2. **Assign service_focus to packages** as needed: `python assign_package_focus.py`
3. **Start both servers** to view pages with packages
