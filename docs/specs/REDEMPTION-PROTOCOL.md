# Redemption Protocol: Secure Handshake

## Overview: Trusted Value Exchange

The redemption protocol ensures that discounts are valid, once-only, and tied to a specific commercial moment. It provides the "satisfying clink" of the cashback animation while preventing fraud.

---

## 1. QR Payload Security

The generated QR code contains a signed token to prevent manual tampering or screenshot re-use.

### Payload Schema:
`spark://redeem/{offer_id}/{expiry_unix}/{hmac_signature}`

- **Offer ID:** Unique session-linked identifier.
- **Expiry:** Unix timestamp (standard: +15 minutes from acceptance).
- **HMAC Signature:** `sha256(offer_id + expiry + merchant_secret)`

### Validation Flow:
1. **Scanning:** Merchant Dashboard (M4) scans the code.
2. **Offline Check:** If internet is slow, the dashboard re-computes the HMAC locally to verify the code was issued by Spark.
3. **Double-Spend Check:** The dashboard pings the backend to ensure the `offer_id` has not been marked as `REDEEMED`.

---

## 2. The "Spark" Cashback Animation

Redemption triggers a real-time event via WebSocket to the user's mobile app.

### Sequence:
1. Merchant pings `POST /api/redemption/confirm`.
2. Backend updates `offer_audit_log` status to `REDEEMED`.
3. Backend pings the user's session via push notification/WebSocket.
4. **Mobile App:** Executes the "Spark" animation (Lottie)—a lightning bolt flying from the merchant's map pin into the user's wallet balance.

---

## 3. Fraud Prevention Hard Rails

- **Geofencing:** A redemption is only valid if the staff's scanning device is within 100m of the merchant's registered coordinates.
- **Velocity Limit:** A single user session is capped at 2 redemptions per 4-hour window to prevent "offer farming."
- **Expiry Decay:** If a user arrives > 5 minutes after the QR expiry, the dashboard offers a "Grace Window" toggle (staff-authorized) or rejects the code automatically.
