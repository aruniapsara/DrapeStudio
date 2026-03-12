# DrapeStudio — Tester / Customer Guide

## Quick Reference

| Item | Details |
|------|---------|
| **App URL** | `http://localhost:8888` |
| **Login Page** | `http://localhost:8888/login` |
| **Pricing Page** | `http://localhost:8888/pricing` |

---

## 1. Getting Started

### 1.1 Opening the App

Open your browser and go to: **http://localhost:8888**

You'll see the DrapeStudio home page with module cards for Adults, Kids, Accessories, and Virtual Fit-On.

### 1.2 Logging In

Go to **http://localhost:8888/login**. You have three options:

#### Option A: Google Login (Recommended)
1. Click **Sign in with Google**
2. Choose your Google account
3. You'll be redirected back to DrapeStudio

#### Option B: Phone OTP
1. Enter your Sri Lankan mobile number (e.g., `071 234 5678`)
2. Click **Send Verification Code**
3. Enter the 6-digit OTP you receive
4. Click **Verify & Login**

> **For testing:** If SMS is not configured, the OTP code is printed to the server console/logs.

#### Option C: Dev Login (Development Only)
If Google OAuth is not configured, you'll see a **"Dev Login (No OAuth)"** button. Click it to auto-login as a test user (`dev@drapestudio.local`).

#### Legacy Test Credentials
If using the legacy cookie-based login:

| Username | Password | Role |
|----------|----------|------|
| `tester` | `Fa#shion$2026` | tester (unlimited free) |
| `aruni` | `Fashion#2026` | admin |

### 1.3 First-Time Users

When you register for the first time, you automatically get:
- **5 free image generations** (trial)
- **1 free Virtual Fit-On** attempt
- **7-day trial period**

After the trial, you'll need to reload your wallet.

---

## 2. Navigation

The app has a **bottom navigation bar** (mobile) or **sidebar** (desktop):

| Tab | Icon | Where It Goes |
|-----|------|--------------|
| **Home** | 🏠 | Main dashboard with modules |
| **Kids** | 👕 | Children's clothing module |
| **Create** | ✨ | Upload garment (center button) |
| **Accessories** | 👜 | Jewelry, bags, etc. |
| **Profile** | 👤 | Your account & wallet |

Additional pages accessible from menus:
- **History** — View all past generations
- **Pricing** — Wallet reload packages
- **Fit-On** — Virtual fitting module

---

## 3. Creating Images — Step by Step

### 3.1 Adult Fashion Module

This is the main module for generating catalogue-quality images of adult clothing on AI models.

**Step 1: Upload your garment**
1. Click **Create** (center button) or the **Adult Fashion** card on Home
2. You'll land on the upload page
3. **Drag & drop** 1–5 photos of your garment, or tap **Browse** to select files
4. Tips for best results:
   - Use good lighting
   - Plain background works best
   - Show the full garment
5. Click **Continue**

**Step 2: Configure the model**
1. **Model Appearance:**
   - Age range (e.g., 20s, 30s, 40s)
   - Gender (female, male)
   - Skin tone (light, medium, tan, dark)
   - Body type (slim, average, plus)
2. **Scene Settings:**
   - Background/environment (studio white, lifestyle, outdoor, etc.)
   - Pose preset (standing front, walking, casual, etc.)
   - Framing (full body, three-quarter, upper body)

**Step 3: Select views & quality**
1. **Views** — Choose which angles to generate:
   - ✅ **Front** (required, always included)
   - ☐ **Side** (optional)
   - ☐ **Back** (optional)
   - Each view = 1 image
2. **Quality** — Choose resolution:
   - **Standard (1K)** — Rs. 40/image — Best for social media
   - **HD (2K)** — Rs. 60/image — Best for online shops
   - **Ultra (4K)** — Rs. 100/image — Best for print
3. The **estimated cost** is shown before you confirm

**Step 4: Review & Generate**
1. Review your settings on the summary screen
2. You'll see the total cost (e.g., "This will cost Rs. 120" for 3 front views at 1K)
3. Click **Generate Images**
4. Wait ~60 seconds while AI creates your images

**Step 5: View & Download**
1. Your 3 generated images appear in a grid
2. Click any image to view full-size
3. Click **Download All** to get a ZIP file
4. Share directly to **WhatsApp** or **Facebook**

### 3.2 Kids Clothing Module

1. Click **Kids** in the bottom nav or the Kids card on Home
2. Select the **age group**: Baby, Toddler, Kid, or Teen
3. Upload your children's garment (1–5 photos)
4. Configure child model: gender, hair, expression, skin tone
5. Select scene: pose style, background
6. Choose views & quality (same pricing as adult)
7. Review, generate, and download

### 3.3 Accessories Module

1. Click **Accessories** in the bottom nav
2. Choose the **category**: Necklace, Earrings, Bracelets, Rings, Bags, Hats, etc.
3. Upload your accessory image
4. Select **display mode**:
   - **On Model** — Shown worn by an AI model
   - **Flat Lay** — Product displayed on a styled surface
   - **Lifestyle** — In-context lifestyle setting
