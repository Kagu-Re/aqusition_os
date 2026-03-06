# Console Access Guide

## Server Status

Your console server is running successfully! The 404 errors you're seeing are normal - the root path `/` doesn't have content, but the console is available at `/console`.

## Accessing the Console

### Main Console URL
```
http://127.0.0.1:8000/console
```
or
```
http://localhost:8000/console
```

The root path (`http://localhost:8000/`) now automatically redirects to `/console`.

### Available Endpoints

**Console UI:**
- `/console` - Main operator console interface
- `/console/clients` - Client management
- `/console/onboarding` - Client onboarding
- `/console/abuse` - Abuse monitoring

**API Endpoints:**
- `/api/health` - Health check endpoint
- `/api/ready` - Readiness probe
- `/api/auth/login` - Authentication endpoint
- `/api/clients` - Client API
- `/api/pages` - Page management API
- `/api/menus` - Menu management API
- `/api/chat-channels` - Chat channel API
- And many more...

## Login

After starting the console, you'll need to log in:

1. **If you haven't set a password yet:**
   ```powershell
   $env:PYTHONPATH="src"
   $env:AE_DB_PATH="acq.db"
   python -m ae.cli auth-set-password --username admin
   ```

2. **Access the console** at `http://localhost:8000/console`

3. **Login via API** (if needed):
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"your_password"}'
   ```

## Troubleshooting

### 404 on Root Path (`/`)
- **This is normal!** The console is at `/console`, not `/`
- The root path now redirects to `/console` automatically

### 404 on `/favicon.ico`
- This is normal - the favicon isn't configured yet
- It doesn't affect functionality

### Server Running but Can't Access
- Make sure you're accessing `http://localhost:8000/console` (not just `/`)
- Check that `AE_DB_PATH` is set correctly
- Verify the database file exists at the specified path

### Authentication Issues
- Make sure you've created an admin user:
  ```bash
  python -m ae.cli auth-create-user --username admin --role admin
  ```
- Set the password:
  ```bash
  python -m ae.cli auth-set-password --username admin
  ```

## Next Steps

1. Open `http://localhost:8000/console` in your browser
2. Log in with your admin credentials
3. Explore the console interface:
   - View clients
   - Manage pages
   - Check system health
   - Monitor leads and bookings

## Health Check

Test that the server is working:
```bash
curl http://localhost:8000/api/health
```

You should get a JSON response with status information.
