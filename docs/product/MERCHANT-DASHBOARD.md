# Spark — Merchant Dashboard: Design Spec

> **David's file. Everything needed to start designing the business dashboard in Figma.**
> Platform: Next.js web app. Primary device: laptop / tablet. Staff QR screen: mobile.

---

## What the Dashboard Is For

The merchant never needs to think about Spark after initial setup. The dashboard has two jobs:

1. **Passive monitoring** — show the merchant their Payone Pulse and what Spark did automatically
2. **One-time rule configuration** — set the rules once, Spark runs campaigns forever

The core UX principle: **"Set it once. Spark handles the rest."**

---

## Navigation Structure

```
┌─────────────────────────────────────────────────────┐
│  ⚡ Spark for Business          Café Römer  [logout] │
├──────────────┬──────────────────────────────────────┤
│              │                                      │
│  📊 Overview │         Main content area            │
│  ⚙️  Rules   │                                      │
│  📈 Analytics│                                      │
│  ✅ Validate │                                      │
│  🏪 Profile  │                                      │
│              │                                      │
└──────────────┴──────────────────────────────────────┘
```

**5 nav items.** No more. Merchant is a café owner, not a marketing team.

- **Overview** — home, default landing, Payone Pulse + active campaign status
- **Rules** — campaign rule engine (set once)
- **Analytics** — performance, revenue delta, redemption history
- **Validate** — QR scanner for staff (simplified, full-screen on mobile)
- **Profile** — merchant info, Payone connection, notification settings

---

## Screen M1 — Overview (Landing Page)

