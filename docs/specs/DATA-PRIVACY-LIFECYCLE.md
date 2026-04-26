# Data Privacy Lifecycle

## Overview: The "Privacy Pulse" Protocol

Spark minimizes the exposure of sensitive data by enforcing a strict **local-first** lifecycle. Raw sensor data and precise locations never cross the privacy boundary.

---

## 1. On-Device Sensor TTL (Time-To-Live)

Raw sensor streams are processed in high-frequency rolling windows and immediately purged.

| Data Type | Retention on Device | Reason |
|---|---|---|
| **IMU Streams** | 30 seconds | Used for FFT movement classification. |
| **GPS Precise** | 60 seconds | Used for grid cell quantization. |
| **Calendar Raw** | RAM Only | Filtered for gaps and immediately discarded. |
| **Wallet Passes** | Event Only | Inferences written to KG; source data unlinked. |

---

## 2. The Cloud Exit Gate

Before any data leaves the device, it passes through the "Exit Gate" where it is abstracted into the **Intent Vector**.

### Anonymization Steps:
1. **Quantization:** Lat/Lon (e.g., `48.7758, 9.1829`) → Grid Cell (e.g., `STG-047`).
2. **Labeling:** Raw speed/cadence → Semantic Mode (e.g., `BROWSING`).
3. **Session Salting:** Every 24 hours, the `session_id` is re-salted to prevent long-term multi-day tracking of a specific anonymous profile.

---

## 3. Privacy Ledger Transparency

The **Privacy Ledger** (Screen S7) provides the user with a real-time audit of this gate.

- **Green Dot (Pulse):** Indicates the device is currently analyzing local context.
- **Ledger Entries:** Shows a side-by-side comparison of "What my phone knows" vs. "What I shared with Spark."
- **Right to Erasure:** A one-tap "Nuclear Option" that deletes the local Knowledge Graph and interaction history.

---

## 4. Backend Retention

The backend only retains data required for **legal accountability** (Audit Log) and **merchant analytics**.
- **Audit Logs:** Retained for 90 days (Air Canada evidentiary standard).
- **Merchant Density:** Aggregated historical transaction counts (no individual card data).
