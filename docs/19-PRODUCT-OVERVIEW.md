# 19 — Spark: Product Overview

> **This doc has been split into two focused files:**
> - **`20-MERCHANT-DASHBOARD.md`** → David's file. Business dashboard screens, wireframes, components, Figma direction. Start here.
> - **`21-CONSUMER-APP.md`** → Consumer screens, push notifications, lock screen, widgets, feature inventory.
>
> This file is kept as a combined reference and flow overview.

---

## What Spark Is (One Paragraph)

Spark detects the most relevant moment for a local merchant to reach a nearby user, generates a personalized offer dynamically (not from templates), and makes it redeemable in one tap. The consumer sees an offer card that adapts its entire visual identity — colors, tone, imagery, urgency — to the context. The merchant sees a dashboard that shows when their business is quiet and lets AI handle the campaign automatically. Everything personal stays on the user's device. The cashback lands instantly in their Sparkasse Girokonto.

**The loop:** Payone detects quiet period → composite context built → Gemini Flash generates offer + visual style → card appears on user's phone → user taps accept → QR validates at merchant → cashback credited.

---

## Two Products, One System

| | **Consumer App** | **Merchant Dashboard** |
|---|---|---|
| Platform | Expo / React Native (iOS + Android) | Next.js web app |
| Primary user | Mia — walking through Stuttgart | Café owner — sitting at register or checking phone |
| Core value | Relevant offer at the right moment | Customers during quiet hours |
| Session trigger | Movement + context detected passively | Payone density drop detected |

---

## Consumer App: All Screens

### Screen 1 — Onboarding / Privacy Consent
**When shown:** First launch only.

**What's on screen:**
- Spark logo + tagline "Make every minute local."
- Three-bullet privacy promise (movement stays on device, no GPS to server, instant delete)
- "What Spark sees vs. what stays on your phone" split diagram
- Single CTA: "Let's go" (enables location + motion permissions)
- Secondary: "See exactly what data leaves your phone →" → opens Privacy Ledger preview

**States:** Default → Permission granted → Permission denied (graceful degradation message)

**Design notes:** Warm amber palette. No dark patterns. The privacy framing is a feature, not a disclaimer.

```
┌─────────────────────────────────┐
│  ⚡ Welcome to Spark            │
│  "Make every minute local."     │
│                                 │
│  📍 Location                    │
│  Used to find nearby merchants. │
│  Processed on your device.      │
│  Only a grid area is shared.    │
│  [Allow Location →]             │
│                                 │
│  🏃 Motion & Fitness            │
│  To detect if you're browsing   │
│  or commuting (so we never      │
│  interrupt the wrong moment).   │
│  Processed on your device only. │
│  [Allow Motion →]               │
│                                 │
│  📅 Calendar (Optional)         │
│  To time offers around your     │
│  schedule. Never leaves device. │
│  [Allow ▼] [Skip]               │
│                                 │
│  Your data stays on your phone. │
│  Spark only receives anonymous  │
│  context signals. No PII.       │
│                                 │
│  [Read our Privacy Approach →]  │
│  [Get Started →]                │
└─────────────────────────────────┘
```

**Key copy principles:** Each permission explains the WHY. "Processed on your device" repeated for every sensitive sensor. Calendar is optional — increases trust by not demanding everything.

---

### Screen 2 — Home / Map View
**When shown:** Default state when app is open and user is moving.

```
┌─────────────────────────────────┐
│  ⚡ Spark                    🟢 │  ← Privacy Pulse dot
│                                 │
│         [Map: Stuttgart]        │
│         Innenstadt              │
│                                 │
│  ┌────────────────────────────┐ │
│  │  Wallet Balance: €4.20  ⚡ │ │
│  └────────────────────────────┘ │
│                                 │
│  "Exploring Stuttgart..."       │
│  We'll find your moment.        │
│                                 │
│  [My History]  [Settings]       │
└─────────────────────────────────┘
```

**What's on screen:**
- Mapbox map of Stuttgart city center
- User position dot (not precise — grid-cell level, ~200m radius)
- Nearby merchant pins (only Payone-registered merchants)
- Status bar: current movement mode badge (🚶 Browsing / 🏃 Moving / 🧘 Stationary)
- Privacy Pulse: small green dot (top right) — pulsing = active, tap = Privacy Ledger
- Wallet balance chip (bottom): "⚡ €2.34 Spark Balance"

