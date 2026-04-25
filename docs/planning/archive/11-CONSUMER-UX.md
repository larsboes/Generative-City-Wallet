# 11 — Consumer UX: Screens, Consent & The Wallet

## The Screens (Consumer App Flow)

### Screen 0: First Launch — Consent & Onboarding

**This screen is non-optional for a German savings bank demo.** GDPR requires explicit, informed, granular consent. This is also your first chance to establish trust.

```
┌─────────────────────────────────┐
│  ⚡ Welcome to Spark            │
│                                 │
│  "Make every minute local."     │
│                                 │
│  To find you the right moment,  │
│  Spark needs:                   │
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

**Key principles:**
- Each permission explained with WHY (not just "we need this")
- "Processed on your device" repeated for each sensitive sensor
- Calendar is explicitly optional (increases trust by not demanding everything)
- Link to privacy approach (can be in-app explainer, not external)

---

### Screen 1: Home / Idle State

The app when no offer is active. Minimal. Not a feed of deals.

```
┌─────────────────────────────────┐
│  ⚡ Spark                    🟢 │ ← Privacy Pulse (green = on-device processing)
│                                 │
│                                 │
│         [Map or city visual]    │
│         Stuttgart Innenstadt    │
│                                 │
│                                 │
│  ┌────────────────────────────┐ │
│  │  Wallet Balance: €4.20  ⚡ │ │
│  └────────────────────────────┘ │
│                                 │
│  "Exploring Stuttgart..."       │
│  We'll find your moment.        │
│                                 │
│                                 │
│  [My History] [Settings]        │
└─────────────────────────────────┘
```

**Design notes:**
- The idle state is calm and minimal — no list of deals, no notifications begging for attention
- "We'll find your moment" = Spark is working in the background (reassuring, not alarming)
- Wallet balance visible at all times (encourages checking after cashback)
- Privacy Pulse: small green dot. Tapping it opens the Privacy Ledger.

---

### Screen 2: Offer Arrives (The Core Moment)

The GenUI card slides up from the bottom. Full-width, half-screen height. Immediately readable without scrolling.

```
┌─────────────────────────────────┐
│  ⚡ Spark                    🟢 │
│                                 │
│         [Map or city visual]    │
│                                 │
│                                 │
│ ╔═════════════════════════════╗ │
│ ║  [Generated imagery: warm  ]║ │  ← AI-generated image via imagery_prompt
│ ║  [ceramic mug, steam, bokeh]║ │
│ ║─────────────────────────────║ │
│ ║  Warm up on us              ║ │  ← headline (≤6 words)
│ ║  Flat white + croissant     ║ │  ← subtext (≤12 words)
│ ║  just 80m away              ║ │
│ ║─────────────────────────────║ │
│ ║  15% off   📍 Café Römer   ║ │
│ ║  ⏱ 12 minutes left         ║ │  ← radial timer (urgency visual)
│ ║─────────────────────────────║ │
│ ║  [Grab it now →]  [✕]      ║ │  ← CTA + dismiss
│ ╚═════════════════════════════╝ │
└─────────────────────────────────┘
```

**3-Second Comprehension Test:**
Reading order in 3 seconds: merchant proximity (80m) → offer (15% off) → merchant (Café Römer) → expiry (12 min). Everything else is context that rewards a second glance.

**What changes with GenUI:**
- Card background color (warm amber vs. electric blue vs. deep purple)
- Font weight (serif cozy vs. bold sans-serif)
- Imagery (generated at runtime based on context + merchant category)
- Timer style (gentle pulse vs. sharp countdown)
- CTA language (emotional vs. directional vs. playful)

**Dismiss (✕):**
- Soft haptic
- Card slides back down
- No guilt, no "are you sure?"
- App returns to idle state
- Cooldown begins (2h for same merchant)

---

### Screen 3: Offer Accepted — QR Token

```
┌─────────────────────────────────┐
│  ⚡ Spark — Redemption          │
│                                 │
│  ✅ Offer locked in!            │
│                                 │
│  ┌─────────────────────────┐    │
│  │  ██████████████████████ │    │
│  │  ██  [QR CODE]  ██████ │    │
│  │  ████████████████████ │    │
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

**Technical note:** QR token is generated on accept and stored locally. It works offline — the validation call happens when the merchant scans it, not before. This prevents failure at the counter if the user has no signal.

