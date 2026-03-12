# DrapeStudio — Admin Guide

## Quick Reference

| Item | Details |
|------|---------|
| **App URL** | `http://localhost:8888` |
| **Admin Login** | `http://localhost:8888/admin/login` |
| **Admin Dashboard** | `http://localhost:8888/admin/dashboard` |

---

## 1. Getting Started

### 1.1 Logging In

1. Open your browser and go to **http://localhost:8888/admin/login**
2. Enter your admin **email** and **password**
3. Click **Sign In**

> **First-time setup?** Create an admin account by running this command inside the Docker container:
> ```bash
> docker compose exec api python -m app.cli create-admin \
>   --email admin@drapestudio.lk \
>   --password YourSecurePassword \
>   --name "Admin Name"
> ```

**Legacy dev credentials** (backward-compatible):
| Username | Password | Role |
|----------|----------|------|
| `aruni` | `Fashion#2026` | admin |
| `tester` | `Fa#shion$2026` | tester |

Your admin session lasts **8 hours**. After that, you'll be asked to log in again.

### 1.2 Logging Out

Click your avatar in the top-right corner and select **Logout**, or go to `http://localhost:8888/admin/logout`.

---

## 2. Admin Dashboard

**URL:** `/admin/dashboard`

The dashboard shows real-time stats for the entire platform:

### At-a-Glance Stats
- **Total Users** — All registered users
- **Users Today / This Week / This Month** — Signup trends
- **Active Users** — Users active in the last 7 days
- **Total Generations** — All image generations ever created
- **Generations Today / This Week** — Recent generation activity
- **Revenue This Month** — Sum of wallet top-ups (LKR)
- **Active Trials** — Users currently on a free trial
- **Premium Users** — Users with active premium subscriptions

### Charts
- **30-Day Signup Trend** — Daily new user registrations
- **30-Day Generation Trend** — Daily generation counts

---

## 3. User Management

**URL:** `/admin/users`

### 3.1 Browsing Users

The user list shows all registered accounts with:
- Name, email, phone
- Role (user / admin / tester)
- Wallet balance (LKR)
- Total generations
- Last login date

**Search:** Type a name or email in the search box to filter.

**Filter by:**
- Role: `user`, `admin`, `tester`
- Sponsored: `yes` / `no`

**Sort by:** Creation date, display name, or last login.

**Pagination:** 25 users per page.

### 3.2 User Detail Page

Click any user row to see their full profile at `/admin/users/{user_id}`.

**What you can see:**
- Full user info (name, email, phone, avatar, language, role)
- Wallet balance, total loaded, total spent
- Trial status (images used, expiry date)
- Premium status
- Last 20 wallet transactions
- Last 20 generation requests (with module, status, and errors)

### 3.3 Admin Actions on a User

From the user detail page, you can:

| Action | What It Does |
|--------|-------------|
| **Grant Credits** | Add LKR to the user's wallet. Enter amount + reason. |
| **Toggle Sponsored** | Enable/disable sponsored status. Set sponsor name and end date. Sponsored users get free generations. |
| **Update Notes** | Add internal admin notes about the user. |
| **Change Role** | Set role to `user`, `admin`, `tester`, or `inactive`. |
| **Deactivate/Reactivate** | Temporarily disable or re-enable the account. |
| **Delete User** | Soft-delete: clears personal info, sets role to "deleted". **Irreversible.** |

> **Every admin action is logged** in the audit trail with your admin ID, the action type, and a timestamp.

---

## 4. Wallet Management

**URL:** `/admin/wallet`

### 4.1 Overview

The wallet page shows all users with their wallet details:
- Current balance (LKR)
- Total loaded (lifetime)
- Total spent (lifetime)
- Trial images used
- Premium status

**Search:** Filter by name or phone number.

### 4.2 Granting Credits

1. Go to `/admin/wallet` or the user detail page
2. Click **Grant Credits**
3. Enter the amount in LKR
4. Enter a reason (e.g., "Compensation for failed generation")
5. Click **Confirm**

The credits appear instantly in the user's wallet, and a `admin_grant` transaction is recorded.

### 4.3 Refunding a Failed Generation

If a generation failed after the user was charged:

1. Go to the user's detail page
2. Find the failed generation in the "Recent Generations" list
3. Click **Refund** next to it

