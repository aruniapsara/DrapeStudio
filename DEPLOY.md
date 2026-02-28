# Deploy DrapeStudio to Hostinger VPS

**Target URL:** https://drapestudio.demostudio.cc
**Repository:** https://github.com/aruniapsara/DrapeStudio

---

## Prerequisites

The VPS must have:
- Ubuntu 22.04+ (or any Debian-based Linux)
- Docker Engine 24+ and Docker Compose v2
- Nginx (for reverse proxy + SSL)
- Certbot (for Let's Encrypt SSL)
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

## Step 1: Clone the Repository

```bash
cd /opt
sudo git clone https://github.com/aruniapsara/DrapeStudio.git
sudo chown -R $USER:$USER /opt/DrapeStudio
cd /opt/DrapeStudio
```

---

## Step 2: Create the `.env` File

```bash
cp .env.example .env
nano .env
```

Set these values in `.env`:

```bash
APP_ENV=production
SECRET_KEY=<generate-a-random-string-here>

# Database (SQLite is fine for single-server)
DATABASE_URL=sqlite:///./drapestudio.db

# Redis (Docker internal)
REDIS_URL=redis://localhost:6379

# OpenRouter API key (REQUIRED for image generation)
OPENROUTER_API_KEY=<your-openrouter-api-key>
OPENROUTER_MODEL=google/gemini-3.1-flash-image-preview

# Storage
STORAGE_BACKEND=local
STORAGE_ROOT=./storage

# Cost controls
DAILY_COST_LIMIT_USD=10.00
```

> **Important:** You MUST set a real `OPENROUTER_API_KEY` for image generation to work. Get one from https://openrouter.ai/keys

To generate a random SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Step 3: Create the Production Docker Compose Override

Create `docker-compose.prod.yml`:

```bash
cat > docker-compose.prod.yml << 'EOF'
version: "3.9"
services:

  redis:
    image: redis:7-alpine
    restart: always
    ports: []
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
EOF
```

Key differences from dev:
- No source code volume mount (uses built image)
- No `--reload` flag (production mode)
- `--workers 2` for better concurrency
- Binds to `127.0.0.1:8000` (only accessible via Nginx, not directly)
- `restart: always` for auto-recovery
- Redis port not exposed externally

---

## Step 4: Create Data Directories

```bash
cd /opt/DrapeStudio
mkdir -p data/storage/uploads data/storage/outputs data/db
```

---

## Step 5: Build and Start the Containers

```bash
cd /opt/DrapeStudio
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

Verify all 3 containers are running:
```bash
docker compose -f docker-compose.prod.yml ps
```

You should see `api`, `worker`, and `redis` all in `running` state.

Test the API is responding:
```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/login
# Should return: 200
```

---

## Step 6: Configure Nginx Reverse Proxy

### 6a. Point DNS

In your Hostinger DNS settings (or wherever `demostudio.cc` DNS is managed), create an **A record**:

| Type | Name | Value |
|------|------|-------|
| A | drapestudio | `<VPS-IP-ADDRESS>` |

Wait for DNS propagation (can take up to a few minutes).

### 6b. Create Nginx config

```bash
sudo nano /etc/nginx/sites-available/drapestudio
```

Paste this:

```nginx
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

        # WebSocket support (for HTMX SSE if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for image generation (can take 30-60s)
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/drapestudio /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6c. Install SSL Certificate

```bash
sudo certbot --nginx -d drapestudio.demostudio.cc
```

Follow the prompts. Certbot will:
- Obtain a Let's Encrypt certificate
- Auto-configure Nginx for HTTPS
- Set up auto-renewal

---

## Step 7: Verify Deployment

1. Open https://drapestudio.demostudio.cc in a browser
2. You should see the login page with the DrapeStudio logo
3. Login with credentials:
   - **Admin:** username `aruni`, password `Fashion#2026`
   - **Tester:** username `tester`, password `Fa#shion$2026`
4. Test the full flow: Upload garment images, configure model, generate

---

## Maintenance Commands

### View logs
```bash
cd /opt/DrapeStudio
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f worker
```

### Restart services
```bash
cd /opt/DrapeStudio
docker compose -f docker-compose.prod.yml restart
```

### Pull updates and redeploy
```bash
cd /opt/DrapeStudio
git pull origin main
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### Stop everything
```bash
cd /opt/DrapeStudio
docker compose -f docker-compose.prod.yml down
```

### Backup database
```bash
cp /opt/DrapeStudio/data/db/drapestudio.db /opt/DrapeStudio/data/db/drapestudio.db.backup-$(date +%Y%m%d)
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 502 Bad Gateway | Check if containers are running: `docker compose -f docker-compose.prod.yml ps` |
| Login page doesn't load | Check API logs: `docker compose -f docker-compose.prod.yml logs api` |
| Image generation fails | Check worker logs and verify `OPENROUTER_API_KEY` is set in `.env` |
| SSL certificate error | Run `sudo certbot renew --dry-run` to test renewal |
| Port 8000 already in use | Check: `sudo lsof -i :8000` and stop the conflicting process |
| Permission denied on data/ | Run: `sudo chown -R $USER:$USER /opt/DrapeStudio/data` |

---

## Architecture Summary

```
Internet
   |
   v
Nginx (port 443/SSL) --> drapestudio.demostudio.cc
   |
   v
Docker: api (port 8000) -- FastAPI + Jinja2 + HTMX
   |            |
   v            v
Docker: redis   Docker: worker (RQ background jobs)
   |                      |
   v                      v
SQLite DB          OpenRouter/Gemini API
(data/db/)         (image generation)
   |
   v
Local Storage
(data/storage/)
```
