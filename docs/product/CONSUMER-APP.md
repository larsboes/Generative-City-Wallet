# Spark — Consumer App: Design Spec

> All consumer-facing screens, notification surfaces, widgets, and lock screen.
> Platform: React PWA (iOS + Android).

---

## The Core Principle

**The offer must find the user — not the other way around.** The app is mostly invisible. It runs in the background, detects context, and surfaces exactly one offer at the right moment. The user should feel like Spark read their mind, not like they opened an app.

This means most of the design work is in the *delivery surfaces* — the offer card, the notification, the lock screen widget — not inside the app itself.

---

## Delivery Surfaces (Where Offers Appear)

Spark can reach the user across four surfaces depending on where they are when the offer fires:

| Surface | When used | Priority |
|---|---|---|
| **In-app offer card** | App is open / foregrounded | Primary — full GenUI experience |
| **Rich push notification** | App in background, phone unlocked | Secondary — quick accept from notification |
| **Lock screen / Live Activity** | Phone locked or on lock screen | Tertiary — glanceable urgency signal |
| **Home screen widget** | User checks phone, doesn't open app | Passive — awareness + balance ticker |

---

## Surface 1 — In-App Offer Card

The full GenUI experience. Only shown when the app is foregrounded.

```
┌─────────────────────────────────┐
│  ⚡ Spark                    🟢 │
│         [Map: Stuttgart]        │
│ ╔═════════════════════════════╗ │
│ ║  [Generated imagery:       ]║ │  ← runtime imagery from prompt
│ ║  warm ceramic mug, steam   ]║ │
│ ║─────────────────────────────║ │
│ ║  Warm up on us              ║ │  ← headline ≤6 words
│ ║  Flat white + croissant     ║ │  ← subtext ≤12 words
│ ║  just 80m away              ║ │
│ ║─────────────────────────────║ │
│ ║  15% off   📍 Café Römer   ║ │
│ ║  ⏱ 12 Minuten noch         ║ │
│ ║─────────────────────────────║ │
│ ║  [Jetzt sichern →]  [✕]   ║ │
│ ╚═════════════════════════════╝ │
└─────────────────────────────────┘
```

**GenUI — what changes per context:**
| Context | Colors | Type | Tone | Animation |
|---|---|---|---|---|
| Cold + quiet café | Amber, warm cream | Serif heavy | "Warm up on us" | Slow fade in |
| Sunny + quick | Electric blue, white | Sans sharp | "Cool down. 150m." | Snap |
| Evening + social | Deep purple, gold | Mixed | "Night's just starting" | Slide up |
| Post-workout | Green, clean white | Sans bold | "Recover right" | Energetic |
| Transit delay | Steel blue, orange | Sans medium | "S1 kommt zu spät. Pretzel?" | Alert |

**States:** Arrived / Expanded (tap for more) / Accepted → QR / Declined → fade / Expired → fade

**Dismiss:** Soft haptic. Card falls away with gravity. "Wir finden einen besseren Moment." No guilt, no "are you sure?". 2h cooldown for same merchant.

---

## Surface 2 — Rich Push Notification

App is backgrounded. Offer fires. This is what the user sees without opening the app.

**iOS (expandable):**
```
┌─────────────────────────────────────────────┐
│  ⚡ Spark                          jetzt     │
│  Café Römer · 80m · 15% Rabatt              │
│  "Wärm dich auf" · noch 18 Min              │
│ ─────────────────────────────────────────── │
│  [Sichern]                    [Später]       │
└─────────────────────────────────────────────┘
```

- Long-press / pull-down expands to show offer card preview image
- **"Sichern"** action button: deep-links directly to QR screen (skips offer card, goes straight to redemption)
- **"Später"** dismisses with same cooldown logic as in-app decline

**Android:**
```
┌─────────────────────────────────────────────┐
│  ⚡ Spark — Café Römer                       │
│  15% Rabatt · 80m · 18 Minuten              │
│                    [Sichern ▸]  [Ignorieren] │
└─────────────────────────────────────────────┘
```

