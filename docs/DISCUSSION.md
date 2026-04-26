# Discussion — `fun` Branch Review

**Branch:** `fun` | **Test:** `test_intent_api_sweep` | **Date:** 2026-04-26

15 scenarios, 1 passed (all 200s). Notes below for Milan, David, and Finn to discuss before merging to main.

---

## 1. `discount=0.0none` auf fast allen Offers

Alle 9 generierten Offers kommen mit `discount=0.0` und `source=merchant_rules_db` raus — kein einziger Rabatt feuert.

**Mögliche Ursachen:**
- Die OSM-Merchants (`osm_node_*`) haben in der Demo-Fixture keine Coupon-Config hinterlegt
- Merchant-Rules matchen auf Legacy-IDs (`MERCHANT_001` etc.), nicht auf H3/OSM-IDs → Rule-Lookup miss

**Zu klären:** Ist das erwartetes Verhalten für den Demo-Datensatz, oder müssen die OSM-Merchants auch Coupon-Rules bekommen? Wenn Coupon-Logic für den Pitch relevant ist, wäre das ein blocker.

---

## 2. Amari dominiert (4 von 9 Offers)

`osm_node_11028440875:Amari` gewinnt in sehr unterschiedlichen Szenarien:
- `cold_quiet_cafe` → Amari ✓ (passt)
- `morning_bakery_commute` → Amari (warum kein Bäcker?)
- `poor_fit_quiet_club` → Amari (sollte das nicht gefiltert werden?)
- `matrix_post_workout` → Amari

**Wahrscheinliche Ursache:** Amari hat in der Demo-Fixture niedrige Occupancy / hohen Density-Drop → wird vom Scoring immer stark bevorzugt, unabhängig vom Intent-Fit.

**Zu klären:** Ist die Intent-to-Category-Gewichtung stark genug, um Occupancy-Signale zu überspielen? Bei `morning_bakery_commute` würde man eine Bäckerei erwarten, nicht eine Bar. Könnten die Category-Weights erhöht werden?

---

## 3. `poor_fit_quiet_club` kriegt trotzdem ein Offer

Das Szenario ist explizit als "poor fit" benannt — Erwartung wäre entweder DO_NOT_RECOMMEND oder ein sehr schwaches Offer. Stattdessen: Amari mit normalem Score.

**Zwei Interpretationen:**
- **Bug:** Das Szenario soll testen, dass bei schlechtem Fit kein Offer kommt → dann fehlt eine Assertion
- **Okay:** Das Szenario testet nur, dass der Conflict-Check korrekt läuft, und ein "schlechter Fit" ist kein Hard-Block → dann fehlt nur ein Kommentar im Test

**Zu klären (Finn):** Was war die Intention hinter diesem Szenario? Wenn es ein negativer Case sein soll, braucht der Test eine `assert offer_id is None` oder eine `DO_NOT_RECOMMEND` Assertion.

---

## 4. 5 von 15 Szenarien → `all_candidates_filtered`

Betroffene Szenarien: `social_bar_evening`, `late_club_high_energy`, `matrix_browsing`, `matrix_transit_waiting`, `matrix_cycling`.

Das ist eine DO_NOT_RECOMMEND-Rate von 33% (+ `matrix_exercising` als korrekter Hard-Block = 40% total ohne Offer).

**Mögliche Ursachen:**
- Test läuft mit `current_dt=2026-04-24T21:00` (21 Uhr) → viele Merchants haben Closing-Windows oder keine aktiven Coupons zu dieser Zeit
- OSM-Merchants haben keine Anti-Spam-History → Counter ist clean, aber irgendeine andere Rule filtert
- Conflict-Rules sind für OSM-Merchant-IDs zu aggressiv, weil keine echte Transaktionshistorie vorliegt

**Empfehlung:** Einen Debug-Run mit `current_dt` auf 13:00 Uhr Mittag legen und schauen ob die `all_candidates_filtered` Rate sinkt. Wenn ja, ist das ein Test-Setup-Problem, kein Logic-Bug.

---

## Verdict

Technisch sauber — H3 integration läuft, alle Endpoints antworten, DB-Guard funktioniert. Die Punkte oben sind keine Blocker für den Merge, aber 2 und 3 sollten zumindest mit einem Kommentar im Test dokumentiert werden, bevor `fun` in `main` geht.

| Punkt | Merge-Blocker? | Owner |
|---|---|---|
| 1. Discount=0 | Nein (wenn Demo-Fixture so gewollt) | Lars / Finn |
| 2. Amari-Dominanz | Nein, aber tunen lohnt sich | Finn |
| 3. poor_fit_intention | Klären + ggf. Assertion | Finn |
| 4. DO_NOT_RECOMMEND-Rate | Nein, Debug-Run empfohlen | Milan / David |
