# Startup Script Summary

## What `start_local_dev.ps1` Now Does

### Automatic Setup (Before Server Starts)

1. **Sets Environment Variables**
   - `PYTHONPATH = "src"`
   - `AE_DB_PATH = "acq.db"`
   - `AE_PUBLIC_API_URL = "http://localhost:8000/api"`

2. **Runs `scripts/setup/setup_demo1_client.py`**
   - Updates client `demo1` business_model to `fixed_price`
   - Creates 3 packages if they don't exist:
     - 60-Minute Relaxation Massage (1,500 THB)
     - 90-Minute Deep Tissue Massage (2,200 THB)
     - Couples Massage (60 min) (2,800 THB)
   - Publishes landing page `p1` with packages

3. **Starts Unified Server**
   - Console: `/console`
   - Money Board: `/money-board`
   - Public API: `/api` and `/v1/*`
   - Landing Pages: `/pages/{page_id}`
   - Telegram Bots: Automatic polling (customer + vendor)

### Fixed Issues

1. **CSS Path**: Changed from relative `assets/styles.css` to absolute `/pages/{page_id}/assets/styles.css`
2. **Client Configuration**: Automatically sets `business_model = fixed_price` for packages to show
3. **Package Creation**: Automatically creates packages if missing
4. **Page Publishing**: Automatically publishes landing page before server starts

### Result

When you run `.\start_local_dev.ps1`:
- ✅ Client configured correctly
- ✅ Packages created and linked
- ✅ Landing page published with packages
- ✅ CSS assets accessible
- ✅ Server starts with everything ready

### Access Points

- **Landing Page**: http://localhost:8000/pages/p1
- **Console**: http://localhost:8000/console
- **Money Board**: http://localhost:8000/money-board
- **Packages API**: http://localhost:8000/v1/service-packages?client_id=demo1&active=true&db=acq.db

Everything is ready to go! 🚀