**States:**
- Idle (no offer) — default
- Offer incoming (card slides up from bottom) — see Screen 3
- Commuting mode — map greyed, badge shows 🚊 "Commuting — Spark paused"
- Exercising mode — 🏃 "Running — Spark paused" (hard block, no offers during exercise)

**Design notes:** Map is ambient, not primary. The offer card IS the primary interaction. Don't over-design the map — it's context, not the product.

---

### Screen 3 — Offer Card (THE screen)
**When shown:** Triggered by composite context state. Slides up over the map.

```
┌─────────────────────────────────┐
│  ⚡ Spark                    🟢 │
│         [Map: Stuttgart]        │
│ ╔═════════════════════════════╗ │
│ ║  [Generated imagery:       ]║ │  ← AI imagery_prompt rendered at runtime
│ ║  warm ceramic mug, steam   ]║ │
│ ║─────────────────────────────║ │
│ ║  Warm up on us              ║ │  ← headline (≤6 words, AI-generated)
│ ║  Flat white + croissant     ║ │  ← subtext (≤12 words)
│ ║  just 80m away              ║ │
│ ║─────────────────────────────║ │
│ ║  15% off   📍 Café Römer   ║ │  ← hard rails: % from DB, not LLM
│ ║  ⏱ 12 minutes left         ║ │  ← radial countdown timer
│ ║─────────────────────────────║ │
│ ║  [Grab it now →]   [✕]     ║ │
│ ╚═════════════════════════════╝ │
└─────────────────────────────────┘
```

**3-Second Comprehension Test:** Reading order: merchant proximity (80m) → offer (15% off) → merchant name (Café Römer) → expiry (12 min). Everything else rewards a second glance.

**What's on screen (top → bottom):**
- Merchant name + category icon
- Distance + walking time ("80m · 1 min walk")
- AI-generated hero imagery (prompt-based, matches context mood)
- Headline — e.g. "Warm up on us" (AI-generated, context-matched)
- Subtext — e.g. "Flat white + croissant · 15% off" (AI copy, hard rails for %)
- Expiry timer — countdown "⏱ 18 min left" (always server-side computed)
- Two CTAs: **"Grab it"** (primary, large) + **"Not now"** (secondary, small)
- GenUI badge (optional): small ✨ "Generated for this moment" chip

**GenUI — what actually changes per context:**
| Context | Color palette | Typography | Headline tone | Animation |
|---|---|---|---|---|
| Cold + quiet café | Amber, warm cream | Serif, heavy | Emotional ("Warm up on us") | Slow fade-in |
| Sunny + quick stop | Electric blue, white | Sans, sharp | Functional ("Ice cold. 150m.") | Snap |
| Evening + social | Deep purple, gold | Mixed | Playful ("Night's just starting") | Slide-up |
| Post-workout | Green, clean white | Sans, bold | Action ("Recover right") | Energetic |
| Transit delay | Steel blue, orange | Sans, medium | Situational ("S1's late. Pretzel?") | Alert-style |

**States:**
- Default (just arrived)
- Expanding (user taps for more detail — shows merchant photos, reviews snippet)
- Accept → transitions to Screen 4
- Decline → soft dismiss with "We'll find a better moment" + gentle fade
- Expired → card fades with "This moment just passed" (no broken state ever)

**Design notes:** This is the demo centerpiece. Every pixel matters. The card must feel different from a push notification and different from a coupon app. It's a moment, not an ad.

---

### Screen 4 — QR Redemption
**When shown:** Immediately after "Grab it" tap.

```
┌─────────────────────────────────┐
│  ⚡ Spark — Redemption          │
│                                 │
│  ✅ Offer locked in!            │
│                                 │
│  ┌─────────────────────────┐    │
│  │  ██  [QR CODE]  ██████ │    │
│  └─────────────────────────┘    │
│                                 │
│  Show this at Café Römer        │
│  📍 80m · Konrad-Adenauer-Str.  │
│                                 │
│  ⏱ Valid for 14:38 more         │
│                                 │
│  15% off any order              │
│                                 │
│  [Get directions →]             │
│                                 │
│  (This code is yours — it won't │
│   be shared or reused.)         │
└─────────────────────────────────┘
```

