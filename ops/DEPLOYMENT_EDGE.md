# Edge-ready deployment notes (Public API + Operator Console)

This project supports **two HTTP surfaces**:

1) **Public API** (for website forms)
- `POST /lead`
- Intended to be internet-facing, protected by **WAF + rate limiting**.

2) **Operator Console** (internal/admin)
- `/console` UI and `/api/*` endpoints
- Intended to be protected behind auth, allowlisted IPs/VPN, or a separate host.

---

## Recommended topology

### Option A — Two hosts (cleanest)
- `public.example.com` → `ae.public_api:app`
- `ops.example.com` → `ae.console_app:app`

Benefits:
- Separate edge policies
- Separate logs and incident blast radius
- Easier to put the console behind VPN / IP allowlist

### Option B — One host, two paths (acceptable)
- `/` or `/public/*` → public API
- `/console` + `/api/*` → console

You must ensure:
- Strict auth for console routes
- Strong edge limits for `/lead`

---

## Public API hardening checklist

### 1) CORS allowlist
Set:
- `AE_PUBLIC_CORS_ORIGINS="https://example.com,https://www.example.com"`

Do NOT leave `*` in production unless you understand the risk.

### 2) Rate limiting
App-level (single-process only):
- `AE_LEAD_RL_PER_MIN=30`
- `AE_LEAD_RL_BURST=60`

Edge-level (recommended):
- Apply per-IP or per /24 limits.
- Block obvious bot UAs and high-frequency POSTs.

**Important:** if you run multiple workers, the in-app limiter becomes **per worker**.
In production prefer:
- Nginx/Cloudflare rate limiting, or
- Redis-backed limiter (future enhancement).

### 3) WAF / bot protection
- Block known bad ASNs if relevant
- Challenge suspicious traffic (JS challenge / managed challenge)
- Enforce HTTPS, HSTS

### 4) Payload size limits
At the edge:
- limit request body (e.g. 32KB) for `/lead`

---

## Nginx example snippets

### Public API upstream + rate limit
```nginx
# 10 requests/minute with burst 20 per IP
limit_req_zone $binary_remote_addr zone=lead_zone:10m rate=10r/m;

server {
  listen 443 ssl;
  server_name public.example.com;

  location = /lead {
    limit_req zone=lead_zone burst=20 nodelay;
    client_max_body_size 32k;

    proxy_pass http://127.0.0.1:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}
```

### Console host with allowlisted IPs
```nginx
server {
  listen 443 ssl;
  server_name ops.example.com;

  # allow VPN / office IPs only (example)
  allow 203.0.113.0/24;
  deny all;

  location / {
    proxy_pass http://127.0.0.1:8000;
  }
}
```

---

## Process model

### Run locally (dev)
- Console:
  - `ae run-console --host 127.0.0.1 --port 8000 --reload`
- Public API:
  - `ae run-public --host 127.0.0.1 --port 8001 --reload`

### systemd service examples

`/etc/systemd/system/ae-public.service`
```ini
[Unit]
Description=Acquisition Engine Public API
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/acq_engine
Environment=AE_PUBLIC_CORS_ORIGINS=https://example.com
Environment=AE_LEAD_RL_PER_MIN=30
Environment=AE_LEAD_RL_BURST=60
ExecStart=/opt/acq_engine/.venv/bin/ae run-public --host 127.0.0.1 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/ae-console.service`
```ini
[Unit]
Description=Acquisition Engine Operator Console
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/acq_engine
ExecStart=/opt/acq_engine/.venv/bin/ae run-console --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Observability (minimum)
- Log: request rate, 4xx/5xx counts, lead spam rate
- Alert: spikes in 429s, spikes in /lead traffic, console auth failures

---

## Security notes
- Keep console secret/auth out of client-side code.
- Prefer separate hosts if you can.
- Treat `/lead` as untrusted input; keep validating + truncating fields.
