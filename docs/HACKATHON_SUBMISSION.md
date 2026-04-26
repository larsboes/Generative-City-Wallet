# HackNation 2025 – Spark Submission Drafts

Use these carefully crafted drafts to directly copy-paste into the DevPost / Hackathon submission form. They are tailored to perfectly hit the judging criteria based on the official project implementation.

## 3. Solution & Core Features
**How do you solve the problem? What are your main functionalities?**

Spark is an AI-powered city wallet that bridges the gap between local merchants and consumers in real-time. Instead of static coupon catalogues, Spark dynamically generates the most relevant local offers at the exact moment a user needs them. 

**Core Features:**
- **Context Sensing Layer:** Aggregates real-time signals including weather conditions, precise location, movement modes (e.g., walking, post-workout), and Payone transaction density to understand the user's immediate state.
- **Generative Offer Engine:** Uses Large Language Models (LLMs) to synthesize the full offer—including visual style, text, UI elements, dynamic discount rates, and timing. Offers do not exist until the moment of need.
- **Privacy-Preserving Architecture:** Sensitive movement and preference data are processed on-device. Only abstract intent vectors are securely sent to the server.
- **Seamless Checkout & Redemption:** Provides dynamic QR tokens, merchant confirmations, and animated Spark cashback, simulating a complete, closed-loop transaction.

---

## 4. Unique Selling Proposition (USP)
**What makes your project better or different from existing solutions?**

What makes Spark uniquely powerful is its "Just-in-Time Generation" model triggered by dynamic "Density Signals."
- **Zero Templates:** Spark generates the entire offer card (UI, imagery, tone, discount) from scratch using AI, tailored perfectly to the user's ongoing context.
- **Transaction Density as a Trigger:** Spark uses the simulated density of local merchant transactions (via Payone) as the core signal to trigger offers. This is an unfair advantage uniquely suited to DSV/Payone's infrastructure.
- **Privacy-First Intelligence:** Unlike competitors that rely on cloud data-mining, Spark utilizes on-device AI (Gemma 3n via Google AI Edge) for intent abstraction, ensuring maximum data privacy.
- **Deterministic Guardrails via Knowledge Graph:** Neo4j ensures that AI generations adhere to business logic, preventing budget exhaustion, applying preference decay, and ensuring offer relevance with deep explainability.

---

## 5. Implementation & Technology
**How did you technically implement the solution? What technologies do you use?**

We implemented Spark using a cutting-edge hybrid architecture prioritizing privacy, speed, and intelligence.
- **Frontend & Mobile:** Built with Expo (React Native) for cross-platform mobile access and Vite + React for the interactive real-time merchant dashboard.
- **Backend Core:** A high-performance Python FastAPI server acts as the central orchestrator.
- **Generative AI (Cloud):** Google Gemini Flash orchestrates exact offer generation and rapid structured output (GenUI) directly feeding the mobile frontend.
- **On-Device Edge AI:** Gemma 3n operating via Google AI Edge processes the abstract intent extraction entirely locally on the device (LiteRT).
- **Data & Context APIs:** Integration with OpenWeatherMap, Google Places, Luma, VVS (transit), and Mapbox for rich context building. 
- **Graph Database & Ops:** Neo4j acts as the central User Knowledge Graph, managing pseudonymous session preferences, offer lifecycles, and providing machine-readable AI explainability.

---

## 6. Results & Impact
**What have you achieved? What value does your solution bring?**

Spark redefines the relationship between Sparkasse, local merchants, and consumers via hyper-relevance.
- **Active Traffic Steering:** By matching real-time user proximity and intent with nearby merchants (using Payone density), Spark actively converts quiet streets into vibrant physical traffic dynamically.
- **Deepened User Engagement:** The fully generative, bespoke nature of the offers significantly increases potential click-through and redemption rates compared to standard static discounts. 
- **Privacy-Compliant Intelligence:** We successfully demonstrated that advanced, hyper-personalized AI experiences can be achieved without compromising user privacy, proving the commercial viability of on-device LLMs.
- **Architectural Maturity:** Delivered a production-ready monorepo complete with strict CI quality gates, comprehensive test suites, and robust deterministic graph protection (Neo4j).

---

## Video Submissions

### Demo Video (max 60 sec) Script: UI/UX & Flow
- **`0:00 - 0:10`** - **[Screen Record Mobile]** Walking down the street. The Context Sensing Layer quietly monitors the signals (show minimal abstract icons for weather, movement updating).
- **`0:10 - 0:25`** - **[Screen Record Mobile]** Boom! A dynamically generated offer appears. Briefly read out how the UI, generative text, and discount perfectly match the user's current context (e.g., matching a post-workout recovery state with a nearby smoothie spot).
- **`0:25 - 0:35`** - **[Screen Record Dashboard]** Switch to the Merchant dashboard. Show the density peak on the Mapbox heatmap that influenced and triggered the offer targeting. 
- **`0:35 - 0:50`** - **[Screen Record Mobile]** User reviews and accepts the AI offer. Demonstrate the seamless checkout—a dynamic QR token is generated and immediately scanned. 
- **`0:50 - 0:60`** - **[Screen Record Mobile]** The distinct Spark cashback animation confidently confirms the successful closed-loop transaction. Fade to Tagline: *"Right place. Right time. Right Spark."*

### Tech Video (max 60 sec) Script: Stack & Architecture
- **`0:00 - 0:15`** - **[Architecture Overview Graphic]** Briefly explain the separation of concerns between On-Device Gemma 3n (privacy-first intent extraction without PII leak) and Server-side Gemini Flash (heavy generative and styling output).
- **`0:15 - 0:30`** - **[Screen Record Editor/FastAPI]** Show the FastAPI python orchestrator code. Highlight the smooth integration of external enrichment APIs (Weather, Places, Payone simulated Density).
- **`0:30 - 0:45`** - **[Screen Record Neo4j Browser]** Show the Neo4j Graph visualizer populated with nodes. Explain how it enforces idempotent guardrails, mathematically decays user preferences, and explains exactly why every AI decision was made.
- **`0:45 - 0:60`** - **[Screen Record Terminal/CI]** Show the Docker stack elegantly spinning up all microservices or monorepo tools running. Emphasize the developer quality gates, zero-PII cloud transmission, and solid production-ready setup built during the hackathon.
