# Analytics Engine: Value Quantification

## Overview: Proving Local Impact

The Analytics Engine quantifies the economic value Spark generates for both the merchant and the local community. This data is surfaced in the Merchant Dashboard to justify the platform's utility and provide "Community Hero" branding.

---

## 1. Recovered Revenue Algorithm

The primary KPI for merchants is **Recovered Revenue**—money that would have been lost due to perishable inventory or empty capacity.

### The Formula:
`Recovered Revenue = Sum(Redemption Value) * Confidence Factor`

- **Redemption Value:** The actual transaction amount confirmed via the QR handshake.
- **Confidence Factor:** A weight based on the Payone density signal at the time of offer.
    - `FLASH` signal (70%+ drop) = 1.0 confidence (pure recovery).
    - `QUIET` signal (30%+ drop) = 0.6 confidence (mixed recovery/discovery).

---

## 2. Community Hero Score

This metric differentiates Spark from global ad networks and delivery platforms by highlighting the "local multiplier effect."

### The Logic:
`Hero Score = (Total Spark Spend) - Estimated Ad-Network Leakage`

- **Ad-Network Leakage:** The 15-30% fees typically paid to platforms like Lieferando, UberEats, or Google Ads.
- **Pitch Narrative:** "By using Spark, you saved €187 this week in commissions that stayed in the Stuttgart economy rather than leaking to Silicon Valley."

---

## 3. Behavioral Segmenting (Privacy-Preserving)

Rather than individual user profiles, the engine aggregates interaction data into anonymized **Contextual Cohorts**.

| Cohort Name | Trigger Pattern |
|---|---|
| **Transit Stoppers** | High correlation with VVS delay signals or station grid cells. |
| **Afternoon Explorers** | Browsing mode detected during the 14:00–16:00 window. |
| **Recovery Crowd** | High acceptance rates following `POST_WORKOUT` mobility states. |

---

## 4. Merchant ROI Dashboard

The engine provides a "Community Hero Badge" status:
- **Level 1 (Local Supporter):** 5+ quiet periods filled.
- **Level 2 (City Catalyst):** €500+ revenue recovered.
- **Level 3 (Community Hero):** Top 10% of merchants by "Ad-Leakage Saved."
