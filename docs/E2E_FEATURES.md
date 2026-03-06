# End-to-End Initialization - Feature Coverage

This document outlines all the system components that are initialized and tested during the end-to-end initialization process.

## Core Components

### 1. Database & Schema
- SQLite database initialization
- All tables created (clients, templates, pages, menus, chat_channels, qr_attributions, etc.)
- Indexes and foreign keys configured

### 2. Templates & Pages
- **Template**: `trade_lp` (Trades Landing Page template)
- **Client**: `demo1` (Demo Plumbing)
- **Page**: `p1` (demo-plumbing-v1 landing page)
- Page validation and publishing workflow

### 3. Chat Channels
- **WhatsApp Channel**: `ch_demo_whatsapp`
  - Provider: WhatsApp
  - Handle: +61-400-000-000
  - Linked to demo1 client
  - Supports conversation mapping and automation

### 4. Menus
- **Menu**: `menu_demo1`
  - Client: demo1
  - Language: English
  - Currency: AUD
  - Status: Draft
  - **Sections**: Services
  - **Items**: 
    - Emergency Plumbing ($150 AUD)
    - General Repairs ($120 AUD)

### 5. QR Codes
- QR code generation tested
- Output directory: `generated/qr/`
- File: `test-menu-demo1.png`
- Supports attribution tracking
- Can be linked to menus for scan tracking

### 6. Ads Integration
- **Meta Ads Adapter** (stub)
  - Pull spend data
  - Pull results (leads, bookings, revenue)
  - Push assets
- **Google Ads Adapter** (stub)
  - Pull spend data
  - Pull results (leads, bookings, revenue)
  - Push assets

### 7. Authentication
- **Admin User**: `admin`
  - Default password: `changeme123` (must be changed!)
  - Role: admin
  - Console access enabled

### 8. Console & API
- FastAPI console application
- Health endpoints (`/health`, `/ready`)
- Public API endpoints
- Console UI at `/console`

## Testing Coverage

### Unit Tests
- All test suites run via pytest
- Tests cover:
  - Database operations
  - Service layer logic
  - API endpoints
  - Adapters
  - Models and validation

### Compliance Checks
- Alias registry validation
- Guardrails evaluation
- Schema validation

### Smoke Tests
- Health endpoint checks
- Ready endpoint checks
- Lead intake API test
- Console API accessibility

## System Flow Coverage

The initialization covers the full system flow:

```
Ads (Meta/Google) → Landing Page → Lead → Chat → Booking → Payment → Export
                    ↓
                 QR Codes → Menu → Attribution Tracking
```

### Components Initialized:
1. ✅ **Ads**: Meta & Google adapters tested
2. ✅ **Landing Pages**: Template, client, page created
3. ✅ **Chat**: WhatsApp channel configured
4. ✅ **Menus**: Menu with sections and items
5. ✅ **QR Codes**: Generation tested with attribution
6. ✅ **Authentication**: Admin user created
7. ✅ **Console**: Startup verified
8. ✅ **API**: Endpoints tested

## Next Steps After Initialization

1. **Change Admin Password**
   ```bash
   python -m ae.cli auth-set-password --username admin
   ```

2. **Start Console**
   ```bash
   export AE_DB_PATH=$(pwd)/acq.db
   python -m ae.cli serve-console
   ```

3. **Access Console**
   - URL: http://localhost:8000/console
   - Login with admin credentials

4. **Configure Real Integrations**
   - Replace ads stubs with real API credentials
   - Connect real chat provider webhooks
   - Set up real payment provider
   - Configure export destinations

5. **Generate Production QR Codes**
   - Use console API to generate QR codes for menus
   - Enable attribution tracking
   - Deploy QR codes to physical locations

6. **Set Up Monitoring**
   - Configure logging
   - Set up metrics collection
   - Enable alerts

## Feature-Specific Documentation

- **Chat**: See `tests/test_chat_channels_v1.py` and `tests/test_chat_automation_v1.py`
- **Menus**: See `tests/test_menu_schema_v1.py` and `src/ae/console_routes_menus.py`
- **QR Codes**: See `tests/test_qr_batch_generator.py` and `src/ae/qr_codes.py`
- **Ads**: See `tests/test_ads_stubs.py` and `src/ae/ads/`

## Notes

- All components use demo/test data suitable for development
- Production deployments require:
  - Real API credentials
  - Secure password management
  - Production-grade database backups
  - Monitoring and alerting
  - Rate limiting configuration
