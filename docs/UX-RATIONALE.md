# UX Rationale — The 3-Second Rule

Spark is designed for **instant comprehension**. Our core UX principle is that a user should understand the value of an offer in under 3 seconds without scrolling or deliberation.

## 1. Visual Hierarchy (GenUI)

Our **Generative UI** pipeline enforces a strict information hierarchy:

1.  **The Reward (Top 20%)**: Large, bold discount or benefit (e.g., "25% OFF").
2.  **The Reason (Top 40%)**: Contextual "Why" (e.g., "Warm up from the rain").
3.  **The Action (Center)**: Single, high-contrast button to "Claim" or "Save to Wallet."
4.  **The Deadline (Bottom)**: Scarcity-driven timer (e.g., "Valid for 15 mins").

## 2. Emotional vs. Factual Framing

Spark dynamically switches its "Tone" based on the user's movement mode and weather:

| Mode | Framing Style | Example Copy |
|---|---|---|
| **Browsing (Sunny)** | Factual-Informative | "15% off at Café Müller, 300m away" |
| **Warmth-Seeking (Rain)** | Emotional-Situational | "Cold outside? Your cappuccino is waiting." |
| **Post-Workout** | Reward-Focused | "Recovery is served. 20% off green juices." |

## 3. Interaction Channels

To minimize friction and maximize attention, Spark utilizes:

-   **Lock-Screen Widgets**: For "Decision Moments" (e.g., dwelling near a shop).
-   **Contextual Push**: Only triggered when a "Perfect Moment" (High Density Drop + High Preference) occurs.
-   **In-App Cards**: For general browsing.

## 4. Intentional Exit Paths

Acceptance and rejection are equally important to preserve the user experience:

-   **Expiry**: Offers automatically "fade" to prevent cluttering the wallet.
-   **Dismissal**: A single swipe-away informs the AI that the context was wrong (Learning Loop).
-   **Redemption**: A seamless QR-scan or "Cashback" loop closes the circle with zero mental load.