**Default state: normal trading**

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚡ Spark for Business                      Café Römer  [logout] │
├───────────┬─────────────────────────────────────────────────────┤
│  📊 Overview◄│  ┌──────────────────────────────────────────────┐ │
│  ⚙️  Rules  │  │  🟢 Trading normally                          │ │
│  📈 Analytics│ │  Tuesday 14:22 · Volume on track               │ │
│  ✅ Validate │  └──────────────────────────────────────────────┘ │
│  🏪 Profile  │                                                   │
│             │  ╔══════════════════════════════════════════════╗  │
│             │  ║  Payone Pulse — Tuesday                      ║  │
│             │  ║                                              ║  │
│             │  ║  Transactions/hr                             ║  │
│             │  ║  12│    ╭──╮                                 ║  │
│             │  ║   9│   ╭╯  ╰──╮    ← current                ║  │
│             │  ║   6│──╯       ╰──── ··· avg                 ║  │
│             │  ║   3│                                         ║  │
│             │  ║   0└──────────────────────────────           ║  │
│             │  ║     8  9  10  11  12  13  14  15             ║  │
│             │  ╚══════════════════════════════════════════════╝  │
│             │                                                   │
│             │  Today's snapshot                                 │
│             │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│             │  │  0       │  │  0       │  │  €0      │        │
│             │  │ Campaigns│  │Redemptions│  │ Recovered│        │
│             │  └──────────┘  └──────────┘  └──────────┘        │
└─────────────┴─────────────────────────────────────────────────────┘
```

---

**Quiet period state** — this is the key moment, design it with energy

```
┌──────────────────────────────────────────────────────────────────┐
│  ╔════════════════════════════════════════════════════════════╗   │
│  ║  ⚡ Quiet period detected                                  ║   │
│  ║  68% below your Tuesday 14:00 average                     ║   │
│  ║                                                            ║   │
│  ║  Generating campaign...  ████████░░  [view rules →]       ║   │
│  ╚════════════════════════════════════════════════════════════╝   │
│                                                                   │
│  ╔══════════════════════════════════════════════════════════════╗ │
│  ║  Payone Pulse — Tuesday                                     ║ │
│  ║                                              ↓ now          ║ │
│  ║  12│    ╭──╮                                                ║ │
│  ║   9│   ╭╯  ╰──╮────────────────── ··· avg                  ║ │
│  ║   6│──╯       ╰──────╮  ← drop                             ║ │
│  ║   3│                  ╰─ current                            ║ │
│  ║   0└──────────────────────────────                          ║ │
│  ╚══════════════════════════════════════════════════════════════╝ │
```

**Campaign live state** — after offer is generated and sent

```
│  ╔════════════════════════════════════════════════════════════╗   │
│  ║  ✅ Campaign live                                          ║   │
│  ║  "Warm up on us" — 15% off · Valid 20 min                 ║   │
│  ║  Sent to 3 users in range · 1 accepted · 14:31 min left   ║   │
│  ║                                                            ║   │
│  ║  [View offer →]  [Stop campaign]                          ║   │
│  ╚════════════════════════════════════════════════════════════╝   │
```

**All states for the status banner:**

| State | Color | Icon | Copy |
|---|---|---|---|
| Normal trading | 🟢 Green | ✓ | "Trading normally · Volume on track" |
| Quiet period | 🟡 Amber | ⚡ | "Quiet period detected · 68% below avg · Generating..." |
| Campaign live | 🔵 Blue | 📡 | "Campaign live · Sent to N users · X accepted" |
| Flash period | 🔴 Red | ⚠️ | "Flash quiet — 75%+ drop · Max discount rules activated" |
| Outside hours | ⚫ Grey | 🌙 | "Closed · Next open: Tomorrow 08:00" |
| Blackout active | ⚫ Grey | 🚫 | "Blackout period · Offers paused till 08:00" |

---

## Screen M2 — Rule Engine

**The entire campaign strategy in one form. Saved once.**

```
┌──────────────────────────────────────────────────────────────────┐
│  ⚙️  Campaign Rules                          [Save rules]        │
│                                                                   │
│  ── When to trigger ────────────────────────────────────────     │
│                                                                   │
│  Alert when volume drops below:                                   │
│  Mild    ○──────●──────────────○  Aggressive                     │
│           [30%]  below average                                    │
│                                                                   │
│  ── Discount ───────────────────────────────────────────────     │
│                                                                   │
│  Minimum discount:  [10] %                                        │
│  Maximum discount:  [20] %                                        │
│  (Spark picks within this range based on urgency)                │
│                                                                   │
│  ── Offer tone ─────────────────────────────────────────────     │
│                                                                   │
│  [Cozy ✓]  [Energetic]  [Professional]  [Playful]               │
│                                                                   │
│  ── Offer type ─────────────────────────────────────────────     │
│                                                                   │
│  [Discount ✓]  [Free add-on]  [Bundle deal]  [Loyalty stamp]    │
│                                                                   │
│  ── Blackout times ─────────────────────────────────────────     │
│                                                                   │
│  Never send offers between:  [22:00]  and  [08:00]              │
│                                                                   │
│  ── Today's special ────────────────────────────────────────     │
│                                                                   │
│  [toggle] I have surplus stock / inventory today                  │
│           → Spark will emphasize availability in offer copy       │
│                                                                   │
│  ── Preview ────────────────────────────────────────────────     │
│                                                                   │
│  Based on current rules, if a quiet period fires right now:      │
│  "Warm up on us — Flat white + croissant, 15% off.               │
│   Café Römer, 80m. 20 minutes left."                             │
│                                             [Regenerate preview]  │
│                                                                   │
│                              [Save rules →  "Spark handles it"] │
└──────────────────────────────────────────────────────────────────┘
```

**Design notes:**
- The "Preview" section at the bottom shows what an offer would look like right now with these rules. Real-time feedback that the rules make sense.
- "Save rules" button copy: **"Save · Spark handles the rest"** — reinforce the value prop at the moment of commitment.
- After saving: confirmation toast "Rules saved. Next quiet period: Spark's on it." with a small ⚡ animation.
- No complexity hidden behind "Advanced Settings." Everything that matters is visible.

---

## Screen M3 — Analytics

```
┌──────────────────────────────────────────────────────────────────┐
│  📈 Analytics              [This week ▼]  [Export CSV]           │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  3           │  │  8           │  │  5 / 62.5%   │           │
│  │ Quiet periods│  │ Offers sent  │  │ Accepted     │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                   │
│  ┌──────────────────────────────────────────────┐                │
│  │  💰 €34.50 recovered revenue this week       │                │
│  │     from tables that would have been empty   │                │
│  └──────────────────────────────────────────────┘                │
│                                                                   │
│  ┌──────────────────────────────────────────────┐                │
│  │  ⚡ Community Hero Score                      │                │
│  │  €187 stayed in Stuttgart this week          │                │
│  │  that would have gone to Lieferando           │                │
│  └──────────────────────────────────────────────┘                │
│                                                                   │
│  Redemptions by hour-of-week                                      │
│  ┌──────────────────────────────────────────────┐                │
│  │  Mon  ████░░░░░░░░░░░░░░░░░░░░               │                │
│  │  Tue  ███████░░░░░░░░░░░░░░░░               │                │
│  │  Wed  █████░░░░░░░░░░░░░░░░░░               │                │
│  │  Thu  ████████░░░░░░░░░░░░░░               │                │
│  │  Fri  ███░░░░░░░░░░░░░░░░░░░░               │                │
│  └──────────────────────────────────────────────┘                │
│                                                                   │
│  Best performing offers                                           │
│  1. "Warm up on us"       3 redemptions   avg €4.20             │
│  2. "Quick lunch break"   2 redemptions   avg €7.50             │
│                                                                   │
│  Who's coming in  (behavioral segments, no personal data)         │
│  ● Thursday lunch crowd  ● Evening explorers  ● Transit stoppers │
└──────────────────────────────────────────────────────────────────┘
```

**Time filters:** This week / Last 4 weeks / All time

**Design notes:**
- "€34.50 recovered revenue" card should be visually prominent — this is the number that makes merchants stay.
- Community Hero Score is a brand differentiator; give it its own visual weight (amber background, ⚡ icon).
- Behavioral segments are curiosity-inducing but privacy-safe ("Thursday lunch crowd" not "User #4291").

---

## Screen M4 — QR Validator

**Staff-facing. Used at the counter. Mobile-first, full-screen.**

```
┌─────────────────────────────────┐
│  ⚡ Spark — Validate offer      │
│                                 │
│  ┌─────────────────────────┐    │
│  │                         │    │
│  │    [Camera viewfinder]  │    │
│  │                         │    │
│  │    Point at customer's  │    │
│  │    QR code              │    │
│  │                         │    │
│  └─────────────────────────┘    │
│                                 │
│  ────── or enter code ──────    │
│                                 │
│  [ _ _ _ _ _ _ _ _ ]            │
│         [Validate]               │
│                                 │
└─────────────────────────────────┘
```

**On success:**
```
┌─────────────────────────────────┐
│                                 │
│  ✅ Valid offer                 │
│                                 │
│  Flat white + croissant         │
│  15% off · €4.50                │
│                                 │
│  Cashback credited to user ⚡   │
│                                 │
│  [Done — scan next]             │
│                                 │
└─────────────────────────────────┘
```
→ Green full-screen flash for 1.5s, then auto-ready for next scan.

**On failure:**
```
┌─────────────────────────────────┐
│                                 │
│  ❌ Invalid                     │
│                                 │
│  Expired — offer ran out        │
│                                 │
│  [Try again]                    │
│                                 │
└─────────────────────────────────┘
```

**Failure reasons:** `Expired` / `Already used` / `Wrong merchant` / `Invalid code`

**Design notes:** This is used by café staff mid-rush. One hand, half-attention. Large tap targets (min 64px). Instant full-screen color feedback (green / red). No nav, no sidebar — pure function.

---

## Screen M5 — Merchant Onboarding

**First-time setup. Sequential steps, not one long form.**

```
Step 1 of 4: Business details
┌──────────────────────────────────────────────────────────────────┐
│  Welcome to Spark ⚡                                             │
│  Let's set up Café Römer in about 3 minutes.                     │
│                                                                   │
│  Business name:  [Café Römer              ]                       │
│  Category:       [Café / Coffee shop  ▼  ]                       │
│  Address:        [Königstr. 40, Stuttgart ]                       │
│  Opening hours:  Mon–Fri [07:00] – [20:00]                       │
│                  Sat–Sun [08:00] – [18:00]                       │
│                                                                   │
│  Upload a photo of your space:  [Choose photo]                   │
│  (Used to help generate authentic offer imagery)                  │
│                                                                   │
│                                        [Next →]                  │
└──────────────────────────────────────────────────────────────────┘