**QR payload format:** `spark://redeem/{offer_id}/{token_hash}/{expiry_unix}` — merchant app validates against backend. Token generated on accept and stored locally — works **offline**. Validation call happens when merchant scans, not before. No failure at the counter from lost signal.

**What's on screen:**
- Large QR code (centered, full contrast)
- Merchant name + offer summary (what they claimed)
- Expiry countdown (still ticking — urgency maintained)
- "Show this to staff" instruction
- Subtle animation: QR code has a shimmer effect indicating it's live

**States:**
- Active (QR valid, countdown running)
- Scanned / Validated → transitions to Screen 5
- Expired (countdown hits 0) → QR greyes out, "Offer expired. No charge." message

**Design notes:** Keep it dead simple. User is standing at a counter. No distractions. Large QR. Clear instruction. Done.

---

### Screen 5 — Spark Cashback Animation
**When shown:** Immediately after merchant validates QR.

```
┌─────────────────────────────────┐
│                                 │
│      ✅ Payment confirmed       │
│                                 │
│         ⚡ (animation:          │
│      lightning bolt flies       │
│      from top → wallet)         │
│                                 │
│    + €0.68 Local Reward         │
│    credited to your wallet      │
│                                 │
│    Saved at Café Römer          │
│    Today, 12:51                 │
│                                 │
│    Wallet balance: €4.88 ⚡     │
│                                 │
│  [Done]  [Share this moment →]  │
└─────────────────────────────────┘
```

**Animation spec:** Lightning bolt particle flies from merchant pin → wallet balance number, which ticks up. Use **Lottie or Rive** — not CSS. Needs to feel premium. Auto-dismiss after 2.5s → returns to Home.

**What's on screen:**
- Full-screen celebration moment
- ⚡ spark/lightning bolt animation flying from merchant pin into wallet
- "⚡ +€0.68 Local Reward" large text
- "Stayed local. Made a difference." subtext
- Wallet balance updates live: "€2.34 → €3.02"
- "Community Hero" micro-badge if user triggered a Spark Wave milestone
- Auto-dismiss after 2.5 seconds → returns to Home

**Design notes:** This is the reward moment. It should feel like something. Not a toast notification — a genuine celebration. The ⚡ animation is the Sparkasse visual language. Make it feel electric.

---

### Screen 6 — Wallet / History
**When shown:** Tap on wallet balance chip (Screen 2) or bottom nav.

```
┌─────────────────────────────────┐
│  ⚡ Spark Wallet                │
│                                 │
│  Balance: €4.88                 │
│  [Cash out to Sparkasse →]      │  ← grayed out / "Coming soon" in MVP
│                                 │
│  ──── This Week ────            │
│  ✅ Café Römer       +€0.68     │
│     Flat white + croissant      │
│     Today, 12:51                │
│                                 │
│  ✅ Bäckerei Wolf    +€0.45     │
│     End-of-day pastry rescue    │
│     Yesterday, 16:14            │
│                                 │
│  ✕  Bar Unter        declined   │
│     Craft beer offer, 20:30     │
│     Wednesday                   │
│                                 │
│  ──── Local impact ────         │
│  €1.13 kept in Stuttgart ⚡     │
└─────────────────────────────────┘
```

**Cashback model note:** The brief specifies cashback-after, not upfront discount. User pays full price → QR validated → Spark credits the discount amount. Simpler to demo (no POS integration), aligns with the banking model, matches the brief. In pitch: *"In production, that wallet is their Sparkasse Girokonto. Deposit growth for the bank, reward for the user."*

**What's on screen:**
- Total Spark balance (large)
- "Withdraw to Girokonto" CTA (or auto-credit if configured)
- Transaction history: list of past redemptions with merchant, amount, date
- "Impact" stat: "€187 stayed in Stuttgart this month"
- Preference graph teaser: "Spark thinks you like... [Cozy cafés · Transit stops · Quick lunches]" → tap → Screen 7

**States:** Default / Empty state for new users ("Your first Spark is waiting")

---

### Screen 7 — Privacy Ledger
**When shown:** Tap on green Privacy Pulse dot (Screen 2).

