# Intent Model: On-Device Inference

## Architectural Principle

To maximize privacy and comply with GDPR, sensitive intent inference is performed entirely on the user's device. The cloud backend only receives an anonymous **Intent Vector**.

---

## 1. Mobility Classification (IMU & GPS)

The on-device model classifies raw sensor data into behavioral movement modes.

### Movement Modes

| Mode | Characteristics | Policy |
|---|---|---|
| **BROWSING** | Slow walking, irregular path, frequent stops. | Prime offer moment. |
| **COMMUTING** | Sustained directional movement, rhythmic cadence. | Suppress offers (respect attention). |
| **STATIONARY** | Stopped for >2 min near a merchant. | Offer if dwell > 45s. |
| **EXERCISING** | High cadence (>7 km/h or ~2Hz oscillation). | **Hard block.** Never interrupt. |
| **POST_WORKOUT** | Pace decelerating from exercise, within last 8 min. | Boost recovery/hydration categories. |
| **CYCLING** | Smooth oscillation, 12-25 km/h, low step freq. | **Safety block.** Unsafe for interaction. |

### Technical Detection
- **Accelerometer FFT:** Distinguishes between walking (~1Hz), running (~2Hz), and cycling (smooth patterns).
- **GPS Integration:** Agreement between sensor oscillation and ground speed increases classification confidence.

---

## 2. Intent Vector Schema

The output of the on-device inference layer. No PII, no raw coordinates.

```json
{
  "grid_cell": "STR-MITTE-047",
  "movement_mode": "browsing",
  "time_bucket": "tuesday_lunch",
  "weather_need": "warmth_seeking",
  "social_preference": "quiet",
  "price_tier": "mid",
  "recent_categories": ["coffee", "bakery"],
  "dwell_signal": false,
  "battery_low": false,
  "session_id": "anon-uuid"
}
```

---

## 3. On-Device LLM (Function Calling)

Small-footprint models (e.g., **FunctionGemma 270M** or **Qwen3-1.7B**) can be used to map multi-modal sensor inputs to structured tool calls (like building the Intent Vector) without personal data leaving the boundary.

| Model Option | Size | Best Case Usage |
|---|---|---|
| **FunctionGemma** | 270M | Intent extraction and local tool routing. |
| **Gemma 3 1B** | 1B | Lightweight general reasoning. |
| **Qwen3-1.7B** | ~2B | Strong open-license alternative. |
