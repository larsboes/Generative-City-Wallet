# Product Overview

## Spark: "Make every minute local."

Spark is a real-time context layer that connects local merchants with urban professionals in motion. It detects "perishable moments"—empty café seats, surplus pastries, or quiet gym hours—and generates personalized, dynamic offers delivered exactly when a user is nearby and browsing.

---

## Two Products, One System

| | **Consumer App** | **Merchant Dashboard** |
|---|---|---|
| **Platform** | React PWA | Next.js Web App |
| **Primary User** | Professionals & Explorers | Local Business Owners |
| **Core Value** | Discovery & Cashback | Filling Lulls & Inventory Rescue |
| **Trigger** | Contextual Browsing State | Payone Transaction Density Drop |

---

## Key User Flows

### 1. The Core Loop
- **Detection:** User is browsing slowly; nearby café transaction volume drops 60%.
- **Generation:** AI creates a context-matched offer (e.g., "Warm up on us" for a rainy day).
- **Hard Rails:** System enforces merchant's discount caps and name accuracy.
- **Redemption:** User accepts → QR scans at counter → Instant cashback animation.

### 2. GenUI Context Shift
Users can watch the interface visually transform as their context changes (e.g., from a warm amber "cozy" theme during rain to an electric blue "energetic" theme during sunshine). This ensures the interface *feels* as relevant as the offer text.

### 3. Privacy-First Trust
Users can inspect the **Privacy Ledger** to see the exact anonymized "Intent Vector" that leaves their phone, confirming that raw GPS, personal names, and sensor data remain local.

---

## Detailed Specifications

- **[`CONSUMER-APP.md`](CONSUMER-APP.md)**: Screen definitions, movement modes, and mobile interactions.
- **[`MERCHANT-DASHBOARD.md`](MERCHANT-DASHBOARD.md)**: Rule engine, analytics, and QR validation flow.