**What's on screen:**
- Header: "What left your device — right now"
- Live feed of the last intent vector sent:
  ```
  📍 Grid cell: Stuttgart-Mitte-047 (not your exact location)
  🚶 Movement: Browsing
  🕐 Time bucket: Tuesday lunch
  🌧️ Weather need: Warmth-seeking
  👤 Social preference: Quiet
  💰 Price tier: Mid
  ```
- "What stayed on your device" section: GPS coords, movement raw data, KG graph, transaction history
- "Your preferences" → tap → Screen 8
- "Delete all my data" CTA (red, bottom)

**Design notes:** This screen wins the German savings bank judges. It needs to feel like a real privacy dashboard, not a reassurance page. Numbers, not prose.

---

### Screen 8 — Knowledge Graph / Preference Viewer
**When shown:** From Screen 7 or Settings.

**What's on screen:**
- Visual representation: "Spark thinks you tend to..."
- Simple tag-style chips: "☕ Cozy cafés when cold (strong)" · "🍺 Bars on Friday evenings (moderate)" · "🥗 Avoids fast food (always)"
- Each chip is tappable: "Edit" → slider to adjust weight, or delete
- "How did Spark learn this?" expandable per chip: "From 14 coffee shop visits" / "From your transaction history"
- Social mode toggle: "I want to meet people tonight 🔥" → activates session SEEKS:Lively edge

**States:** Default / Social mode active (toggle glows, chip "Meeting people tonight" appears)

**Design notes:** GDPR Article 22 compliance made visible. User can contest and correct any preference. The social mode toggle is a UX delight moment — show it in the demo.

---

### Screen 9 — Context Slider (Demo Panel)
**When shown:** Developer/demo mode only. Accessible via shake gesture or Settings.

**What's on screen:**
- "Context Simulator" header (makes clear this is a debug tool)
- Sliders:
  - 🌡️ Temperature: Cold ←→ Hot
  - ⛅ Weather: Rainy ←→ Sunny
  - 🕐 Time of day: Morning / Lunch / Afternoon / Evening
  - 📊 Merchant occupancy: Empty ←→ Busy
  - 👥 Social preference: Alone ←→ Social
- "Regenerate offer" button (or auto-regenerates on slider change with 300ms debounce)
- Live offer card preview updates in real time below sliders

**Design notes:** This is THE demo moment. When the card visually transforms as the sliders move — that's GenUI. Make the transition smooth but visible. Amber ↔ blue palette shifts should be obvious. This panel doesn't ship in production.

---

## Merchant Dashboard: All Screens

### Screen M1 — Overview / Payone Pulse
**When shown:** Default landing screen for merchant.

**What's on screen:**
- Merchant name + current status badge (🟢 Normal / 🟡 Quiet / 🔴 Flash)
- **Payone Pulse chart** (line chart): current transaction rate (hourly) vs. 4-week rolling average for this hour-of-week
- When below threshold: alert banner "⚡ Quiet period — 68% below Tuesday average · Generating campaign..."
- Active offers list: "2 offers live · 1 accepted · 3 users in range"
- Quick stats: Today's redemptions, today's recovered revenue

**States:**
- Normal trading
- Quiet period detected (banner + auto-campaign status)
- Flash period (deep drop — urgent banner, max discount rules activated)
- Campaign active (spinner while Gemini Flash generates)
- Offer delivered (confirmation: "Offer sent to 3 users")

---

### Screen M2 — Rule Engine
**When shown:** Tab or menu item "Campaign Rules".

**What's on screen:**
- "Set it once. Spark handles the rest." header
- Trigger threshold slider: "Alert me when volume drops [30%] below average"
- Discount range: Min [10%] ← slider → Max [20%]
- Tone selector: [Cozy] [Energetic] [Professional] [Playful]
- Offer type: [Discount] [Free add-on] [Bundle] [Loyalty stamp]
- Blackout times: "Never offer between [22:00] and [08:00]"
- Inventory toggle: "I have surplus stock today" → boosts offer urgency
- Save button → "Rules saved · Next quiet period: Spark handles it"

**Design notes:** One form, save once. The merchant should not need to think about this again. The copy "Set it once. Spark handles the rest." is the merchant value prop in a sentence.

---

### Screen M3 — Analytics
**When shown:** "Analytics" tab.

