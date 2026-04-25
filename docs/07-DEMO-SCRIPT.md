# 07 — Demo Script & Presentation Strategy

## The One Thing That Must Land

The judges wrote the Mia persona. Make them feel like they are watching Mia. Use second person. Use Stuttgart. Use tonight.

> "It's 14:30 on a Tuesday. You're walking through Stuttgart's Innenstadt. You've been in meetings since 9. You have 20 minutes before your next one. You're cold. You're vaguely hungry. You have no idea that Café Römer, 80 meters from you, just hit its quietest Tuesday in three weeks."

That's your opening. Not "we built an app." Not "our system uses AI." The opening is a *situation*.

---

## 3-Minute Presentation Structure

### 0:00–0:30 — The Problem (the Mia story)
Don't explain your product yet. Tell the story.

Script:
> "Between a person walking past a quiet café and a perfectly timed offer for that exact person at that exact moment — there is a gap. That gap costs local merchants billions in lost revenue every year. And it closes every time you leave without stopping. Spark closes that gap."

### 0:30–1:30 — Live Demo (the loop)
This is the core. Everything else is support.

**Demo sequence:**
1. Open merchant dashboard for "Café Römer, Stuttgart"
2. Show the Payone Pulse — line dipping below average band
3. Point to the notification: "⚡ Quiet period detected — 75% below Tuesday average"
4. Watch: "Generating campaign..." → 1 second → "Offer sent to 2 users in range ✓"
5. Pick up the phone (Mia's phone)
6. Watch the offer card arrive: `[warm imagery, amber tones, "Warm up on us" — "Flat white + croissant, 15% off, 80m — 12 minutes left"]`
7. Say: "The card isn't a template. The imagery, the tone, the colors — all generated for this context. Cold Tuesday + quiet café = cozy offer. Let me show you what happens when I change the context."
8. Open the Context Slider panel: drag weather from "cold/rainy" to "sunny/warm"
9. Watch the card transform in real time: amber → electric blue, cozy serif → sharp sans, "Warm up on us" → "Cool down. 150m."
10. Say: "That's GenUI — the interface is the generated artifact."
11. Switch back to original context. Tap "Accept" on the offer.
12. QR code appears on phone.
13. Scan the QR (or click "validate" on merchant dashboard).
14. Spark animation plays: "⚡ +€0.68 Local Reward credited"
15. Merchant dashboard: "1 redemption · €4.50 recovered revenue"

**Full loop: 60 seconds. Say nothing complicated. Let it speak.**

### 1:30–2:00 — Privacy & GDPR (the trust moment)
This is where you win the Sparkasse judges specifically.

Script:
> "Now — we're presenting this to a German savings bank, so let's talk about privacy. Tap the green dot in the corner."

Show the Privacy Ledger:
> "Everything you just saw — the movement detection, the location processing, the preference model — happened on Mia's device. What reached our servers was this: a grid cell, a movement mode, and an abstract intent vector. No GPS coordinates. No personal data. No names. GDPR compliance isn't a checkbox for us. It's the architecture."

### 2:00–2:30 — Merchant POV (the supply side)
Most teams forget this. You don't.

Script:
> "The consumer experience is the frontend. The real product is this."

Show:
- Rule engine: "Café Römer set this up once. Max 20% discount, cozy tone, trigger when volume drops 30%. That's it. On Sunday evening. And Spark handled the rest all week."
- Analytics: "Three quiet periods this week. Eight offers generated. Five redeemed. €34.50 in revenue from tables that would have been empty."
- Community Hero Score: "€187 stayed in Stuttgart this week that would have gone to Lieferando."

### 2:30–3:00 — Vision + Payone Angle (the business case)
Close with the strategic insight.

Script:
> "Why can Spark do this? Because Payone sees transaction density across every local merchant in Stuttgart. In real production, this isn't simulated data — it's the actual pulse of local commerce. DSV Gruppe sits at the intersection of payments, banking, and merchant relationships. No startup can replicate that position. Spark is what happens when you build the Amazon recommendation engine for the corner café."

Tagline close: **"Spark. Make every minute local."**

---

## The Four UX Questions (Explicitly Answer These)

The brief says to address these in the demo. Do it verbally, explicitly.

### 1. "Where does the interaction happen?"
> "We chose the in-app card format — not a push notification. A notification can be dismissed before it's understood. An in-app card gives the offer the 3 seconds it needs. The offer appears as the user is using their phone — which, given slow browsing movement, is exactly what they're doing."

### 2. "How does the offer address the user?"
> "The tone adapts to the context. Cold weather → emotional framing ('Warm up on us'). Sunny and quick → factual ('Ice cold. 150m.'). The GenUI system generates the appropriate emotional register automatically."

### 3. "What happens in the first 3 seconds?"
> "Merchant name, distance, headline, discount, expiry timer. That's it. Nothing else. The hierarchy is: where → what → how much → how long. In that order. Always."

### 4. "How does the offer end?"
> "Three endings: accept (QR + Spark animation), decline (soft dismiss: 'We'll find a better moment'), or expiry (card fades with a gentle animation — not a crash, not a broken state). All three leave the user experience intact."

---

## The Stuttgart-Specific Demo Moments

Use these to make the demo feel local and real:

### Scenario A: The Tuesday Lunch Lull (Primary Demo)
- Time: 14:30 (or simulate 14:30)
- Context: cold, overcast Stuttgart, Café Römer at 25% of normal volume
- Offer: warm drink + pastry, 15% off, 20 min valid
- Trigger: Payone density drop + weather + browsing IMU

### Scenario B: VVS Transit Delay (Bonus — now with OCR precision)
- User photographs their DB ticket: "S1 → Schwabstraße, 18:02, Gleis 2"
- On-device OCR (ML Kit) parses: train S1, departure 18:02, platform 2
- Backend queries marudor.de: S1 running 14 minutes late
- Offer fires: "Your S1's 14 minutes late. Bäckerei Wolf is 90m away — grab a pretzel. We'll alert you 4 minutes before you need to board."
- The **"4 minutes before you need to board" notification** is the gasp moment. Not just the offer — the deadline awareness.
- Without OCR fallback: if user hasn't scanned a ticket, backend still polls VVS for delays affecting trains at Stuttgart Hbf and sends a softer offer for any user with `transit_waiting` movement mode at the station
- This scenario takes 30 seconds including the ticket scan and is uniquely Stuttgart (marudor is S-Bahn/RE specific, works perfectly here)

### Scenario C: Hackathon Night (Tonight!)
- Time: tonight, wherever the hackathon is
- Context: evening, Luma event ("Hackathon Night Stuttgart") 200m
- User: stationary for 4 hours (IMU: deeply stationary, you've been sitting)
- Offer: "Need air? Craft beer + loaded fries at [bar], 150m. 20% off till midnight."
- This scenario is about the judges themselves. You're literally at the event.
- "Luma is showing tonight's hackathon as a local event. We're in our own system's context. Meta, but it works."

---

## Killer Demo Moments — Timing Checklist

| Moment | Timing | What to say |
|--------|--------|-------------|
| Payone pulse drops → notification fires | 0:35 | Nothing. Let the animation speak. |
| Offer card arrives on phone | 0:45 | "The card isn't a template." |
| Context Slider: weather changes, card transforms | 0:55 | "That's GenUI." |
| QR code appears after accept | 1:10 | "One tap to accept, QR to redeem." |
| Spark cashback animation | 1:15 | "⚡ Staying local never felt this good." |
| Privacy Ledger opens | 1:35 | "GDPR compliance isn't a checkbox. It's the architecture." |
| Merchant analytics update | 2:05 | "€34.50 from would-have-been-empty tables." |

---

## Language to Use in Pitch

**Always say:**
- "Composite context state" (not "we check the weather")
- "Payone transaction density" (not "we see if the café is busy")
- "Generative UI" (not "AI-generated text")
- "On-device intent abstraction" (not "we process things locally")
- "Anticipatory demand matching" (if you've built the prediction angle)
- "Temporal perishability" (not "empty seats")

**Never say:**
- "We use AI to generate offers" (too vague)
- "Our app shows discounts" (sounds like a coupon app)
- "We track your location" (instead: "your location is quantized on-device")

---

## Q&A Preparation

**Q: "How is this different from existing coupon apps?"**
> "Coupon apps pull from a database of pre-existing offers. Spark generates the offer at the moment it's needed, for this specific person, at this specific merchant. The offer didn't exist five minutes ago. That's the difference."

**Q: "Is the Payone data real?"**
> "For this demo, we're using a simulated Payone-compatible feed that follows Payone's data schema and realistic transaction patterns. In production, this feeds directly from Payone's transaction stream — no new infrastructure needed."

**Q: "What about privacy?"**
> "Everything personal stays on device. What reaches our servers is an abstract intent vector — no coordinates, no identifiers, no interaction history. We built GDPR compliance into the data architecture, not as a feature flag. Happy to show you the Privacy Ledger again."

**Q: "Can you really scale this beyond Stuttgart?"**
> "Every city is a configuration file. Stuttgart runs on VVS + OpenWeatherMap Stuttgart + local Payone merchants. Adding Munich is changing three lines of YAML. The Payone feed is already national infrastructure."

**Q: "What's the business model?"**
> "Merchant SaaS subscription for the analytics and rule engine. Performance fee — a small percentage of redeemed offer value. Only Spark takes a fee when it delivers a customer. No results, no cost. And long-term: the Spark wallet balance lives in a Sparkasse Girokonto. Deposit growth for the bank itself."

---

## Branding During Demo

- App name visible: **Spark** (with ⚡ icon)
- Tagline visible at end of demo: **"Make every minute local."**
- The cashback animation: a spark/lightning bolt flying into wallet balance (Sparkasse visual language)
- Color in app: amber/warm tones for "cozy" default state (aligns with Sparkasse's warm brand)

---

## What Could Go Wrong & Mitigation

| Risk | Mitigation |
|------|-----------|
| API rate limit during demo | Cache last good response; demo works offline with cached state |
| Gemini API slow | Pre-generate 3 offer examples for fallback; can swap in instantly |
| Mobile app crash | Prepare screen recording of the full flow as backup on laptop |
| QR scan fails | "Validate" button on merchant dashboard works without phone camera |
| WiFi at venue bad | Run backend locally on laptop; all APIs pre-cached |
| Context Slider timing | Reduce re-generation calls; cache GenUI output per scenario |
