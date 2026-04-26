# Transit Wait Logic

## Overview: Turning Delays into Opportunities

Spark recognizes transit delays as prime "micro-lull" moments. When a user's commute is interrupted, the system identifies venues within walking distance that match the delay window.

---

## 1. Visit Window Calculation

The engine only recommends venues that a user can realistically visit without missing their recalculated departure.

### The Algorithm:
`Visit_Window = Delay_Minutes - (Walk_Time * 2) - Buffer`

- **Delay_Minutes:** Parsed from user's OCR ticket or DB API real-time feed.
- **Walk_Time:** Estimated minutes to the venue (80m/min).
- **Buffer:** Standard 3-minute "safety margin."

### Offer Suppression:
- If `Visit_Window < 5 min`: Suppress all offers.
- If `Visit_Window < 10 min`: Prioritize "Grab & Go" (Bakeries, Coffee).
- If `Visit_Window > 15 min`: Prioritize "Dine-In" (Cafés, Restaurants).

---

## 2. Dynamic Deadline Framing

For transit-delay offers, the CTA tone shifts from "Save now" to "Deadline-aware."

### Framing Examples:
- **Header:** "Train's 14m late. Grab a coffee?"
- **Timer:** "Ready in 4m · 90m away."
- **Return Alert:** "Head back in 7 minutes." (Triggered via push notification).

---

## 3. Station Grid Cell Seeding

Spark pre-registers specific merchants located inside or within 100m of major transit hubs (e.g., Stuttgart Hbf, Charlottenplatz). These merchants receive a **20% Context Boost** in the ranking engine when a transit delay is active in their specific grid cell.
