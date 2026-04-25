# 00 — Vision & Product Strategy

## The Core Insight: Time is Perishable Inventory

Every local merchant is sitting on perishable assets they cannot recover:

- A café's empty table at 14:30 is gone forever by 15:00
- A hairdresser's 14:00 appointment slot, if not filled, produces zero revenue
- A bakery's croissants at 16:30 become waste if unsold
- A nail salon's empty chair at Thursday noon is gone

Global e-commerce platforms (Amazon, Zalando) have mastered dynamic pricing and demand-side stimulation for physical goods. **No one has solved this for perishable time-slots and service capacity in local retail.** That's the gap Spark fills.

The key weapon: **Payone transaction density**. DSV Gruppe, as the parent of Payone (Germany's largest payment processor), sees transaction patterns across thousands of local merchants in real time. This is data Amazon cannot buy. It is the unfair advantage that makes Spark uniquely defensible.

---

## Product Vision

**Spark is a real-time context layer, not a coupon app.**

Offers don't exist in a database waiting to be retrieved. They are generated at the moment a user's context state — weather, movement, time, nearby merchant demand, personal preferences — creates a compelling reason to act. The offer is *created for this person, at this moment, at this merchant*, and expires when the moment passes.

This is the difference between:
- `"10% off at Café Müller, valid this month"` (ignored)
- `"Flat white + croissant, 15% off at Café Müller — 80m, quiet right now, ready in 2 min"` (acted on)

---

## Target Customers

### Consumer Side (Demand)

**Primary persona: Urban professionals in motion**
- Age 22–40, smartphone-native, time-constrained lunch breaks
- Walking between meetings, at transit stops, exploring new neighborhoods
- Value convenience and spontaneity over advance planning
- Slightly price-conscious but respond more to relevance than raw discounts
- **Key behavior:** they don't search for offers, the offer must find *them* at exactly the right moment

**Secondary persona: Tourists and visitors**
- Don't know the city, high context-hunger
- No loyalty to existing chains, open to discovery
- High conversion rate if offer is relevant and frictionless

### Merchant Side (Supply)

Any merchant with perishable time/capacity — far wider than just cafes:

| Category | Perishable Asset | Quiet Period Trigger |
|----------|-----------------|---------------------|
| Cafés & Coffee Shops | Empty seats, fresh pastries | Mid-morning dip, post-lunch lull |
| Restaurants | Table capacity | Pre-lunch (11-12), early dinner (17-18) |
| Bars & Pubs | Seating, staff already on shift | Pre-happy-hour, weekday afternoons |
| Bakeries | End-of-day inventory | 15:00–17:00 (TooGoodToGo Pro Max) |
| Hair Salons | Stylist appointment slots | Tuesday–Thursday midweek gaps |
| Nail Salons | Chair capacity | Similar midweek pattern |
| Boutiques & Shops | Staff attention / footfall | Any quiet period |
| Gyms / Studios | Class seats | Off-peak classes |
| Bookshops / Concept Stores | Staff + space | Any time |

The merchant value proposition is universal: **"We know when you're quiet before you do, and we fill that gap."**

---

## The "TooGoodToGo Pro Max" Concept

TooGoodToGo solved food waste for physical inventory (yesterday's bread). Spark solves capacity waste for temporal inventory (today's empty chair). The analogy is powerful for pitch:

- TooGoodToGo: merchant lists surplus → user discovers statically → comes later
- Spark: system *detects* surplus capacity in real time via Payone → generates offer dynamically → pushes to user already nearby → drives immediate footfall

Spark is also broader: not just food, not just "rescue" framing. It's proactive demand generation.

---

## Competitive Moat

### Why only DSV/Payone can do this at scale:

1. **Transaction density signal** — Payone processes payments for thousands of Stuttgart merchants. The volume data (not individual transactions) is the early-warning signal for quiet periods. No startup can replicate this without the payment infrastructure.

2. **Banking relationship trust** — Sparkasse has existing relationships with local merchants. Merchants already trust the Sparkasse brand for their business accounts. Spark extends that relationship digitally.

3. **GDPR-compliant by design** — On-device personalization means personal movement and preference data never reaches the server. Only an abstract intent vector (no PII) is sent to cloud. A German savings bank *leading* on privacy is a story the market rewards.

4. **Network effects flywheel:**
   - More merchants → richer offer selection for users → higher engagement
   - More user interactions → better preference model → more relevant offers → higher acceptance rate
   - Higher acceptance rate → merchants see ROI → more merchants join
   - More Payone transactions → better quiet-period detection → better trigger accuracy

---

## Business Model (Post-Hackathon Vision)

- **Merchant SaaS subscription**: tiered plan based on offer volume and analytics depth
- **Performance fee**: small percentage of redeemed offer value (only pay for results)
- **Premium placement**: merchants can boost visibility during quiet periods for a fee
- **Sparkasse integration**: Spark wallet balance tied to Girokonto — cashback lands directly in their Sparkasse account. Deposit growth for the bank.
- **Data intelligence product**: anonymized aggregate demand insights sold back to merchants for inventory planning (opt-in)

---

## The Big Picture: Why This Matters

Inner-city retail is dying. Not because people stopped wanting local experiences, but because local merchants have no tools to compete with algorithmic demand generation. Amazon knows exactly when you're about to run out of coffee. Your corner café has no idea you're walking past right now.

Spark gives the corner café the same intelligence layer. Not by copying Amazon, but by doing it locally, privately, and through the infrastructure Germany's savings banks already own.

**"Giving the corner shop an AI brain."**
