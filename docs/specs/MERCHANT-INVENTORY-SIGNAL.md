# Merchant Inventory Signal

## Overview: "TooGoodToGo Pro Max"

The merchant inventory signal allows business owners to bridge the gap between their fixed rules and today's reality. By toggling a surplus signal, they can influence Spark's ranking and framing in real-time.

---

## 1. Inventory Ranking Boost

When a merchant toggles the "Surplus Stock" flag in their dashboard (M2):

1. **Ranking Multiplier:** The merchant's relevance score is boosted by **20%** globally for all users in range.
2. **Category Precedence:** If multiple merchants in the same category (e.g., two bakeries) are quiet, the one with active surplus inventory is prioritized.

---

## 2. LLM Prompt Injection

The inventory signal is passed to the Generative Engine as a **Sustainability Constraint**.

### Prompt Addition:
`"Merchant Signal: Active surplus stock (Pastries). Framing Instruction: Use sustainability/rescue language. Emphasize immediate availability."`

### Generated Output Examples:
- **Headline:** "Be a hero. Rescue a pretzel."
- **Subtext:** "Fresh batch surplus. 15% off for next 12 min."
- **Imagery Prompt:** "Close up of artisanal pastries on a wooden tray, natural morning light."

---

## 3. Capacity Toggle (Bars/Restaurants)

For hospitality venues, the "Inventory" signal behaves as a **Seating Capacity** toggle.
- **Signal:** "Available capacity right now" [Toggle ON].
- **Effect:** Resolves the "Conflict Engine" check for social users by confirming that the merchant *expects and can handle* immediate arrivals.
