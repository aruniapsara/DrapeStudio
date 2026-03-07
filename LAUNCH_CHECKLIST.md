# DrapeStudio v2 Launch Checklist

## Infrastructure
- [ ] PostgreSQL database provisioned (Render / Fly.io / Supabase)
- [ ] Redis server configured (Render Redis / Upstash)
- [ ] Domain `drapestudio.lk` pointed to server IP
- [ ] SSL certificate installed (cert.pem + key.pem in `./certs/`)
- [ ] Nginx reverse proxy configured (`nginx.conf` reviewed and deployed)
- [ ] Docker images built: `docker-compose -f docker-compose.prod.yml build`
- [ ] Production Docker Compose starts cleanly: `docker-compose -f docker-compose.prod.yml up -d`
- [ ] Environment variables set in `.env` (all production values, no defaults)

## External Services
- [ ] OpenRouter API key (production tier, sufficient credits)
- [ ] Notify.lk SMS credentials (`NOTIFY_LK_USER_ID`, `NOTIFY_LK_API_KEY`, `NOTIFY_LK_SENDER_ID`)
- [ ] PayHere merchant ID + secret (`PAYHERE_SANDBOX=false` for production)
- [ ] Google Analytics 4 measurement ID (`GA4_MEASUREMENT_ID=G-XXXXXXXXXX`)
- [ ] Sentry DSN for server + client (`SENTRY_DSN`, `SENTRY_DSN_JS`)
- [ ] VAPID keys for push notifications (`VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`)
- [ ] JWT secret rotated from default (`JWT_SECRET` — generate with `python -c "import secrets; print(secrets.token_hex(32))"`)

## Database
- [ ] Alembic migrations applied: `docker-compose exec api alembic upgrade head`
- [ ] Confirm migration 009 (indexes) applied successfully
- [ ] Database backups configured (automated daily snapshots)
- [ ] Connection pooling set for PostgreSQL

## Testing
- [ ] All pytest tests pass: `docker-compose exec api pytest tests/ -v`
- [ ] Manual: Adult generation flow (upload → configure → generate → results → download)
- [ ] Manual: Children generation flow (all 4 age groups: baby, toddler, kid, teen)
- [ ] Manual: Accessories generation flow (at least 3 categories, all display modes)
- [ ] Manual: Virtual Fit-On flow (measurements → reference photo → fitted image)
- [ ] Manual: Phone OTP login (real phone, receives SMS)
- [ ] Manual: PayHere payment (sandbox environment, test card)
- [ ] Manual: Language switching (EN → SI → TA, persists across pages)
- [ ] Manual: Push notification (subscribe in profile, trigger generation, receive push)
- [ ] Manual: WhatsApp share link from results page
- [ ] Mobile: iPhone SE (375px) — all critical flows
- [ ] Mobile: Samsung Galaxy (412px) — all critical flows
- [ ] Tablet: iPad (768px)
- [ ] Desktop: 1280px+
- [ ] Lighthouse Performance score ≥ 80 (`chrome://extensions` → Lighthouse)
- [ ] Lighthouse Accessibility score ≥ 90
- [ ] Lighthouse PWA score ≥ 80
- [ ] Check `/health/detailed` returns `status: ok` in production

## Security
- [ ] `APP_ENV=production` set (enables HTTPS redirect, strict CORS)
- [ ] CORS restricted to `BASE_URL` (not `"*"`)
- [ ] Rate limiting active (check `/api/v1/auth/otp/request` — max 5/minute)
- [ ] Security headers present: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- [ ] `HSTS` header active (set by Nginx `Strict-Transport-Security`)
- [ ] PayHere webhook URL whitelisted in PayHere dashboard
- [ ] No secrets committed to Git (run `git log -p | grep -i "api_key\|secret\|password"`)

## Content & SEO
- [ ] Privacy Policy page (`/privacy`) — link from footer
- [ ] Terms of Service page (`/terms`) — link from footer
- [ ] About page (`/about`) or update home hero with real copy
- [ ] WhatsApp business number updated in `base.html` (replace `94XXXXXXXXX`)
- [ ] Social media links updated in `home.html` footer (Facebook, Instagram, TikTok URLs)
- [ ] OG image created at 1200×628px and saved to `app/static/og-image.png`
- [ ] PWA icons verified: `app/static/icon-192.png` and `app/static/icon-512.png`
- [ ] `robots.txt` sitemap URL updated to production domain
- [ ] Google Search Console: submit sitemap `https://drapestudio.lk/sitemap.xml`
- [ ] GA4: verify events firing (generation_start, generation_complete, download_image)
- [ ] Sentry: trigger a test error and confirm it appears in Sentry dashboard

## Monitoring & Alerting
- [ ] Uptime monitor configured (UptimeRobot / Better Stack) — ping `/health`
- [ ] Sentry alert rules set (email on new issues, P1 errors → immediate alert)
- [ ] GA4 dashboard set up (daily active users, generation funnel, revenue)
- [ ] Log aggregation configured (Render logs / Datadog / Logtail)
- [ ] Daily cost limit in effect (`DAILY_COST_LIMIT_USD=10.00` or higher for production)

## Post-Launch
- [ ] Announce on social media (Facebook, Instagram, TikTok)
- [ ] Submit to Sri Lankan business directories
- [ ] Monitor `/metrics` endpoint for early usage patterns
- [ ] Review Sentry for any production errors in first 24 hours
- [ ] Check GA4 for traffic and conversion funnel in first 48 hours