**Notification content rules:**
- Max 2 lines visible collapsed
- Merchant name always first
- Distance always shown (makes it feel relevant, not generic)
- Expiry always shown (creates urgency)
- No emoji in notification title (looks spammy)
- Actions: accept (direct to QR) + dismiss — no "maybe later" option (either you want it or you don't)

**When NOT to send a push notification:**
- User is in commuting mode (hard block — never interrupt commute)
- User is in exercising mode (hard block)
- User already has an active unredeemed QR
- Same merchant within 2h
- After blackout time (merchant's setting)
- More than 3 notifications in 24h (anti-spam hard cap)

---

## Surface 3 — Lock Screen & Live Activity

**iOS: Dynamic Island + Lock Screen Live Activity**

When user accepts an offer (has active QR), show a Live Activity:

```
Dynamic Island (compact):
  ⚡ [Café Römer logo]  12:34 left

Dynamic Island (expanded, long press):
┌────────────────────────────────┐
│  ⚡ Spark — Offer active       │
│  Café Römer · 80m              │
│  15% off · 12 Minuten noch     │
│  [QR anzeigen]                 │
└────────────────────────────────┘

Lock Screen widget (below notification):
  ⚡ Café Römer · 12:34 · [QR →]
```

**iOS Lock Screen widget (standalone, before any offer fires):**
```
┌──────────────────────┐
│  ⚡ Spark            │
│  Stuttgart-Mitte     │
│  Kein Angebot gerade │
│  Balance: €4.20      │
└──────────────────────┘
```

**Android lock screen notification:**
Standard Android heads-up notification style — same content as push notification. Active QR shows as persistent notification until redeemed or expired.

**Live Activity states:**
| State | Content |
|---|---|
| Offer arrived (app closed) | "⚡ Neues Angebot — Café Römer 80m" → tap to open |
| QR active (accepted) | Countdown timer + "QR anzeigen" deep link |
| Offer expiring soon (< 3 min) | Timer turns amber, gentle pulse animation |
| Offer expired | "Moment verpasst — nächstes kommt bald" → auto-dismiss |
| Redeemed | "⚡ +€0.68 gutgeschrieben" → auto-dismiss after 5s |

---

## Surface 4 — Home Screen Widget

User doesn't open the app but checks their phone. Two widget sizes.

**Small widget (2×2):**
```
┌──────────────────┐
│  ⚡ Spark        │
│                  │
│  €4.88           │
│  Stuttgart       │
└──────────────────┘
```
Shows wallet balance. Taps to open app.

**Medium widget (4×2) — default state:**
```
┌───────────────────────────────────┐
│  ⚡ Spark · Stuttgart-Mitte       │
│                                   │
│  Kein Angebot gerade              │
│  Spark hält Ausschau...           │
│                     Balance: €4.88 │
└───────────────────────────────────┘
```

**Medium widget — offer available:**
```
┌───────────────────────────────────┐
│  ⚡ Spark · Angebot in der Nähe   │
│                                   │
│  Café Römer · 80m · 15% Rabatt   │
│  ⏱ 16 Minuten noch               │
│                     [Sichern →]   │
└───────────────────────────────────┘
```
Amber background when offer is live. Tapping "Sichern" deep-links to QR screen.

**Widget update frequency:** Every 15 minutes (iOS WidgetKit limit) or on offer fire (push-triggered refresh via WidgetKit background update).

**Android widget:** Same concept, uses AppWidget + RemoteViews.

---

## In-App Screens

### Screen 1 — Onboarding / Privacy Consent
First launch only.

```
┌─────────────────────────────────┐
│  ⚡ Willkommen bei Spark        │
│  "Make every minute local."     │
│                                 │
│  📍 Standort                    │
│  Für nahe Händler-Suche.        │
│  Verarbeitung auf deinem Gerät. │
│  Nur ein Rasterbereich geteilt. │
│  [Standort erlauben →]          │
│                                 │
│  🏃 Bewegung & Fitness          │
│  Erkennt Browsing vs. Pendeln   │
│  (damit wir nie den falschen    │
│  Moment stören).                │
│  Nur auf deinem Gerät.          │
│  [Bewegung erlauben →]          │
│                                 │
│  📅 Kalender (Optional)         │
│  Für Angebote um deine          │
│  Termine herum. Verlässt nie    │
│  dein Gerät.                    │
│  [Erlauben ▼] [Überspringen]    │
│                                 │
│  Deine Daten bleiben auf deinem │
│  Gerät. Spark erhält nur        │
│  anonyme Kontextsignale.        │
│                                 │
│  [Datenschutzansatz lesen →]    │
│  [Loslegen →]                   │
└─────────────────────────────────┘
```

**Key principle:** Each permission explains WHY. Calendar is optional. "Processed on your device" repeated for every sensitive sensor.

---

### Screen 2 — Home / Map View
Default state, app open.

```
┌─────────────────────────────────┐
│  ⚡ Spark                    🟢 │  ← Privacy Pulse dot
│                                 │
│         [Map: Stuttgart]        │
│         Innenstadt              │
│                                 │
│  ┌────────────────────────────┐ │
│  │  Guthaben: €4.20  ⚡      │ │
│  └────────────────────────────┘ │
│                                 │
│  "Stuttgart erkunden..."        │
│  Wir finden deinen Moment.      │
│                                 │
│  [Verlauf]   [Einstellungen]    │
└─────────────────────────────────┘
```

**States:**
- Idle / Commuting mode (map greyed, 🚊 "Pendeln — Spark pausiert") / Exercising (🏃 "Läuft — pausiert")
- Offer arriving → card slides up from bottom

**Design notes:** Map is ambient, not primary. Don't over-design it. The card IS the product.

---

### Screen 3 — Offer Card
See Surface 1 above for full wireframe and GenUI table.

---

### Screen 4 — QR Redemption

```
┌─────────────────────────────────┐
│  ⚡ Spark — Einlösen            │
│                                 │
│  ✅ Angebot gesichert!          │
│                                 │
│  ┌─────────────────────────┐    │
│  │  ██  [QR CODE]  ██████ │    │
│  └─────────────────────────┘    │
│                                 │
│  Zeig das bei Café Römer        │
│  📍 80m · Königstr. 40          │
│                                 │
│  ⏱ Noch 14:38 gültig            │
│                                 │
│  15% Rabatt auf jede Bestellung │
│                                 │
│  [Route anzeigen →]             │
│                                 │
│  (Dieser Code gehört dir —      │
│   einmalig verwendbar.)         │
└─────────────────────────────────┘
```

**QR payload:** `spark://redeem/{offer_id}/{token_hash}/{expiry_unix}` — stored locally, works offline.

**States:** Active (ticking) / Scanned → Screen 5 / Expired ("Abgelaufen. Kein Abzug.")

---

### Screen 5 — Spark Cashback Animation

```
┌─────────────────────────────────┐
│                                 │
│      ✅ Zahlung bestätigt       │
│                                 │
│         ⚡ (Lottie/Rive:        │
│      Blitz fliegt oben →        │
│      Geldbeutel unten)          │
│                                 │
│    + €0.68 Lokale Belohnung     │
│    deinem Guthaben gutgeschr.   │
│                                 │
│    Café Römer gespart           │
│    Heute, 12:51                 │
│                                 │
│    Guthaben: €4.88 ⚡           │
│                                 │
│  [Fertig]  [Moment teilen →]    │
└─────────────────────────────────┘
```

**Animation:** Lightning bolt Lottie/Rive, NOT CSS. Flies from merchant pin → wallet balance, which ticks up. Auto-dismiss 2.5s.

---

### Screen 6 — Wallet / History

```
┌─────────────────────────────────┐
│  ⚡ Spark Guthaben              │
│                                 │
│  Guthaben: €4.88                │
│  [Auf Sparkasse auszahlen →]    │  ← "Demnächst verfügbar" in MVP
│                                 │
│  ──── Diese Woche ────          │
│  ✅ Café Römer       +€0.68     │
│     Flat White + Croissant      │
│     Heute, 12:51                │
│                                 │
│  ✅ Bäckerei Wolf    +€0.45     │
│     Tagesgebäck-Rettung         │
│     Gestern, 16:14              │
│                                 │
│  ✕  Bar Unter        abgelehnt  │
│     Craft Beer, 20:30           │
│     Mittwoch                    │
│                                 │
│  ──── Lokale Wirkung ────       │
│  €1.13 in Stuttgart behalten ⚡ │
└─────────────────────────────────┘
```

---

### Screen 7 — Privacy Ledger
Tap the 🟢 Privacy Pulse dot.

```
┌─────────────────────────────────┐
│  Was dein Gerät geteilt hat     │
│  — gerade eben                  │
│                                 │
│  📍 Rasterzelle: STG-047        │
│     (nicht dein exakter Ort)    │
│  🚶 Bewegung: Browsing          │
│  🕐 Zeitfenster: Di. Mittag     │
│  🌧️ Wetterbedarf: Wärme         │
│  👤 Sozialpräferenz: Ruhig      │
│  💰 Preissegment: Mittel        │
│                                 │
│  ── Was auf deinem Gerät blieb  │
│  GPS-Koordinaten  ✓ bleibt hier │
│  Rohdaten (Bewegung) ✓ hier     │
│  Präferenzgraph   ✓ hier        │
│  Transaktionsverlauf ✓ hier     │
│                                 │
│  [Meine Präferenzen →]          │
│  [Alle Daten löschen]  ← rot    │
└─────────────────────────────────┘
```

**Design notes:** Numbers, not prose. This screen wins the GDPR judges. Make it feel like a real dashboard, not a reassurance page.

---

### Screen 8 — Knowledge Graph / Preferences

```
┌─────────────────────────────────┐
│  Spark kennt dich schon ein     │
│  bisschen...                    │
│                                 │
│  ☕ Gemütliche Cafés wenn kalt  │
│     (stark) [bearbeiten] [✕]   │
│                                 │
│  🍺 Bars freitagabends          │
│     (mittel) [bearbeiten] [✕]  │
│                                 │
│  🥗 Meidet Fast Food            │
│     (immer) [bearbeiten] [✕]   │
│                                 │
│  ── Heute Abend ──              │
│  [toggle] Ich will Leute        │
│           treffen 🔥            │
│  ↑ Session-Modus, endet heute   │
│                                 │
│  Woher weiß Spark das?          │
│  "Aus 14 Café-Besuchen" [?]    │
└─────────────────────────────────┘
```

---

### Screen 9 — Context Slider (Demo only)
Shake gesture or Settings → "Demo-Modus".

```
┌─────────────────────────────────┐
│  Kontext-Simulator              │
│  (Demo-Werkzeug)                │
│                                 │
│  🌡️ Temperatur                  │
│  Kalt ●────────────────○ Heiß  │
│                                 │
│  ⛅ Wetter                      │
│  Regen ●───────────────○ Sonne │
│                                 │
│  🕐 Tageszeit                   │
│  [Morgen][Mittag]►[Nachmittag][Abend]│
│                                 │
│  📊 Auslastung Händler          │
│  Leer ●───────────────○ Voll   │
│                                 │
│  👥 Sozialpräferenz             │
│  Allein ●──────────────○ Sozial│
│                                 │
│  ── Live-Vorschau ──            │
│  [Offer card updates here]      │
└─────────────────────────────────┘
```

**Design notes:** This is THE demo moment. Card morphs visually as sliders move (300ms debounce). Amber ↔ blue shifts must be obvious and smooth. Does not ship in production.

---

## Feature Inventory

### MVP — Must Ship

| Feature | Surface | Notes |
|---|---|---|
| Offer card + GenUI | In-app | Core loop |
| Rich push notification | Notification | Background delivery |
| Accept → QR flow | In-app | Core loop |
| Spark cashback animation | In-app | Lottie/Rive required |
| Privacy Ledger | In-app S7 | GDPR demo moment |
| IMU movement mode detection | Background | Commuting block critical |
| Location quantization | Background | Grid cell, not GPS |
| Intent vector → backend | Background | Core |
| Context Slider | Demo panel | GenUI proof |

### Should Have

| Feature | Surface | Notes |
|---|---|---|
| Home screen widget (medium) | Widget | Balance + active offer |
| Live Activity / Dynamic Island | Lock screen | Active QR countdown |
| Map view | In-app S2 | Ambient context |
| Wallet / history screen | In-app S6 | Balance continuity |
| KG preference editor | In-app S8 | GDPR Art.22 + social mode |
| Knowledge Graph SQLite | Background | Conditional preferences |
| Transaction history KG seed | Background | Cold-start |
| Decline / expiry states | In-app S3 | Polish |
| German language throughout | All surfaces | Stuttgart demo |

### Nice to Have

| Feature | Surface | Notes |
|---|---|---|
| Small widget (balance ticker) | Widget | Simple, quick win |
| Lock screen widget (no active offer) | Lock screen | Passive awareness |
| OCR transit ticket scan | In-app overlay | Gasp moment in demo |
| Spark Wave social coordination | In-app S3 | Group mechanic |
| Wallet pass KG seeding | Background | Cold-start enrichment |
| Post-workout recovery offers | Background | IMU pattern detection |
| Google Calendar gap detection | Background | On-device only |

---

## Notification Strategy

**Anti-spam rules (hard limits, non-negotiable):**
- Max **3 push notifications per day**
- Min **2 hours** between any two notifications
- **Zero** notifications during commuting mode
- **Zero** notifications during exercising mode
- **Zero** notifications when user already has active unredeemed QR
- After **3 consecutive declines** in 24h: suppress all notifications for 6h

**Notification copy rules:**
- Always in German for Stuttgart demo
- Merchant name always first
- Distance always included (makes it feel relevant)
- Expiry always included (creates urgency)
- No emoji in notification title (looks spammy on lock screen)
- ≤ 50 chars in title, ≤ 100 chars in body

---

## Screens Not to Build

| Screen | Why |
|---|---|
| Microphone permission | GDPR red flag, cut from architecture |
| Google Health integration | Article 9 special category data |
| Social friend graph | Out of scope; Spark Wave is anonymous |
| Browse-all-offers feed | Contradicts single-offer principle |
| Search / filter | Not a discovery app |
| Multi-city selector | Stuttgart only for demo |