**What's on screen:**
- This week: Quiet periods detected / Offers generated / Offers accepted / Acceptance rate
- Revenue delta: "€34.50 recovered from would-have-been-empty tables"
- Community Hero Score: "€187 stayed in Stuttgart this week that would have gone to Lieferando"
- Chart: redemptions over time (bar chart by hour-of-week)
- Best performing offer types (ranked)
- Top user segments (behavioral clusters, no PII: "Thursday lunch crowd" / "Evening regulars")

---

### Screen M4 — QR Validator
**When shown:** Merchant staff screen for in-store use (simplified, full-screen).

**What's on screen:**
- Large "Scan QR" button / camera viewfinder
- OR manual "Validate" text input (for when camera fails)
- On success: green flash + "✅ Offer valid · €4.50 · Flat white + croissant 15% off"
- On failure: red + reason ("Expired" / "Already used" / "Invalid")

**Design notes:** This is used by café staff at a counter. Needs to be operable with one hand by someone who's also making coffee. Large tap targets. Immediate visual feedback. Nothing else on screen.

---

### Screen M5 — Onboarding / Registration
**When shown:** New merchant first login.

**What's on screen:**
- Business name (auto-populated from Payone merchant ID)
- Category selector
- Opening hours
- Photo upload (used for GenUI merchant imagery context)
- Payone connection status (auto-detected if existing customer)
- "Validate on Google Maps" → Apify verification step
- Done → Rule Engine setup (M2) as next step

---

## Complete Feature Inventory

### Consumer App — MVP (must ship)

| Feature | Screen | Status |
|---|---|---|
| Offer card with GenUI | S3 | Core |
| Accept + QR flow | S4 | Core |
| Spark cashback animation | S5 | Core |
| Privacy Ledger | S7 | Core |
| Movement mode detection (IMU) | Background | Core |
| Location quantization (grid cell) | Background | Core |
| Intent vector construction | Background | Core |
| Commuting mode block | Background | Core |
| Context Slider demo panel | S9 | Core (demo) |

### Consumer App — Should Have

| Feature | Screen | Status |
|---|---|---|
| Map view with merchant pins | S2 | Should |
| Wallet / history screen | S6 | Should |
| KG preference viewer + editor | S8 | Should |
| Social mode toggle | S8 | Should |
| Knowledge Graph (SQLite) | Background | Should |
| Transaction history KG seed | Background | Should |
| Offer decline / expiry states | S3 | Should |

### Consumer App — Nice to Have

| Feature | Screen | Status |
|---|---|---|
| OCR transit ticket scan | S2 overlay | Nice |
| Spark Wave social coordination | S3 | Nice |
| Wallet pass KG seeding | Background | Nice |
| Post-workout recovery offers | Background | Nice |
| Google Calendar gap detection | Background | Nice |

### Merchant Dashboard — MVP (must ship)

| Feature | Screen | Status |
|---|---|---|
| Payone Pulse chart | M1 | Core |
| Quiet period detection alert | M1 | Core |
| Rule engine (trigger, discount, tone) | M2 | Core |
| QR validator | M4 | Core |
| Offer history feed | M1 | Core |

### Merchant Dashboard — Should Have

| Feature | Screen | Status |
|---|---|---|
| Analytics (redemptions, revenue delta) | M3 | Should |
| Community Hero Score | M3 | Should |
| Inventory/surplus toggle | M2 | Should |
| Onboarding flow | M5 | Should |

---

## Key User Flows

### Flow 1: The Core Loop (Primary Demo — 60 seconds)
```
User walking → IMU: browsing mode
     ↓
Payone detects: Café Römer 68% below Tuesday average
     ↓
Backend builds composite state: cold + quiet + browsing + tuesday_lunch
     ↓
Gemini Flash generates: offer content + GenUI params (amber, serif, cozy)
Hard rails applied: discount capped at merchant's 15% max, expiry computed
     ↓
Offer card slides up on user's phone: "Warm up on us · 80m · 18 min left"
     ↓
User taps "Grab it" → QR appears
     ↓
Staff scans QR → merchant dashboard: "1 redemption · €4.50 recovered"
     ↓
Spark animation: ⚡ +€0.68 flies into wallet
```

