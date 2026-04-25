# 05 — Merchant Platform

## The Merchant Perspective: Why It's Non-Optional

The challenge brief is explicit: *"Ignore the merchant's perspective. A city wallet without happy merchants has no supply side — and no future."*

This isn't just a scoring criterion. It's structurally true. Without merchants who have registered, set rules, and seen their analytics, there's nothing to offer users. The merchant platform IS the supply side.

**Key insight for pitch:** Spark isn't a consumer app with a merchant portal bolted on. Spark is a merchant demand-generation platform that happens to have a consumer interface. The merchant is the customer; the user is the product (in the best sense — they get relevant offers).

---

## Merchant Value Proposition by Category

The universal pitch: **"We detect when you're losing revenue to empty capacity and fill it — automatically."**

| Merchant Type | Their Perishable Asset | Quiet Period Pattern | Spark's Promise |
|--------------|----------------------|---------------------|-----------------|
| Café | Seats + fresh pastries | 10-11:30, 14-16 daily | "We fill your Tuesday lull" |
| Restaurant | Table capacity | 11:30-12:00, 17-18 | "Early dinner slots, filled" |
| Bar/Pub | Seating + staff on shift | Weekday afternoons | "Pre-happy-hour converted" |
| Bakery | End-of-day inventory | 15:00-17:00 | "Zero waste, max revenue" |
| Hair Salon | Appointment slots | Tu-Th midweek | "We book your Tuesday 14:00" |
| Nail Salon | Chair capacity | Similar midweek | Same |
| Boutique | Staff attention + space | Any quiet period | "Footfall on demand" |

---

## Merchant Onboarding Flow

### Step 1: Registration
- Business name + type
- Address → auto-validated against Google Maps listing (via Apify scraper or Google Places)
  - "We found: Café Römer, Marktplatz 5, Stuttgart — is this your business? ✓"
  - Prevents fake registrations
- Payment method for Spark cashback settlements
- Payone account ID (links to real transaction data in production)

### Step 2: Profile Setup
- Menu/service categories (used for offer content)
- Operating hours (blackout windows auto-computed)
- Photos (used in generated offer imagery)
- "Vibe" preference: Cozy | Energetic | Trendy | Classic | Sustainable
- Cuisine/product tags (for user preference matching)

### Step 3: Rule Engine Configuration
This is the core merchant control surface. One-time setup, runs automatically.

```
📋 Offer Rules for: Café Römer

Trigger Condition:
  [●] Transaction volume drops below: [30]% of weekly average
  [ ] Manual trigger only
  [ ] Specific quiet hours only: [____] to [____]

Discount Settings:
  Maximum discount: [20]% 
  Minimum discount: [10]%
  (Spark AI determines exact % based on urgency level)

Offer Duration:
  Offer valid for: [20] minutes after delivery
  
Content Preferences:
  Tone: [Cozy ▼] (Cozy | Energetic | Playful | Sophisticated)
  Language: [German ▼] / [English ▼] / [Both ▼]
  
Inventory Signals (optional):
  Share current stock level: [On/Off]
  Share table availability: [On/Off]

Blackout Windows:
  Never offer before: [08:00]
  Never offer after: [21:00]
  Blackout days: [None ▼]
  
Max budget per day: [€50] in total discounts
```

### Step 4: Google Maps Listing Validation (Apify Integration)
- Apify Google Maps Scraper verifies the business exists and is open
- Pulls: rating, opening hours, category, photos, popular times
- Popular times data supplements Payone density signal (or replaces it for non-Payone merchants)
- Shows merchants their public Google profile in the dashboard

---

## The Inventory / Capacity Module ("TooGoodToGo Pro Max")

This is a genuine differentiator. Beyond detecting quiet periods via Payone, merchants can actively signal their state:

### Real-Time Status Panel
```
🟢 Status: Open for business
   Available seats: [8] of [24]     [Update]
   
📦 Today's Surplus:
   + Croissants x 12 (best by 17:00)    [Add]
   + Quiche du jour x 4                 [Add]
   + Oat milk special still available   [Add]
   
⏰ Staff note: Busy barista, prefer quick orders 14-15h
```