**QR content:** `spark://redeem/{offer_id}/{token_hash}/{expiry_unix}` — merchant app validates against backend.

---

### Screen 4: Redemption Confirmed — The Spark Moment

```
┌─────────────────────────────────┐
│                                 │
│                                 │
│      ✅ Payment confirmed       │
│                                 │
│                                 │
│         ⚡ (spark animation)    │
│      flies from top into        │
│      wallet balance area        │
│                                 │
│                                 │
│    + €0.68 Local Reward         │
│    credited to your wallet      │
│                                 │
│    Saved at Café Römer          │
│    Today, 12:51                 │
│                                 │
│    Wallet balance: €4.88 ⚡     │
│                                 │
│  [Done]   [Share this moment →] │
└─────────────────────────────────┘
```

**The Spark animation:** Lightning bolt or sparkle particle flies from top of screen into the wallet balance number, which ticks up with a satisfying animation. Lottie or Rive for this — not CSS, it needs to feel premium.

**"Share this moment →":** Optional. If tapped: "I just discovered Café Römer with Spark. 15% off for supporting local. ⚡" — social proof mechanic, opt-in only.

---

### Screen 5: History / Wallet

```
┌─────────────────────────────────┐
│  ⚡ Spark Wallet                │
│                                 │
│  Balance: €4.88                 │
│  [Cash out to Sparkasse →]      │  ← production feature; grayed out in MVP
│                                 │
│  ──── This Week ────            │
│                                 │
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
│  this week                      │
│                                 │
└─────────────────────────────────┘
```

---

## Cashback vs. Upfront Discount: The Decision

The challenge brief says: *"after a successful transaction the customer receives a cashback credit for the discount amount."*

**This is cashback-after, not upfront discount.** Clarifying because these are two different implementations:

| Model | Flow | Our choice? |
|-------|------|-------------|
| Upfront discount | Show QR → merchant scans → discount applied at POS → user pays less | Simpler |
| Cashback-after | User pays full price → QR validated → Spark credits the discount amount | Brief's stated preference |

**Recommendation: implement cashback model** — it matches the brief, it aligns with the Sparkasse banking model (credit to account), and it's arguably simpler to simulate (no POS integration required, just a credit to the in-app wallet).

**For the MVP simulation:**
- User pays "full price" (implied, not actually processed)
- Merchant taps "Validate" in their dashboard
- System credits `offer.discount_eur` to user's Spark wallet
- Spark animation fires

**In the pitch:** "After validation, the cashback credit appears instantly in the user's Spark wallet — and in production, that wallet is their Sparkasse Girokonto. Deposit growth for the bank, reward for the user."

---

## The Wallet: What Is It?

The wallet balance is Spark Credits, denominated in EUR. In the MVP:
- Credits accumulate from redeemed offers
- Shown in-app as a running balance
- "Cash out to Sparkasse" button: grayed out with "Coming soon" in MVP, but visually present
- Each transaction shows how much was saved and where

**Why not just ignore the wallet?** Because the brief says "city wallet" not "city app." The wallet concept is the continuity across sessions — it makes Spark feel like a financial product, not a notification app. Even a simple balance ticker with transaction history transforms the perception.

**Production vision:** Spark wallet = sub-account linked to Sparkasse Girokonto. Cashback credited directly to real bank account. This is the product that makes Sparkassen relevant to 22-year-old urban professionals who currently don't have a Sparkasse relationship.

---

## Language: German First

For Stuttgart demo, all user-facing content should default to German. This includes:
- Offer headlines and copy (generated by LLM in German)
- Onboarding text
- Wallet transaction labels

**LLM prompt addition:** "Generate the offer in German. Use informal 'du' form. Keep it warm and direct."

**Fallback:** English if German detection fails. Merchant can set preferred offer language in dashboard.

---

## User Preferences Screen

Simple settings accessible from home:
- Social preference: "I prefer **quiet** / **lively** places" (toggle)
- Price tier: "I usually spend: **under €5** / **€5-15** / **€15+**" (slider)
- Notifications: "Alert me when: **always** / **only when browsing** / **only when I open the app**"
- Dietary: tags (vegetarian, vegan, gluten-free, no allergens)
- "Clear my preferences" (GDPR right to erasure, on-device — just wipes local SQLite)

**The "I want to meet people tonight" feature:** Add a temporary toggle: "I'm feeling social 🎉 / I need quiet time 🧘" — active for the current session only. Directly affects which merchants rank higher.
