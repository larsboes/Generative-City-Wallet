# 08 — Open Questions & Decisions

## Resolved

### ✅ "Wenn Transaction → gegangen (leaving) oder gekommen (arriving)?"
**Resolved:** Neither direction matters. We track **transaction volume per time window vs. historical baseline** for that merchant at that hour-of-week. A transaction event = "a customer was served." Low volume = underperforming. The directionality of individual cash flows is irrelevant to quiet-period detection. What matters: `current_rate / historical_avg_rate` → density score.

### ✅ "Wie sehen Transactions aus? Welche Daten?"
**Resolved:** Minimal schema needed. For simulation: `{merchant_id, timestamp, amount_eur, category, grid_cell}`. That's it. From this we compute: hourly rate → vs. 4-week rolling average for this hour-of-week → density score → quiet period classification. No individual customer data needed. No PII involved.

### ✅ Should we cut Luma?
**Resolved: NO. Keep Luma.** It provides tonight's real Stuttgart events, which enables a live demo scenario ("you're at the hackathon, here's what Spark would do"). Other teams won't have real event data. Keep it. Luma has a public API at `https://lu.ma/api/` or use their ical feed. Fallback: parse their public Stuttgart page.

### ✅ Target city?
**Resolved: Stuttgart.** The hackathon is in Stuttgart. Demo on home turf. Pre-register Stuttgart merchants. Use VVS not BVG. Use Stuttgart weather. Make judges recognize Café Römer or Markthalle. Hyper-local = more credible.

### ✅ Should we fake Payone data?
**Resolved: Yes, simulate.** Generate synthetic data that follows realistic patterns and matches Payone's conceptual schema. Say explicitly in the pitch: "simulated Payone-compatible feed; production connects to the real stream." Judges know this is a hackathon — what they want to see is that you understand what the data looks like and how to use it. Build the generator (see `MVP-SCOPE.md`).

---

## Open / Needs Decision

### ❓ Mobile platform: Expo vs. Web PWA?

**Expo (React Native):**
- Pros: real IMU data, real GPS, real push notifications, looks like a product
- Cons: more build time, need to run on physical device

**Progressive Web App (Next.js):**
- Pros: fast to build, demo in browser on any device
- Cons: limited sensor access (no IMU), less impressive technically

**Recommendation:** Expo if you have mobile dev experience. PWA if you need to move faster and can fake IMU with a UI slider. For the demo the consumer flow needs to be on a real phone — either way works if the UX is clean.

### ❓ How to handle Luma API access?

Options:
1. `lu.ma/api/v1/calendar/list-events` — check if public or needs key
2. Parse Luma's Stuttgart public page (HTML/iCal)
3. Pre-seed Stuttgart events manually (fallback, 30 min work)
4. Eventbrite API (has a proper public API with Stuttgart city filter)