5. Configure context, model skin tone, background
6. Choose quality
7. Review, generate, and download

### 3.4 Virtual Fit-On Module

The Fit-On module shows how a garment will look on a specific person.

1. Go to **Fit-On** from the bottom nav or Home
2. **Upload the garment** image
3. **Enter customer details:**
   - Upload a customer photo (selfie/full body)
   - Body measurements (cm): Bust/Chest, Waist, Hips, Height, Shoulder Width
   - Fit preference: Slim, Regular, or Loose
   - Garment size label (XS, S, M, L, XL, XXL, 3XL)
4. Click **Generate Fit-On**
5. Results include:
   - **2 fit-on variation images**
   - **Recommended size** (e.g., "L")
   - **Fit confidence** percentage
   - **Fit details** per measurement (bust: good, waist: tight, etc.)

**Pricing:** Rs. 80 per Fit-On generation (premium users: unlimited free).

---

## 4. Wallet & Payments

### 4.1 Checking Your Balance

Your wallet balance is shown in three places:
- **Header bar** (desktop) — top-right, green pill
- **Sidebar** (desktop) — bottom, above your profile
- **Mobile header** — green chip next to your avatar

Click any of these to go to the Pricing page.

### 4.2 How Billing Works

DrapeStudio uses a **prepaid wallet** (like a mobile phone reload):

1. **Load money** into your wallet
2. **Each image** deducts the cost based on quality
3. **Balance never expires** — use it whenever you want
4. **No monthly fees** — pay only when you need

### 4.3 Image Costs

| Quality | Resolution | Cost per Image |
|---------|-----------|---------------|
| Standard (1K) | 1024px | **Rs. 40** |
| HD (2K) | 2048px | **Rs. 60** |
| Ultra (4K) | 4096px | **Rs. 100** |
| Fit-On | 1024px | **Rs. 80** |

**Example:** Generating Front + Side + Back at HD quality = 3 images × Rs. 60 = **Rs. 180**

### 4.4 Reloading Your Wallet

1. Go to **http://localhost:8888/pricing** (or click your balance)
2. Choose a reload package:

| Package | You Pay | Bonus | Wallet Gets |
|---------|---------|-------|------------|
| **Starter** | Rs. 500 | — | Rs. 500 |
| **Popular** | Rs. 1,000 | +Rs. 100 | Rs. 1,100 |
| **Value** | Rs. 2,500 | +Rs. 350 | Rs. 2,850 |
| **Bulk** | Rs. 5,000 | +Rs. 1,000 | Rs. 6,000 |

3. Click **Pay Now** on your chosen package
4. Complete payment via **PayHere** (Visa, Mastercard, bank transfer)
5. Your wallet is credited instantly after payment

### 4.5 Premium Subscription

For heavy users, there's a **Premium** plan:

| | Details |
|---|--------|
| **Price** | Rs. 5,000/month |
| **Monthly balance** | Rs. 8,000 loaded to wallet |
| **Fit-On** | Unlimited (free) |
| **Queue** | Priority processing |
| **Watermark** | Removed |

Subscribe from the Pricing page. Auto-renews monthly via PayHere.

### 4.6 Transaction History

View all wallet activity at **Profile** → **Transaction History**:
- **Top Up** — Money added via PayHere
- **Image Generated** — Cost deducted per image
- **Refund** — Money returned for failed generations
- **Trial** — Free trial images used

---

## 5. Viewing History

1. Go to **History** from the sidebar or profile menu
2. Browse all your past generations
3. **Filter by:**
   - Module: Adult, Kids, Accessories, Fit-On
   - Status: Succeeded, Failed, Running, Queued
4. Click any generation to view/download results
5. Failed generations show the error reason — and your wallet is automatically refunded

---

## 6. Profile & Settings

Go to **Profile** (bottom nav → Me icon):

### What You Can Do:
- **Edit display name**
- **View wallet balance** and trial status
- **Change language**: English 🇬🇧, Sinhala 🇱🇰, Tamil 🇱🇰
- **View billing history**
- **Toggle notifications** (SMS, Push)
- **See account stats**: Total generations, join date, last login

### Changing Language

1. Go to Profile
2. Tap **Language** / **භාෂාව** / **மொழி**
3. Choose:
   - **English**
   - **සිංහල** (Sinhala)
   - **தமிழ்** (Tamil)
4. The entire app switches to your chosen language instantly

---

## 7. Testing Checklist (For QA Testers)

Use this checklist when testing DrapeStudio features:

### Authentication
- [ ] Login via Google OAuth works
- [ ] Login via Phone OTP works (check server logs for OTP code)
- [ ] Dev Login button appears when OAuth is not configured
- [ ] Logout clears session properly
- [ ] First-time user gets 5 trial images + 1 trial fit-on

