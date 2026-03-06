# Client Schema v2 - Scalable Design

## Overview

The Client schema has been updated to support multiple business models and service types in a scalable way. This design separates "what business they're in" (trade) from "how they operate" (business model).

## Changes

### New Fields

1. **`business_model`** (enum, required, default: `quote_based`)
   - Defines how the client operates
   - Values: `quote_based`, `fixed_price`, `subscription`, `hybrid`

2. **`service_config_json`** (dict, optional, default: `{}`)
   - Flexible configuration for service-specific settings
   - Structure varies by business model

### Updated Trade Enum

Added new trade types:
- `massage`
- `spa`

## Schema Structure

```python
class Client(BaseModel):
    # Core identity
    client_id: str
    client_name: str
    
    # Business category (what they do)
    trade: Trade  # plumber, electrician, massage, spa, etc.
    
    # Operational model (how they operate) - NEW
    business_model: BusinessModel = Field(default=BusinessModel.quote_based)
    
    # Location & contact
    geo_country: str = Field(default="AU")
    geo_city: str
    service_area: List[str]
    primary_phone: str
    lead_email: EmailStr
    status: ClientStatus = ClientStatus.draft
    
    # Optional business info
    hours: Optional[str] = None
    license_badges: List[str] = Field(default_factory=list)
    price_anchor: Optional[str] = None
    brand_theme: Optional[str] = None
    notes_internal: Optional[str] = None
    
    # Service configuration (flexible JSON) - NEW
    service_config_json: Dict[str, Any] = Field(default_factory=dict)
```

## Usage Examples

### Traditional Quote-Based Client (Plumber)

```python
Client(
    client_id="plumber-cm-oldtown",
    client_name="CM Oldtown Plumbing",
    trade=Trade.plumber,
    business_model=BusinessModel.quote_based,
    geo_city="chiang mai",
    service_area=["Chiang Mai Old Town"],
    primary_phone="+66-80-000-0000",
    lead_email="leads@example.com",
    # service_config_json defaults to {}
)
```

### Fixed-Price Service Client (Massage Spa)

```python
Client(
    client_id="massage-spa-cm",
    client_name="CM Relaxation Spa",
    trade=Trade.massage,
    business_model=BusinessModel.fixed_price,
    geo_city="chiang mai",
    service_area=["Chiang Mai City"],
    primary_phone="+66-80-000-0000",
    lead_email="bookings@example.com",
    service_config_json={
        "booking_flow": "package_selection",
        "payment_flow": "deposit_then_balance",
        "deposit_percentage": 50,
        "default_booking_windows": ["morning", "afternoon", "evening"],
        "features": {
            "service_packages": True,
            "online_booking": True,
            "time_slots": True,
            "addons": True
        }
    }
)
```

## Service Config JSON Structure

### For Fixed-Price Clients

```json
{
  "booking_flow": "package_selection",
  "payment_flow": "deposit_then_balance",
  "deposit_percentage": 50,
  "default_booking_windows": ["morning", "afternoon", "evening"],
  "features": {
    "service_packages": true,
    "online_booking": true,
    "time_slots": true,
    "addons": true
  }
}
```

### For Quote-Based Clients

```json
{
  "booking_flow": "quote_request",
  "features": {
    "quote_requests": true,
    "callback_requests": true
  }
}
```

## Database Schema

```sql
CREATE TABLE clients (
    client_id TEXT PRIMARY KEY,
    client_name TEXT NOT NULL,
    trade TEXT NOT NULL,
    business_model TEXT NOT NULL DEFAULT 'quote_based',  -- NEW
    geo_country TEXT NOT NULL,
    geo_city TEXT NOT NULL,
    service_area_json TEXT NOT NULL,
    primary_phone TEXT NOT NULL,
    lead_email TEXT NOT NULL,
    status TEXT NOT NULL,
    hours TEXT,
    license_badges_json TEXT NOT NULL,
    price_anchor TEXT,
    brand_theme TEXT,
    notes_internal TEXT,
    service_config_json TEXT NOT NULL DEFAULT '{}'  -- NEW
);
```

## Migration Notes

- Existing databases: New columns added with defaults
- Existing clients: Will default to `business_model='quote_based'` and `service_config_json={}`
- No breaking changes: All existing code continues to work

## Benefits

1. **Scalable**: Easy to add new trade types without code changes
2. **Flexible**: Business model enum handles operational differences
3. **Extensible**: JSON config allows per-client customization
4. **Queryable**: Can filter by `business_model` or `service_config_json` features
5. **Type-safe**: Enums provide structure, JSON provides flexibility

## API Usage

### Create Fixed-Price Client

```bash
POST /api/clients
{
  "client_id": "massage-spa-cm",
  "client_name": "CM Relaxation Spa",
  "trade": "massage",
  "business_model": "fixed_price",
  "geo_city": "chiang mai",
  "primary_phone": "+66-80-000-0000",
  "lead_email": "bookings@example.com",
  "service_config_json": {
    "deposit_percentage": 50,
    "features": {"service_packages": true}
  }
}
```

### Query by Business Model

```python
# Get all fixed-price clients
clients = [c for c in repo.list_clients(db_path) 
           if c.business_model == BusinessModel.fixed_price]

# Get clients with service packages enabled
clients = [c for c in repo.list_clients(db_path)
           if c.service_config_json.get("features", {}).get("service_packages")]
```

## Future Extensions

- Add new trade types: Just add to `Trade` enum
- Add new business models: Add to `BusinessModel` enum
- Customize per client: Use `service_config_json`
- No code changes needed for new combinations