The original image cost is returned to the user's wallet as a `refund` transaction.

> **Note:** The worker automatically refunds failed generations. Manual refund is for edge cases.

### 4.4 Wallet Stats

The wallet management page includes aggregate statistics:
- Total users with wallets
- Total LKR loaded across all users
- Total LKR spent across all users
- Total transaction count
- Active trial users
- Premium subscribers

---

## 5. Usage Reports

**URL:** `/admin/usage`

### 5.1 Viewing Reports

The usage report shows all generation requests with:
- Generation ID
- User / Session ID
- Status (queued / running / succeeded / failed)
- AI model used
- Input/output tokens
- Estimated cost (USD)
- Duration (ms)
- Error message (if failed)

### 5.2 Filtering

- **Date Range:** Set "From" and "To" dates
- **Status:** Filter by queued, running, succeeded, or failed

### 5.3 Exporting

Click **Export CSV** or **Export JSON** to download the filtered report.

---

## 6. Understanding the Billing System

DrapeStudio uses a **wallet-based prepaid** model (like a mobile phone reload):

### Image Pricing

| Quality | Resolution | Cost per Image (LKR) |
|---------|-----------|---------------------|
| Standard (1K) | 1024px | Rs. 40 |
| HD (2K) | 2048px | Rs. 60 |
| Ultra (4K) | 4096px | Rs. 100 |
| Fit-On | 1024px | Rs. 80 |

### Wallet Packages

| Package | Price (LKR) | Bonus | Total Balance |
|---------|------------|-------|--------------|
| Starter | Rs. 500 | — | Rs. 500 |
| Popular | Rs. 1,000 | +Rs. 100 | Rs. 1,100 |
| Value | Rs. 2,500 | +Rs. 350 | Rs. 2,850 |
| Bulk | Rs. 5,000 | +Rs. 1,000 | Rs. 6,000 |

### Special Account Types

| Type | How It Works |
|------|-------------|
| **Trial** | 5 free images + 1 free fit-on for 7 days after signup |
| **Tester** | Role = "tester". Unlimited free generations. No wallet deduction. |
| **Sponsored** | `is_sponsored = true`. Free generations until `sponsored_until` date. |
| **Premium** | Rs. 5,000/month. Gets Rs. 8,000 wallet balance. Unlimited fit-on, priority queue, no watermark. |

### Billing Priority (checked in this order)

1. Admin/Tester role → free
2. Sponsored account → free (until expiry)
3. Active trial → free (up to 5 images)
4. Premium + fit-on → unlimited
5. Premium wallet balance → deduct from premium allocation
6. Prepaid wallet balance → deduct from wallet

---

## 7. Creating Tester & Sponsored Accounts

### Setting Up a Tester

1. Go to `/admin/users`
2. Find the user (or ask them to register first)
3. Click their row to open the detail page
4. Click **Change Role** → select **tester**
5. Confirm

The user now has unlimited free generations.

### Setting Up a Sponsored Account

1. Go to the user's detail page
2. Click **Toggle Sponsored**
3. Enter the sponsor name (e.g., "Fashion Week 2026")
4. Set the sponsorship end date
5. Confirm

The user gets free generations until the end date. After expiry, they'll need to use their wallet.

---

## 8. Troubleshooting

| Issue | Solution |
|-------|----------|
| Admin login not working | Verify the admin was created via CLI. Check that `admin_password_hash` exists in the database. |
| User can't generate images | Check their wallet balance at `/admin/users/{id}`. Grant credits if needed. |
| Generation stuck in "running" | Check the worker container logs: `docker compose logs worker --tail=50` |
| PayHere top-up not crediting | Check `/admin/wallet` for the transaction. Verify PayHere notify endpoint received the callback. |
| "Insufficient balance" for tester | Verify their role is set to "tester" (not "user"). |

### Useful Docker Commands

```bash
# View API logs
docker compose logs api --tail=50

# View worker logs
docker compose logs worker --tail=50

# Rebuild & restart after code changes
docker compose build api worker && docker compose up -d api worker

# Run database migrations
docker compose exec api alembic upgrade head

# Create a new admin
docker compose exec api python -m app.cli create-admin \
  --email admin@drapestudio.lk --password YourPassword --name "Admin"
```

---

*DrapeStudio Admin Guide — v2.0 — March 2026*