### Wallet & Billing
- [ ] New user sees trial badge and "5 free images remaining"
- [ ] Trial countdown shows correct expiry date (7 days from signup)
- [ ] Wallet balance displays correctly in header, sidebar, and mobile
- [ ] After 5 trial images, user is prompted to reload wallet
- [ ] Each image generation deducts the correct amount (Rs. 40 / 60 / 100)
- [ ] Fit-On deducts Rs. 80 per generation
- [ ] PayHere payment flow opens correctly
- [ ] Wallet is credited after successful PayHere payment
- [ ] Bonus amounts are applied correctly per package
- [ ] Failed generations are automatically refunded
- [ ] "Balance never expires" — verify old balances still work

### Image Generation — Adults
- [ ] Upload page accepts 1–5 images (JPG, PNG, WebP)
- [ ] Upload rejects files > size limit
- [ ] Configure page shows all model/scene options
- [ ] Views selection: Front (required), Side (optional), Back (optional)
- [ ] Quality selector shows prices: Rs. 40 / Rs. 60 / Rs. 100
- [ ] Estimated cost updates live when changing views/quality
- [ ] Review page shows correct summary
- [ ] Generation starts and shows progress/polling screen
- [ ] Results display 3 images (or number matching selected views)
- [ ] Download All creates a ZIP file
- [ ] WhatsApp / Facebook share buttons work

### Image Generation — Kids
- [ ] Age group selection works (Baby/Toddler/Kid/Teen)
- [ ] Upload and configuration flow completes
- [ ] Generated images show appropriate child models

### Image Generation — Accessories
- [ ] Category selection works (Necklace, Earrings, etc.)
- [ ] Display mode selection works (On Model, Flat Lay, Lifestyle)
- [ ] Generated images match the chosen display mode

### Virtual Fit-On
- [ ] Garment upload works
- [ ] Customer photo upload works
- [ ] Measurement inputs accept valid values
- [ ] Size recommendation is displayed
- [ ] Fit confidence percentage is shown
- [ ] 2 fit-on variations are generated
- [ ] Costs Rs. 80 per attempt (free for premium/trial)

### Trilingual UI
- [ ] Switch to Sinhala — all text changes to Sinhala
- [ ] Switch to Tamil — all text changes to Tamil
- [ ] Switch back to English — all text reverts
- [ ] Pricing page shows correct currency format per language:
  - English: Rs. 1,000
  - Sinhala: රු. 1,000
  - Tamil: ரூ. 1,000
- [ ] Wallet balance format matches selected language

### History
- [ ] All past generations appear
- [ ] Filters work (module, status)
- [ ] Can view and download past results
- [ ] Failed generations show error message

### Profile
- [ ] Display name is editable
- [ ] Language switcher works
- [ ] Wallet info is accurate
- [ ] Transaction history loads

### Edge Cases
- [ ] Generating with zero wallet balance shows "Insufficient balance" error
- [ ] Uploading an invalid file type shows an error
- [ ] Network interruption during generation shows appropriate error
- [ ] Refreshing the generation page resumes polling (doesn't create a duplicate)
- [ ] Concurrent generations from same user don't conflict

### Tester Account
- [ ] Tester role gets unlimited free generations (no wallet deduction)
- [ ] Tester can access all modules
- [ ] Tester sees no "insufficient balance" errors

### Sponsored Account
- [ ] Sponsored user gets free generations
- [ ] After sponsor end date, user is charged normally

---

## 8. Common Issues & Fixes

| Issue | What to Do |
|-------|-----------|
| **"Not authenticated"** | Your session expired. Log in again at `/login`. |
| **"Insufficient balance"** | Your wallet is empty. Go to `/pricing` to reload. |
| **Generation stuck at "Running"** | Wait up to 2 minutes. If still stuck, check History — it may have failed silently. Your wallet will be refunded. |
| **Images look wrong** | Try different model/scene settings. Better garment photos (flat, well-lit, plain background) give better results. |
| **Can't change language** | Go to Profile → Language and select your preferred language. Refresh the page if it doesn't update. |
| **PayHere payment failed** | Try again or use a different payment method. If money was deducted but wallet not credited, contact admin. |
| **OTP not received** | In development, OTP is logged to the server console, not sent via SMS. Ask the admin for the code. |

---

## 9. Tips for Best Results

### Garment Photos
- **Good lighting** — natural light or well-lit indoor
- **Plain background** — white or single color works best
- **Full garment visible** — don't crop off sleeves or hemlines
- **Multiple angles** — upload front, back, and detail shots
- **Flat lay or hanger** — both work, flat lay is slightly better

### Choosing Settings
- **Standard (1K)** is perfect for Instagram, Facebook, and WhatsApp catalogue sharing
- **HD (2K)** is ideal for Shopee, Daraz, or your own website
- **Ultra (4K)** is for print catalogues and large format displays
- **Front view** is required; add Side and Back for complete product listings

### Saving Money
- Start with **Standard quality** to test — you can always regenerate at higher quality
- Use the **Popular package** (Rs. 1,000 + Rs. 100 bonus) for the best value
- **Front-only** at Standard = just Rs. 40 per garment

---

*DrapeStudio Tester Guide — v2.0 — March 2026*
