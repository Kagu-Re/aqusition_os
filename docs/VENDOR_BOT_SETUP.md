# Vendor Bot Setup Guide

## Overview

The vendor bot allows vendors to manage bookings directly through Telegram without accessing the Money Board web UI.

## Setup

### Step 1: Create Vendor Bot Channel

```powershell
python create_vendor_telegram_channel.py
```

This creates a Telegram channel entry with:
- **Channel ID:** `ch_vendor_telegram`
- **Handle:** `@vendorthaibot`
- **Bot Token:** `8250433487:AAFtelsTkLUjO56D7T3glHiUz5GC0ibqTKY`
- **Bot Type:** `vendor`

### Step 2: Start Local Dev Server

```powershell
.\start_local_dev.ps1
```

The vendor bot will start automatically in polling mode (no webhook needed).

## Vendor Bot Commands

### `/start` or `/help`
Show available commands.

### `/bookings`
List pending bookings that need vendor action:
- Bookings with status `deposit_requested` (waiting for payment)
- Bookings with status `confirmed` (ready to complete)

**Example output:**
```
📋 Pending Bookings:

• br_123
  John Doe | Status: deposit_requested | Payment: requested (pi_456)
  Time: 2024-02-10 14:00-16:00

• br_124
  Jane Smith | Status: confirmed | Payment: paid (pi_457)
```

### `/confirm <booking_id>`
Confirm a booking manually (if payment was received outside the system).

**Example:**
```
/confirm br_123
```

**Response:**
```
✅ Booking 'br_123' confirmed!
```

### `/paid <payment_id>`
Mark a payment intent as paid. This will:
1. Mark the payment intent as paid
2. Create a Payment record
3. Automatically confirm the booking

**Example:**
```
/paid pi_456
```

**Response:**
```
✅ Payment 'pi_456' marked as paid!
Amount: ฿1500
Booking automatically confirmed.
```

### `/complete <booking_id>`
Mark a booking as completed (after service is delivered).

**Example:**
```
/complete br_123
```

**Response:**
```
✅ Booking 'br_123' marked as completed!
```

**Note:** Booking must be `confirmed` before it can be marked as `completed`.

## Workflow

### Typical Vendor Workflow

1. **Customer books** → Booking created with status `requested`
2. **Time window set** → Booking status: `deposit_requested`
3. **Payment intent created** → Vendor sees in `/bookings`
4. **Customer pays** → Vendor runs `/paid <payment_id>`
5. **Booking confirmed** → Automatically updated to `confirmed`
6. **Service delivered** → Vendor runs `/complete <booking_id>`
7. **Booking completed** → Status: `completed`

### Alternative: Manual Confirmation

If payment was received outside the system:
1. Vendor runs `/confirm <booking_id>`
2. Booking status: `confirmed`
3. Later: `/complete <booking_id>`

## Testing

### Test Vendor Bot

1. **Start server:**
   ```powershell
   .\start_local_dev.ps1
   ```

2. **Send message to vendor bot:**
   - Open Telegram
   - Find `@vendorthaibot`
   - Send `/start`

3. **Check server logs:**
   - Should see: `[TelegramPolling] ✅ Started Telegram vendor bot polling`
   - Should see message received

4. **Test commands:**
   - `/bookings` - List bookings
   - `/paid <payment_id>` - Mark payment as paid
   - `/complete <booking_id>` - Complete booking

## Integration with Money Board

The vendor bot and Money Board share the same database:
- **Vendor bot actions** update the same booking records
- **Money Board** shows real-time updates from vendor bot
- **Both systems** stay in sync automatically

## Benefits

✅ **No web UI needed** - Manage bookings via Telegram
✅ **Mobile-friendly** - Use on phone while on-site
✅ **Fast actions** - Quick commands for common tasks
✅ **Real-time sync** - Updates reflected in Money Board immediately
✅ **No webhook setup** - Polling mode works locally

## Troubleshooting

### Vendor Bot Not Responding

1. **Check server logs:**
   - Should see: `[LocalDevServer] ✅ Started Telegram vendor bot polling`

2. **Verify channel exists:**
   ```python
   from ae import repo
   channel = repo.get_chat_channel("acq.db", "ch_vendor_telegram")
   print(channel.meta_json.get("telegram_bot_token"))
   ```

3. **Test manually:**
   - Send `/start` to `@vendorthaibot`
   - Check server logs for errors

### Booking Not Found

- Verify booking ID format (e.g., `br_123`)
- Check booking exists in database:
  ```python
  from ae import repo
  booking = repo.get_booking_request("acq.db", "br_123")
  print(booking)
  ```

### Payment Not Found

- Verify payment intent ID format (e.g., `pi_456`)
- Check payment intent exists:
  ```python
  from ae import repo
  payment = repo.get_payment_intent("acq.db", "pi_456")
  print(payment)
  ```

## Next Steps

1. ✅ **Create vendor channel:** `python create_vendor_telegram_channel.py`
2. ✅ **Start server:** `.\start_local_dev.ps1`
3. ⏳ **Test vendor bot:** Send `/start` to `@vendorthaibot`
4. ⏳ **Test commands:** `/bookings`, `/paid`, `/complete`
5. ⏳ **Verify in Money Board:** Check updates appear

Ready to manage bookings via Telegram! 🚀