**Why this matters:**
- Surplus inventory + quiet period = scarcity + urgency in one offer: "8 croissants left, 15:30, 20% off" → powerful combination
- Sustainability framing: "Rescue today's batch" (for zero-waste conscious users → preference match)
- Capacity toggle lets merchants say "we're actually not ready for more customers right now" even during a Payone-detected lull

### Data Mapping Layer
The backend maps inventory signals to offer generation:

```python
def enrich_offer_context(merchant_id, composite_state):
    inventory = merchant_db.get_inventory(merchant_id)
    
    if inventory.surplus_items:
        composite_state["merchant_context"] += f"""
        Merchant has surplus: {inventory.surplus_items}
        This is an opportunity for a sustainability/waste-reduction angle.
        """
    
    if inventory.available_seats < inventory.total_seats * 0.3:
        composite_state["merchant_context"] += """
        Merchant is nearly full. Do NOT trigger offer — 
        capacity not available despite quiet Payone signal.
        """
    
    return composite_state
```

This prevents sending users to a café that is Payone-quiet (staff on break) but physically full of people who aren't paying yet.

---

## Merchant Dashboard Views

### 1. Real-Time Payone Pulse

The centerpiece visualization. Mapbox heatmap with transaction density overlay.

**Demo sequence (the killer moment):**
1. Show merchant dashboard: Payone Pulse line is dropping below the average band
2. System notification fires: "⚡ Quiet period detected — 75% below Tuesday average"
3. "Generating 'Warm Tuesday' campaign..." (1-second pause)
4. "Offer sent to users in range ✓"
5. Switch to Mia's phone → offer card arrives → she taps accept
6. Back to merchant dashboard: "1 offer accepted · ETA 3 min"

This is the end-to-end loop in 30 seconds.

### 2. Offer Performance Analytics

```
Today's Summary:
├── Quiet periods detected: 3
├── Offers generated: 8
├── Offers delivered: 6  (2 users out of range)
├── Accepted: 4           (67% acceptance rate)
├── Redeemed: 3           (75% of accepted)
└── Revenue from Spark offers: €34.50
    (vs. €0 during those quiet periods without Spark)

This week:
└── Revenue impact: €187.30 from would-have-been-empty tables

Local Economy Score:
└── €187.30 stayed in Stuttgart this week that would have gone to delivery apps
```

### 3. Offer History Feed
- Chronological list of all generated offers
- Each shows: context triggers, offer content, outcome (accepted/redeemed/expired)
- Allows merchant to see why offers were generated: "Triggered by: 75% transaction drop at 14:23"

### 4. Rule Performance
- Which rule triggers most often?
- Which discount level has highest acceptance?
- Recommendation: "Increasing your max discount from 15% to 20% could increase acceptance by ~18% based on similar merchants"

---

## The Business Registration via Apify

**Why Apify Google Maps Scraper is valuable:**
- Validates that the business is real (anti-fraud)
- Auto-populates merchant profile from existing Google listing (reduces onboarding friction)
- Pulls "popular times" data → supplements Payone density for new merchants without data history
- Keeps merchant info up to date (re-scrape weekly)

**Alternative for MVP:** Google Places API Details endpoint — same data without scraper overhead, but requires Places API key. Apify adds: bulk scraping for pre-seeding Stuttgart merchants, real-time popular times.

**Pre-seeding idea:** Before the hackathon demo, pre-register 5-10 real Stuttgart cafés using Apify data, with simulated Payone data. Makes the demo immediately feel real.

---

## Merchant Communication

When an offer is generated and redeemed, merchants receive:

**Redemption notification (in-app + optional SMS):**
```
⚡ Spark Redemption — 12:53

A customer is on their way!
Offer: Flat white + croissant, 15% off
ETA: approx. 3 minutes
QR Code: [scan at counter to confirm]

Running total today: 3 redemptions · €34.50 recovered revenue
```

**No action needed from merchant in most cases** — set rules once, Spark handles the rest. This is a key pitch point: "Zero marginal effort. Set your rules on Sunday, get customers on Tuesday."