**Decision needed:** Try Luma first. If blocked: Eventbrite as fallback. If both blocked: hardcode 2-3 real Stuttgart events for the demo week (they're real events, just pre-loaded).

### ❓ VVS API access?

Deutsche Bahn Open Data provides the Fahrplan API. VVS (Verkehrsverbund Stuttgart) has their own API too.

- DB API: `https://apis.deutschebahn.com/db-api-marketplace` (requires free account)
- VVS: `https://www.openvvs.de/` (Open Data VVS)
- Fallback: use DB Strecken API for Stuttgart HBF + key U-Bahn stops

**Decision:** Register for DB API today. If too slow to onboard: use mock transit delay data for demo (set delay manually in demo settings panel). The scenario is the important thing, not the live transit connection.

### ❓ Apify vs. Google Places for merchant data?

**Apify Google Maps Scraper:**
- Good for: bulk pre-seeding Stuttgart merchants, getting popular times data not in Places API
- Cost: ~$1-5 for hackathon scale (small run)
- Time: 1 hour to set up + run

**Google Places API:**
- Good for: real-time nearby merchant lookup, details
- Free tier sufficient for hackathon
- Already needed for proximity search

**Recommendation:** Use Google Places as primary (proximity, details). Use Apify one-time to pre-seed 10 Stuttgart merchants with popular times data (supplement to simulated Payone). Both serve different purposes — not either/or.

### ❓ On-device LLM: real model or simulated?

For hackathon: **simulate it.** The Privacy Pulse UI can show "Processing with Phi-3 on device..." while you run a heuristic rule on the device side. No one will check whether Phi-3 is actually running. What matters is the architectural principle (on-device intent abstraction) and the visual demonstration.

If time allows: `transformers.js` can run a tiny sentiment/classification model in-browser. Could be used to classify a text input ("I want to meet people" → social_preference) as the on-device component.

For the pitch: "Our intent abstraction layer is designed for on-device SLMs. For this demo, we're using a lightweight heuristic implementation that mirrors what Phi-3 would produce."

### ❓ Google Calendar integration: on-device only?

**Yes, strictly on-device.** The Calendar API read happens locally. The only output that reaches the backend is `meeting_gap_min: 45` (or `pre_meeting_window: true`). No meeting titles, no attendees, no calendar structure. This is clean GDPR and also much simpler to implement since you don't need backend OAuth flow.

**Implementation:** Use Expo Calendar API (local device calendar access, user grants permission once).

### ❓ What discount range makes sense across merchant types?

Research suggests:
- Cafés: 10-20% feels appropriate (higher % seems desperate)
- Restaurants: 10-15% (lower, already low-margin)
- Bars: 10-20% for drinks (happy hour precedent)
- Bakeries: 20-40% for end-of-day (TooGoodToGo uses 50%+, but Spark is earlier)
- Services (hair, nails): 10-15% off appointment only

**Default rule:** Let merchant set max. AI uses 10% for mild lull, 15% for moderate, 20% for flash (>70% drop). This means the discount level itself signals urgency — users learn this.

### ❓ Team name / branding during hackathon?

**Recommendation: "Spark"** — the Sparkasse connection, the animation opportunity, the ignition metaphor. Beats "Generative City Wallet" as a presentation name immediately.

Alternatives to discuss:
- **SparkPulse** — adds the heartbeat/Payone Pulse angle
- **SparkFlow** — emphasizes seamless city movement
- **Spark** (standalone) — clean, sharp, memorable

**Tagline locked:** "Make every minute local."

### ❓ Machine learning: what to actually claim?

What you can honestly say you have for the demo:
- Bayesian preference model (weighted scoring based on past interactions)
- On-device preference learning (accept/decline weight updates)
- Feature engineering pipeline (context signals → feature vector)
- Composite state classification (rule-based composite state machine)

What you can honestly say is in the roadmap:
- Collaborative filtering for cold-start users
- Reinforcement learning for offer optimization (maximize redemption rate)
- Demand prediction model (quiet period forecasting from Payone history)

What to say in the pitch: "Our MVP uses a Bayesian intent model seeded with behavioral heuristics. The architecture is designed for online learning — every accept and decline updates the model in real time. In production, we layer collaborative filtering and eventually RL-based offer optimization."

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| City | Stuttgart | Hackathon location, judges recognize it |
| Luma | Keep | Unique real event data for tonight |
| Payone | Simulate | Required for hackathon, production-equivalent schema |
| Microphone | Cut | GDPR, scope, not needed for core loop |
| Google Health | Cut | Scope, permissions complexity |
| ML model | Bayesian heuristics | Honest, buildable, extensible narrative |
| Branding | "Spark" | Sparkasse connection, demo animation opportunity |
| Mobile | Expo (or PWA fallback) | Decide based on team capability |

---

## Questions for Team Discussion

1. Does anyone have DB/VVS API credentials already? (saves onboarding time)
2. Do we have a physical device for the demo? Android or iOS?
3. Who handles mobile (Expo)? Who handles backend (FastAPI)? Who handles dashboard (Next.js)?
4. Which Stuttgart cafés/bars do we know personally that we can pre-seed as demo merchants?
5. Should we run the Apify scraper tonight to pre-seed merchant data?
6. Confirm exact Gemini Flash model string in Google AI Studio — Lars has the account. (Decision: Gemini Flash, done.)
