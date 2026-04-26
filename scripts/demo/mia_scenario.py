"""
Mia's Scenario — Concrete Demo Script.
Scenario: Mia is walking through Munich (Marienplatz) on a Tuesday lunch break.
It is raining, and a nearby cafe is currently quiet (low Payone density).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json

from spark.db.connection import get_connection, init_database
from spark.services.location_cells import latlon_to_h3
from spark.services.offer_pipeline import generate_offer_pipeline
from spark.models.api import GenerateOfferRequest, IntentVector

# Marienplatz, Munich
MIA_LAT = 48.137154
MIA_LON = 11.576124
MIA_GRID = latlon_to_h3(MIA_LAT, MIA_LON)

async def run_scenario():
    print("🚀 Starting Mia's Scenario Demo...")
    init_database()
    
    # 1. Ensure the Merchant exists in the DB
    # (In a real demo, this would be 'Cafe Glockenspiel' or similar)
    conn = get_connection()
    try:
        conn.execute("DELETE FROM venues WHERE merchant_id = 'MIA_CAFE'")
        conn.execute("DELETE FROM merchants WHERE id = 'MIA_CAFE'")
        conn.execute("DELETE FROM current_signals WHERE merchant_id = 'MIA_CAFE'")
        
        conn.execute(
            "INSERT INTO merchants (id, name, type, lat, lon, address, grid_cell) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('MIA_CAFE', 'Cafe Marienplatz', 'cafe', MIA_LAT, MIA_LON, 'Marienplatz 1, Munich', MIA_GRID)
        )
        
        # 2. Simulate LOW DENSITY (Quiet Period)
        # density_score=0.1 means unusually quiet
        conn.execute(
            "INSERT INTO current_signals (merchant_id, timestamp, density_score, current_txn_rate) VALUES (?, ?, ?, ?)",
            ('MIA_CAFE', datetime.now().isoformat(), 0.1, 1.2)
        )
        conn.commit()
    finally:
        conn.close()

    # 3. Trigger Offer Generation
    # We pass 'weather_need=warmth_seeking' to simulate the rainy response
    request = GenerateOfferRequest(
        intent=IntentVector(
            grid_cell=MIA_GRID,
            movement_mode="browsing",
            time_bucket="tuesday_lunch",
            weather_need="warmth_seeking",
            social_preference="quiet",
            price_tier="mid",
            recent_categories=[],
            dwell_signal=True,
            battery_low=False,
            session_id="mia-demo-session"
        )
    )

    print(f"📡 Generating offer for Mia (Context: Rainy + Quiet Cafe)...")
    result = await generate_offer_pipeline(request)
    
    if result.offer:
        print("\n✨ SUCCESS: Dynamic Offer Generated!")
        print(f"Merchant: {result.offer.merchant_name}")
        print(f"Title: {result.offer.title}")
        print(f"Discount: {result.offer.discount_pct}%")
        print(f"Vibe framing: {result.offer.vibe_framing}")
        print(f"GenUI Metadata: {json.dumps(result.offer.genui_metadata, indent=2)}")
    else:
        print("\n❌ FAILED: No offer generated. Check decision trace.")
        print(json.dumps(result.decision_trace.model_dump(), indent=2))

if __name__ == "__main__":
    asyncio.run(run_scenario())