Step 2 of 4: Payone connection
┌──────────────────────────────────────────────────────────────────┐
│  🟢 Payone account detected                                       │
│  Merchant ID: PAY-DE-00482910                                    │
│  Connected automatically — no action needed.                     │
│                                                                   │
│  Spark will monitor your transaction volume to detect quiet      │
│  periods and trigger campaigns automatically.                     │
│                                                                   │
│  [Not your account? →]                      [Continue →]        │
└──────────────────────────────────────────────────────────────────┘

Step 3 of 4: Business verified
┌──────────────────────────────────────────────────────────────────┐
│  🟢 Café Römer verified on Google Maps                           │
│  Rating: 4.6 ⭐ · 312 reviews                                    │
│  Königstr. 40, 70173 Stuttgart                                   │
│                                                                   │
│  [Not this business? →]                     [Continue →]        │
└──────────────────────────────────────────────────────────────────┘

Step 4 of 4: Set your rules
→ Goes directly to M2 Rule Engine, pre-filled with sensible defaults
```

---

## Screen M6 — Notification Settings / Profile

Simple settings screen:
- Business name and photo (editable)
- Payone connection status
- **Notification preferences:** Email / SMS / In-app / All three when quiet period fires
- **Minimum campaign approval:** toggle "Always auto-fire" vs. "Notify me first, I approve manually"
- Delete account / disconnect Payone

---

## Component Library (for Figma)

| Component | States | Notes |
|---|---|---|
| **Status Banner** | Normal / Quiet / Live / Flash / Closed / Blackout | The most important component — design all 6 states |
| **Payone Pulse Chart** | Loading / Normal / Dipping / Flash drop | Line chart: current (solid) vs. avg (dashed) |
| **Stat Card** | Default / Highlighted / Empty state | Used in Overview + Analytics |
| **Rule Slider** | Default / Focused / Saved | Trigger threshold, discount range |
| **Tone Selector** | Unselected / Selected | Pill/chip buttons: Cozy / Energetic / Professional / Playful |
| **Offer Preview Card** | Loading / Generated | Shows in Rule Engine preview |
| **QR Scanner** | Idle / Scanning / Success / Error | Staff-facing, mobile |
| **Community Hero Badge** | Default / Achieved | Amber/⚡ branding |
| **Nav Item** | Default / Active | 5 items, sidebar |

---

## Brand / Visual Direction (Merchant Dashboard)

**Tone:** Professional, data-forward, confident. Not consumer-playful. The merchant is running a business.

**Color:**
- Primary background: White / Light grey (#F8F9FA)
- Sidebar: Dark navy (#1A2332)
- Accent: Sparkasse amber (#F59E0B) — used for alerts, highlights, ⚡ moments
- Success: Green (#10B981)
- Warning: Amber (#F59E0B)
- Alert/Flash: Red (#EF4444)
- Charts: Amber for current line, Grey (#94A3B8) for avg line

**Typography:**
- Font: Inter (clean, professional, good for data)
- Nav labels: 14px medium
- Headers: 24px semibold
- Stats: 32px bold (the numbers need to punch)
- Body: 14px regular

**Chart design:**
- Payone Pulse: always show the rolling average as a dashed grey line — the drop is only meaningful relative to the baseline
- Bar charts in Analytics: amber fill, grey background bars
- No pie charts (hard to read quickly)

**Spacing:** Generous. Merchant reads this on a laptop between orders. Breathing room matters.

---

## Empty States

Every screen needs an empty state — the merchant who just signed up and has no data yet.

| Screen | Empty state copy |
|---|---|
| Overview | "Spark is monitoring your Payone feed. We'll alert you the moment a quiet period starts." |
| Analytics (no redemptions) | "No campaigns run yet. Once your first quiet period triggers, your stats appear here." |
| Analytics (week with no quiet periods) | "🟢 Great week — no quiet periods this week. Your busiest Tuesday on record." |
| Validate (no scan yet) | Just the camera viewfinder, large "Point at QR" instruction |

---

## What to Build for Demo vs. Post-MVP

| Screen | Demo (must look real) | Post-MVP enhancement |
|---|---|---|
| M1 Overview | Full — Payone Pulse chart is the demo centrepiece | Real-time websocket update of chart |
| M2 Rules | Full — show saving and preview | A/B test different rule sets |
| M3 Analytics | Summary stats + basic chart | Drill-down per offer, cohort analysis |
| M4 Validate | Full — works end-to-end | Batch validation, receipt printing |
| M5 Onboarding | Steps 1–3 shown, step 4 → rules | Full KYB verification flow |
| M6 Profile | Can be placeholder | Full notification management |
