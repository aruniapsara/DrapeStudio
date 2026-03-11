# Deploy DrapeStudio to Hostinger VPS

**Target URL:** https://drapestudio.demostudio.cc
**Repository:** https://github.com/aruniapsara/DrapeStudio (branch: `main`)

---

## Architecture

```
Internet
   |
   v
Nginx (port 443/SSL)  -->  drapestudio.demostudio.cc
   |
   v
Docker: api (port 8000)  -- FastAPI + Jinja2 + HTMX
   |            |
   v            v
Docker: redis   Docker: worker (RQ background jobs)
                           |
                           v
                  Google Gemini API  (image generation)

Persistent volumes:
  ./data/db/           -- SQLite database
  ./data/storage/      -- uploaded garment images + generated outputs
```

---

## Prerequisites

The VPS must have:
- Ubuntu 22.04+ (or any Debian-based Linux)
- Docker Engine 24+ and Docker Compose v2
- Nginx (reverse proxy + SSL)
- Certbot (Let's Encrypt SSL)
- Git

### Install prerequisites (if not already installed)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Nginx and Certbot
sudo apt install -y nginx certbot python3-certbot-nginx git
```

Log out and back in after adding yourself to the docker group.

---

## Step 1 -- Clone the Repository

```bash
cd /opt
sudo git clone https://github.com/aruniapsara/DrapeStudio.git
sudo chown -R $USER:$USER /opt/DrapeStudio
cd /opt/DrapeStudio
```

---

## Step 2 -- Create the `.env` File

```bash
cd /opt/DrapeStudio
cp .env.example .env
nano .env
```

Set these **required** values:

```bash
# -- REQUIRED -------------------------------------------------------

APP_ENV=production
SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_urlsafe(32))">

# Database (SQLite is fine for single-server deployment)
DATABASE_URL=sqlite:///./drapestudio.db

# Redis (Docker internal -- overridden by docker-compose)
REDIS_URL=redis://localhost:6379

# Google Gemini -- REQUIRED for image generation
GOOGLE_API_KEY=<your-google-api-key>
GEMINI_MODEL=gemini-2.0-flash-exp-image-generation
GEMINI_IMAGE_MODEL=gemini-3.1-flash-image-preview

# Storage
STORAGE_BACKEND=local
STORAGE_ROOT=./storage

# JWT authentication
JWT_SECRET=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30

# Google OAuth -- REQUIRED for "Sign in with Google"
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=https://drapestudio.demostudio.cc/auth/callback

# Public URL (used for OAuth callbacks, PayHere, etc.)
BASE_URL=https://drapestudio.demostudio.cc

# Cost controls
DAILY_COST_LIMIT_USD=10.00

# -- OPTIONAL (leave empty to disable) -----------------------------

# PayHere payment gateway (Sri Lanka)
PAYHERE_MERCHANT_ID=
PAYHERE_MERCHANT_SECRET=
PAYHERE_SANDBOX=false

# Web Push notifications (VAPID keys)
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
VAPID_EMAIL=admin@drapestudio.lk

# Google Analytics 4
GA4_MEASUREMENT_ID=

# Sentry error tracking
SENTRY_DSN=
SENTRY_DSN_JS=

# App version
APP_VERSION=2.0.0
```

> **Critical:** `GOOGLE_API_KEY` must be a valid key from https://aistudio.google.com/apikey.
> `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` come from Google Cloud Console -> Credentials -> OAuth 2.0 Client.
> `GOOGLE_REDIRECT_URI` **must** match the authorized redirect URI in Google Cloud Console -- use the production URL.

---

## Step 3 -- Create the Production Docker Compose Override

```bash
cd /opt/DrapeStudio
cat > docker-compose.prod.yml << 'DEOF'
services:

  redis:
    image: redis:7-alpine
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    build: .
    restart: always
    command: >
      sh -c "mkdir -p /app/data/storage/uploads /app/data/storage/outputs /app/data/db &&
             alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./data/storage:/app/data/storage
      - ./data/db:/app/data/db
    env_file: .env
    environment:
      REDIS_URL: redis://redis:6379
      DATABASE_URL: "sqlite:////app/data/db/drapestudio.db"
      STORAGE_ROOT: "/app/data/storage"
    depends_on:
      redis:
        condition: service_healthy

  worker:
    build: .
    restart: always
    command: >
      sh -c "mkdir -p /app/data/storage/uploads /app/data/storage/outputs /app/data/db &&
             rq worker drapestudio --url redis://redis:6379"
    volumes:
      - ./data/storage:/app/data/storage
      - ./data/db:/app/data/db
    env_file: .env
    environment:
      REDIS_URL: redis://redis:6379
      DATABASE_URL: "sqlite:////app/data/db/drapestudio.db"
      STORAGE_ROOT: "/app/data/storage"
    depends_on:
      redis:
        condition: service_healthy
