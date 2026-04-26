# 🛠️ Spark — Technical Stack

The "Generative City Wallet" is built on a **Hardened Clean Architecture** designed for privacy, deterministic reliability, and just-in-time personalization.

---

### **1. The Privacy-First Frontend**
- **React PWA**: A cross-platform mobile experience focused on low-friction engagement.
- **Edge-First AI**: **Gemma 3n** via Google AI Edge runs locally on-device.
  - *Purpose*: Extracts user intent from raw sensor data (GPS, Motion) without PII ever leaving the device.
- **Geographic Quantization**: Uses **H3 Grid Cells** (~50m resolution) to anonymize precise location before cloud transmission.

### **2. The Intelligent Backend (FastAPI)**
- **Gemini Flash**: Just-in-time generation of hyper-personalized offers and **GenUI** components.
- **Deterministic Decision Engine**: A rules-first engine that filters AI candidates based on physics (Walking Speed) and business logic (Anti-Spam).
- **Domain-Driven Design (DDD)**: Strict layer isolation between API Routers, Domain Services, and Infrastructure Repositories.

### **3. The Knowledge Graph (Neo4j)**
- **Self-Learning Brain**: Tracks category preferences and interaction history using **weighted decay**.
- **Explainability**: Every offer is backed by a machine-readable **Audit Trace**, explaining exactly why a merchant was chosen (e.g., "Post-workout recovery boost").
- **Privacy Shield**: Operates on transient `continuity_id` pseudonyms with built-in reset/opt-out controls.

### **4. Infrastructure & Pipeline**
- **Fluent Bit + Lua**: High-performance ingestion bridge for real-time **Payone transaction density**.
- **uv**: Modern Python package management for reproducible, lightning-fast builds.
- **SQLite**: Local audit logs and idempotency guards for reliable state management.
- **CI/CD**: Fully automated GitHub Actions pipeline with:
  - **Ruff/Pyright**: Zero-tolerance linting and type-safety.
  - **Architecture Guards**: AST-based boundary checks to prevent layer drift.

### **5. Context Ecosystem**
- **Google Places**: Real-time "Place Busyness" and venue metadata.
- **OpenWeatherMap**: Environmental triggers for "Warmth/Refreshment Seeking" logic.
- **Luma**: Local event pressure for nightlife and weekend relevance.
- **Mapbox**: Real-time merchant heatmapping for user discovery.

---

**"Right place. Right time. Right Spark."**
