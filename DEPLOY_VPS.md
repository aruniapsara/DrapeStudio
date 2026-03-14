# DrapeStudio — VPS Deployment Guide

Step-by-step instructions to deploy DrapeStudio on an Ubuntu VPS (22.04 or 24.04 LTS).

---

## 1. VPS Requirements

| Resource     | Minimum        | Recommended     |
|-------------|----------------|-----------------|
| CPU         | 2 vCPU         | 4 vCPU          |
| RAM         | 4 GB           | 8 GB            |
| Disk        | 40 GB SSD      | 80 GB SSD       |
| OS          | Ubuntu 22.04+  | Ubuntu 24.04    |
| Open Ports  | 22, 80, 443    | 22, 80, 443     |

Tested providers: DigitalOcean, Hetzner, Linode, Vultr, AWS Lightsail.

---

## 2. Initial Server Setup

SSH into the VPS as root and create a deploy user:

```bash
# Update system
apt update && apt upgrade -y

# Create deploy user
adduser drapestudio
usermod -aG sudo drapestudio

# Set up SSH key auth for the new user
mkdir -p /home/drapestudio/.ssh
cp ~/.ssh/authorized_keys /home/drapestudio/.ssh/
chown -R drapestudio:drapestudio /home/drapestudio/.ssh
chmod 700 /home/drapestudio/.ssh
chmod 600 /home/drapestudio/.ssh/authorized_keys

# Switch to deploy user for remaining steps
su - drapestudio
```

---

## 3. Install Docker & Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Add user to docker group (no sudo needed for docker commands)
sudo usermod -aG docker $USER

# Log out and back in for group change to take effect
exit
# SSH back in as drapestudio

# Verify
docker --version
docker compose version
```

---

## 4. Install Git & Clone Repository

```bash
# Install git
sudo apt install -y git

# Clone repo
cd ~
git clone https://github.com/aruniapsara/DrapeStudio.git
cd DrapeStudio
```

---

## 5. Configure Environment

```bash
# Copy example env
cp .env.example .env

# Edit with your production values
nano .env
```

### Required `.env` changes for production:

```bash
# ── MUST CHANGE ──────────────────────────────────────────────────────
APP_ENV=production

# Generate a strong secret: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<generated-64-char-hex>

# Generate JWT secret: python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=<generated-64-char-hex>

# Google Gemini API key (from https://aistudio.google.com/apikey)
GOOGLE_API_KEY=AIza...your-key-here

# FASHN.ai API key (from https://fashn.ai) — for fit-on module
FASHN_API_KEY=fa-...your-key-here

# Google OAuth (from Google Cloud Console → APIs & Services → Credentials)
GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxx
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/callback

# PayHere (from https://www.payhere.lk/merchants)
PAYHERE_MERCHANT_ID=your-merchant-id
PAYHERE_MERCHANT_SECRET=your-merchant-secret
PAYHERE_SANDBOX=false                    # false for production!

# Public URL (your actual domain)
BASE_URL=https://yourdomain.com

# ── OPTIONAL BUT RECOMMENDED ─────────────────────────────────────────
# Sentry error tracking
SENTRY_DSN=https://xxxx@sentry.io/xxxx
SENTRY_DSN_JS=https://xxxx@sentry.io/xxxx

# Google Analytics
GA4_MEASUREMENT_ID=G-XXXXXXXXXX

# Push notifications (generate keys — see .env.example for command)
VAPID_PRIVATE_KEY=...
VAPID_PUBLIC_KEY=...
VAPID_EMAIL=admin@yourdomain.com

# ── LEAVE AS-IS (Docker Compose overrides these) ─────────────────────
REDIS_URL=redis://redis:6379
STORAGE_BACKEND=local
STORAGE_ROOT=/app/data/storage
DATABASE_URL=sqlite:////app/data/db/drapestudio.db
```

---

## 6. Set Up SSL with Let's Encrypt (Certbot)

Before starting the app, get SSL certificates:

```bash
# Install certbot
sudo apt install -y certbot

# Make sure port 80 is free (stop nginx if running)
sudo systemctl stop nginx 2>/dev/null || true