DEOF
```

Key differences from dev `docker-compose.yml`:
- No source code volume mount (uses code baked into Docker image)
- No `--reload` flag (production mode)
- `--workers 2` for concurrency
- API bound to `127.0.0.1:8000` (only accessible via Nginx)
- `restart: always` for auto-recovery
- Redis port not exposed externally

---

## Step 4 -- Create Data Directories

```bash
cd /opt/DrapeStudio
mkdir -p data/storage/uploads data/storage/outputs data/db
```

---

## Step 5 -- Build and Start

```bash
cd /opt/DrapeStudio
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

Verify all 3 containers are running:
```bash
docker compose -f docker-compose.prod.yml ps
```

You should see `api`, `worker`, and `redis` all in **Running** state.

Test the API locally:
```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/login
# Expected: 200
```

---

## Step 6 -- Configure Nginx + SSL

### 6a. Point DNS

In your DNS settings for `demostudio.cc`, create an A record:

| Type | Name          | Value              |
|------|---------------|--------------------|
| A    | drapestudio   | `<VPS-IP-ADDRESS>` |

Wait for DNS propagation (usually 1-5 minutes).

### 6b. Create Nginx config

```bash
sudo tee /etc/nginx/sites-available/drapestudio > /dev/null << 'NEOF'
server {
    listen 80;
    server_name drapestudio.demostudio.cc;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (HTMX SSE)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Image generation can take 30-60s per variation
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
NEOF
```

Enable the site:

```bash
sudo ln -sf /etc/nginx/sites-available/drapestudio /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 6c. Install SSL Certificate

```bash
sudo certbot --nginx -d drapestudio.demostudio.cc
```

Certbot will obtain a Let's Encrypt certificate, configure HTTPS in Nginx, and set up auto-renewal.

---

## Step 7 -- Verify Deployment

1. Open **https://drapestudio.demostudio.cc** in a browser
2. You should see the login page
3. Sign in with Google (or test credentials if seeded)
4. Upload a garment image -> Configure model -> Generate
5. Verify 3 images are generated successfully

---

## Maintenance Commands

### View logs
```bash
cd /opt/DrapeStudio
docker compose -f docker-compose.prod.yml logs -f api      # API logs
docker compose -f docker-compose.prod.yml logs -f worker   # Worker/generation logs
docker compose -f docker-compose.prod.yml logs -f redis    # Redis logs
```

### Pull updates and redeploy
```bash
cd /opt/DrapeStudio
git pull origin main
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### Restart services
```bash
cd /opt/DrapeStudio
docker compose -f docker-compose.prod.yml restart
```

### Stop everything
```bash
cd /opt/DrapeStudio
docker compose -f docker-compose.prod.yml down
```

### Backup database
```bash
cp /opt/DrapeStudio/data/db/drapestudio.db \
   /opt/DrapeStudio/data/db/drapestudio.db.backup-$(date +%Y%m%d)
```

### Run database migrations manually
```bash
cd /opt/DrapeStudio
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 502 Bad Gateway | `docker compose -f docker-compose.prod.yml ps` -- check containers are running |
| Login page doesn't load | `docker compose -f docker-compose.prod.yml logs api --tail=50` |
| Google OAuth fails | Verify `GOOGLE_REDIRECT_URI` in `.env` matches Google Cloud Console exactly |
| Image generation fails | Check worker logs: `docker compose -f docker-compose.prod.yml logs worker --tail=50` |
| "GOOGLE_API_KEY is not configured" | Set `GOOGLE_API_KEY` in `.env` and restart |
| SSL certificate error | `sudo certbot renew --dry-run` |
| Port 8000 already in use | `sudo lsof -i :8000` and stop the conflicting process |
| Permission denied on data/ | `sudo chown -R $USER:$USER /opt/DrapeStudio/data` |
| Database locked errors | Restart: `docker compose -f docker-compose.prod.yml restart api worker` |
