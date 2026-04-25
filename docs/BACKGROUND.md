# Spark — Background: Vision, Strategy & Challenge Analysis

> Merged from `00-VISION.md` and `01-CHALLENGE-ANALYSIS.md`. Read this once to understand *why* we built what we built. Not a working document — context only.

---

## Part 1: Vision & Product Strategy

### The Core Insight: Time is Perishable Inventory

Every local merchant is sitting on perishable assets they cannot recover:

- A café's empty table at 14:30 is gone forever by 15:00
- A hairdresser's 14:00 appointment slot, if not filled, produces zero revenue
- A bakery's croissants at 16:30 become waste if unsold
- A nail salon's empty chair at Thursday noon is gone

Global e-commerce platforms (Amazon, Zalando) have mastered dynamic pricing and demand-side stimulation for physical goods. **No one has solved this for perishable time-slots and service capacity in local retail.** That's the gap Spark fills.

The key weapon: **Payone transaction density**. DSV Gruppe, as the parent of Payone (Germany's largest payment processor), sees transaction patterns across thousands of local merchants in real time. This is data Amazon cannot buy. It is the unfair advantage that makes Spark uniquely defensible.

---

### Product Vision

**Spark is a real-time context layer, not a coupon app.**

Offers don't exist in a database waiting to be retrieved. They are generated at the moment a user's context state — weather, movement, time, nearby merchant demand, personal preferences — creates a compelling reason to act. The offer is *created for this person, at this moment, at this merchant*, and expires when the moment passes.

The difference:
- `"10% off at Café Müller, valid this month"` → ignored
- `"Flat white + croissant, 15% off at Café Müller — 80m, quiet right now, ready in 2 min"` → acted on

---

### Target Customers

**Consumer (Demand):** Urban professionals in motion — age 22–40, smartphone-native, time-constrained. Walking between meetings, at transit stops, exploring new neighborhoods. They don't search for offers — the offer must find *them* at exactly the right moment.

**Merchant (Supply):** Any business with perishable time or capacity:

| Category | Perishable Asset | Quiet Period Trigger |
|---|---|---|
| Cafés & Coffee Shops | Empty seats, fresh pastries | Mid-morning dip, post-lunch lull |
| Restaurants | Table capacity | Pre-lunch (11–12), early dinner (17–18) |
| Bars & Pubs | Seating, staff already on shift | Pre-happy-hour, weekday afternoons |
| Bakeries | End-of-day inventory | 15:00–17:00 (TooGoodToGo Pro Max) |
| Hair / Nail Salons | Appointment slots | Tuesday–Thursday midweek gaps |
| Boutiques & Shops | Footfall | Any quiet period |

**The merchant value prop in one sentence:** "We know when you're quiet before you do, and we fill that gap."

---

### The "TooGoodToGo Pro Max" Concept

TooGoodToGo solved food waste for physical inventory (yesterday's bread). Spark solves capacity waste for temporal inventory (today's empty chair):

- TooGoodToGo: merchant lists surplus → user discovers statically → comes later
- Spark: system *detects* surplus capacity via Payone → generates offer dynamically → pushes to user already nearby → immediate footfall

---

### Competitive Moat

1. **Transaction density signal** — Payone processes payments for thousands of Stuttgart merchants. The volume data (not individual transactions) is the early-warning signal. No startup replicates this without the payment infrastructure.
2. **Banking relationship trust** — Sparkasse has existing merchant relationships. Merchants trust Sparkasse for their business accounts. Spark extends that relationship digitally.
3. **GDPR-compliant by design** — On-device personalization means personal data never reaches the server. Only an abstract intent vector (no PII) goes to cloud. A German savings bank *leading* on privacy is a story the market rewards.
4. **Network effects flywheel:** more merchants → richer offers → higher engagement → better preference model → higher acceptance rate → merchants see ROI → more merchants → better Payone signal → better trigger accuracy.

---

### Business Model

- **Merchant SaaS subscription:** tiered plan based on offer volume and analytics depth
- **Performance fee:** small % of redeemed offer value — only pay for results
- **Sparkasse integration:** Spark wallet balance tied to Girokonto — cashback lands in Sparkasse account. Deposit growth for the bank.
- **Data intelligence product:** anonymized aggregate demand insights for merchant inventory planning (opt-in)

---

### The Big Picture

Inner-city retail is dying — not because people stopped wanting local experiences, but because local merchants have no tools to compete with algorithmic demand generation. Amazon knows exactly when you're about to run out of coffee. Your corner café has no idea you're walking past right now.

Spark gives the corner café the same intelligence layer — locally, privately, through infrastructure Germany's savings banks already own.

**"Giving the corner shop an AI brain."**

---

## Part 2: Challenge Analysis — Reading Between the Lines

### What the Brief Actually Means

Surface ask: *"Build an AI-powered city wallet MVP."*

What they're really testing: DSV Gruppe owns Payone. They're sitting on transaction density data across every local merchant in Germany. They want someone to prove this data is as valuable as Amazon's purchase history — that it can generate demand for local merchants the same way algorithmic recommendation engines do for e-commerce.

**Your submission is a proof-of-concept for Payone as a competitive intelligence layer for local retail.**

If your demo shows: *"The café has 70% fewer transactions than usual for a Tuesday lunch → system detects quiet period → generates targeted offer → user nearby receives it → redeems → merchant gets a customer they wouldn't have had"* — you have answered the question. Everything else is embellishment.

---

### The Three Non-Negotiables (Elimination Criteria)

**1. Real context signals — visible to user, minimum 2 categories**
"Visible to the user" is key. The user must *see* that the offer was triggered by, e.g., rain AND low merchant busyness. Not just behind-the-scenes. Demo explicitly: "Rainy Tuesday + Café quiet = warm drink offer."

**2. Offer generated dynamically — not from a database**
Show that flipping context parameters changes the offer in real time. The GenUI card must visibly adapt. Best demo: Context Slider where you toggle weather sun → rain and the card visually transforms.

**3. End-to-end flow with merchant dashboard**
The loop: Merchant dashboard detects quiet → offer generated → user receives → user redeems → merchant dashboard updates. Merchant view is explicitly required. It cannot be an afterthought.

---

### The Four UX Questions (Answer All Four Verbally in the Demo)

1. **Where does the interaction happen?** Push notification? In-app card? Lock screen widget? You must choose one and justify it. (Spark's answer: in-app card — a notification can be dismissed before it's understood; a card gives the offer the 3 seconds it needs.)

2. **How does the offer address the user?** Factual ("15% off, 300m away") or emotional ("Your cappuccino is waiting")? Answer should depend on context — cold/rainy = emotional, sunny/quick = factual. (Spark's answer: GenUI generates the appropriate emotional register automatically.)

3. **What happens in the first 3 seconds?** Merchant name, distance, headline, discount, expiry timer. In that order. Always.

4. **How does the offer end?** Three endings: accept (QR + Spark animation), decline (soft dismiss: "We'll find a better moment"), expiry (card fades gently — not a crash). All three leave the UX intact.

---

### What Makes a Strong vs. Weak Submission

**Strong:**
- Real context in action: system *reacts* to a concrete scenario and produces a *specific* offer
- Full loop: context detection → generation → display → accept/decline → checkout
- Honest about GDPR with visible mechanism (Privacy Ledger, not just a claim)

**Weak (traps to avoid):**
- Beautiful UI with static/hardcoded offers — judges ask "how is this generated?" and you have no answer
- Ignoring the merchant perspective — "A city wallet without happy merchants has no supply side"
- Over-engineering the AI stack and under-engineering the experience — won in interaction design, not model architecture
- Vague GDPR claims without showing the actual mechanism

---

### The Payone Angle — Maximum Points Available Here

The brief calls Payone transaction density a *"key DSV asset"* — not once but three times. The word "asset" is deliberate. Position Payone not as a payment processor but as an **intelligence platform**:

> "Our Context Sensing Layer consumes a simulated Payone transaction feed — real Payone data would be the production input. When a merchant's transaction volume drops 30% below their Tuesday rolling average, our system detects a quiet period and triggers offer generation. This is the intelligence layer that Amazon has for e-commerce. Payone, through DSV Gruppe, can provide this for every local merchant in Germany."

---

### What Will Differentiate Spark from Other Teams

Most teams will use OpenWeatherMap, Google Places, a simple LLM call for offer text, and a basic consumer UI. Spark's differentiators:

1. Payone transaction density as *primary* trigger (not weather)
2. Composite context state machine (multi-signal, not if-then)
3. GenUI that visually transforms with context (not just different text)
4. Luma integration for tonight's live events
5. Merchant rule engine (not just a dashboard — actual rule-setting UI)
6. Privacy Pulse — visible on-device processing indicator
7. Spark cashback animation — the Sparkasse emotional close

---

### Glossary — Use These Terms in the Pitch

| Say this | Not this |
|---|---|
| Composite context state | "We check the weather" |
| Payone transaction density | "We see if the café is busy" |
| Generative UI (GenUI) | "AI-generated text" |
| On-device intent abstraction | "We process things locally" |
| Intent vector | "We send some data" |
| Temporal perishability | "Empty seats" |
| Hyper-local demand signal | "Sales data" |