# Get certificate (replace with your domain)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Create certs directory and symlink
mkdir -p ~/DrapeStudio/certs
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ~/DrapeStudio/certs/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ~/DrapeStudio/certs/key.pem
sudo chown drapestudio:drapestudio ~/DrapeStudio/certs/*
```

---

## 7. Update Nginx Config for Your Domain

Edit `nginx.conf` and replace `drapestudio.lk` with your actual domain:

```bash
cd ~/DrapeStudio
nano nginx.conf
```

Change these lines:
```nginx
server_name yourdomain.com www.yourdomain.com;  # line 34 and 39
```

Also update the static files alias to work with Docker volumes. Replace the `/static/` location block:

```nginx
location /static/ {
    proxy_pass http://api:8000;
    proxy_set_header Host $host;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

---

## 8. Create Data Directories

```bash
cd ~/DrapeStudio
mkdir -p data/storage/uploads data/storage/outputs data/db
```

---

## 9. Build & Start

```bash
cd ~/DrapeStudio

# Build all images
docker compose -f docker-compose.prod.yml build

# Start everything (detached)
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps

# Check logs
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f worker
docker compose -f docker-compose.prod.yml logs -f nginx
```

### Verify it's running:

```bash
# Health check
curl -s http://localhost:8000/health | python3 -m json.tool

# From outside (should redirect to HTTPS)
curl -I http://yourdomain.com
```

---

## 10. Set Up Auto-Restart on Reboot

```bash
# Docker services restart automatically (restart: always in compose)
# But ensure Docker itself starts on boot:
sudo systemctl enable docker
```

---

## 11. SSL Certificate Auto-Renewal

```bash
# Create renewal script
cat << 'EOF' | sudo tee /etc/cron.d/certbot-renew
# Renew Let's Encrypt certs twice daily
0 0,12 * * * root certbot renew --quiet --deploy-hook "cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /home/drapestudio/DrapeStudio/certs/cert.pem && cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /home/drapestudio/DrapeStudio/certs/key.pem && docker compose -f /home/drapestudio/DrapeStudio/docker-compose.prod.yml restart nginx"
EOF
```

---

## 12. Deploying Updates

When you push new code to GitHub:

```bash
cd ~/DrapeStudio

# Pull latest code
git pull origin main

# Rebuild and restart (zero-downtime with rolling update)
docker compose -f docker-compose.prod.yml build api worker
docker compose -f docker-compose.prod.yml up -d api worker

# Verify
docker compose -f docker-compose.prod.yml logs --tail=20 api
```

---

## 13. Useful Commands

```bash
# View all logs
docker compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker compose -f docker-compose.prod.yml logs -f api --tail=50

# Restart a service
docker compose -f docker-compose.prod.yml restart api

# Stop everything
docker compose -f docker-compose.prod.yml down

# Stop and remove volumes (DANGER: deletes data!)
docker compose -f docker-compose.prod.yml down -v

# Shell into api container
docker compose -f docker-compose.prod.yml exec api bash

# Run a Python command in api container
docker compose -f docker-compose.prod.yml exec api python -c "print('hello')"

# Run database migration manually
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# Check disk usage
docker system df
```

---

## 14. Monitoring & Troubleshooting

### Check if services are healthy:
```bash
docker compose -f docker-compose.prod.yml ps
```

### Common issues:

| Problem | Solution |
|---------|----------|
| `502 Bad Gateway` | API not ready yet. Check: `docker compose logs api` |
| `SSL error` | Cert files missing. Re-run certbot step |
| Images not generating | Check worker logs: `docker compose logs worker` |
| Worker stuck | Restart worker: `docker compose restart worker` |
| DB locked (SQLite) | Only 1 writer at a time. For heavy load, switch to PostgreSQL |
| Out of disk | Clean Docker: `docker system prune -a` |

### Health endpoint:
```bash
curl https://yourdomain.com/health
# Returns: {"status": "ok", ...}
```

---

## 15. Backup

```bash
# Backup database and storage
cd ~/DrapeStudio
tar -czf ~/backup-$(date +%Y%m%d).tar.gz data/

# Restore
tar -xzf ~/backup-YYYYMMDD.tar.gz -C ~/DrapeStudio/
```

### Automated daily backup (optional):
```bash
cat << 'EOF' | sudo tee /etc/cron.d/drapestudio-backup
# Daily backup at 2 AM
0 2 * * * drapestudio cd /home/drapestudio/DrapeStudio && tar -czf /home/drapestudio/backups/backup-$(date +\%Y\%m\%d).tar.gz data/ && find /home/drapestudio/backups -mtime +7 -delete
EOF

mkdir -p ~/backups
```

---

## Architecture (Production)

```
                    ┌──────────────┐
   Internet ───────►│  Nginx :443  │
                    │  (SSL + Rate │
                    │   Limiting)  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  FastAPI     │
                    │  :8000       │
                    │  (2 workers) │
                    └──────┬───────┘
                           │
               ┌───────────┼───────────┐
               │           │           │
        ┌──────▼──┐  ┌─────▼────┐ ┌───▼────────┐
        │  Redis  │  │  SQLite  │ │  Storage   │
        │ :6379   │  │  (data/) │ │  (data/)   │
        └─────────┘  └──────────┘ └────────────┘
               │
        ┌──────▼──────┐
        │  RQ Workers │
        │  (x2)       │
        │  → Gemini   │
        │  → FASHN    │
        └─────────────┘
```

---

## Google OAuth Setup for Production

In Google Cloud Console → APIs & Services → Credentials:

1. Edit your OAuth 2.0 Client
2. Add to **Authorized redirect URIs**: `https://yourdomain.com/auth/callback`
3. Add to **Authorized JavaScript origins**: `https://yourdomain.com`
4. Save

---

## PayHere Webhook Setup for Production

In PayHere Merchant Dashboard:

1. Go to Settings → Domain Verification
2. Add your domain: `yourdomain.com`
3. Set Notify URL to: `https://yourdomain.com/api/v1/billing/payhere/notify`

---

*Last updated: March 2026*