### Flow 2: Context Slider (GenUI Demo — 30 seconds)
```
Show offer card (cold/rainy context) → amber, cozy serif, "Warm up on us"
     ↓
Open Context Slider (shake gesture)
     ↓
Drag temperature: cold → sunny
     ↓
Card transforms in real time: amber → electric blue, serif → sans, "Cool down. 150m."
     ↓
"That's GenUI — the interface is the generated artifact."
```

### Flow 3: Privacy Ledger (Trust Demo — 20 seconds)
```
Tap green Privacy Pulse dot
     ↓
Privacy Ledger opens: shows last intent vector
"Grid cell · Movement mode · Time bucket · Weather need · Price tier"
     ↓
"No GPS coordinates. No personal data. No names. GDPR compliance isn't 
a checkbox — it's the architecture."
```

### Flow 4: Transit Delay (Stuttgart-Specific — 30 seconds)
```
User photographs DB ticket
     ↓
On-device OCR (ML Kit): parses S1, 18:02, Gleis 2
     ↓
Backend queries marudor.de: S1 running 14 minutes late
     ↓
Offer fires: "Your S1's 14 minutes late. Bäckerei Wolf is 90m away."
     ↓
"We'll alert you 4 minutes before you need to board." ← gasp moment
```

### Flow 5: Merchant Sets Rules (One-Time Setup)
```
Merchant opens dashboard → M2 Rule Engine
     ↓
Sets: trigger at 30% drop / max 20% discount / cozy tone / no offers after 22:00
     ↓
Saves → "Spark handles the rest"
     ↓
Next quiet period fires automatically, no merchant action needed
```

### Flow 6: Decline / Bad Timing
```
Offer card arrives
     ↓
User taps "Not now"
     ↓
Soft dismiss: "We'll find a better moment"
     ↓
KG edge weight updated: slight downweight for this context
     ↓
No offer for next 20 minutes (anti-spam rule)
```

---

## Screens Not to Build (Explicitly Cut)

| Screen | Why Cut |
|---|---|
| Microphone permission request | GDPR red flag, cut from architecture entirely |
| Google Health data screen | Special category data, Article 9, cut |
| ElevenLabs voice reservation | Not in core loop, 8h build for zero demo value |
| Multi-city selector | Stuttgart only for demo |
| Social graph / friend following | Out of scope; anonymous co-movement only |
| Full CRM for merchants | Dashboard, not a CRM |

---

## Language

**German first.** For Stuttgart demo, all user-facing content defaults to German. Offer headlines, onboarding text, wallet labels — all German.

LLM prompt addition: *"Generate the offer in German. Use informal 'du' form. Keep it warm and direct."*

Fallback: English if German detection fails. Merchant can set preferred offer language in dashboard.

---

## Brand & Visual Language

**App name:** Spark  
**Icon:** ⚡ (lightning bolt — Sparkasse connection)  
**Tagline:** "Make every minute local."

**Default color palette (consumer):**
- Primary: Amber / warm orange — the "cozy" default state
- Accent: Electric blue — energetic / sunny context
- Background: Off-white / warm cream
- Text: Near-black, not pure black

**GenUI overrides the palette per context** — amber is just the default. The card can be any color the AI decides is right.

**Merchant dashboard:**
- Cleaner, more professional
- Sparkasse-adjacent: navy/white with amber accents
- Data-forward: charts, numbers, status indicators dominate

**Typography:**
- Consumer headlines: Mix of serif (cozy) and sans-serif (energetic) — chosen by GenUI
- Merchant dashboard: Clean sans only (Inter or similar)
- Body text always sans for legibility

**Animation language:**
- Offer card: smooth slide-up from bottom
- GenUI transitions: morph (not cut) when context changes
- Spark cashback: lightning bolt flies from merchant pin to wallet (the brand moment)
- Decline: gentle fade with gravity — card "falls away" rather than snaps off
- Everything: 60fps, spring physics, nothing harsh

---

## The One Thing Design Must Nail

The offer card (Screen 3) is the entire product in one screen. If that card feels like a coupon notification from a loyalty app — Spark loses. If it feels like a moment generated specifically for this person in this context — Spark wins.

The Context Slider demo (Screen 9) exists solely to prove the card isn't a template. Design them as a pair. Every visual element that changes between contexts (color, font weight, imagery style, urgency indicator) must visibly change when the slider moves.

That transformation IS the demo.
