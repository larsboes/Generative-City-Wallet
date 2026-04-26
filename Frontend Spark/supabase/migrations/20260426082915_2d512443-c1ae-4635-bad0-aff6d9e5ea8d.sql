-- Replace the merchant UPDATE policy on offer_claims with one that pins all
-- non-redemption fields, so merchants can only flip redeemed_at on claims for their own offers.
DROP POLICY IF EXISTS "Merchants update claims on own offers" ON public.offer_claims;

CREATE POLICY "Merchants mark own-offer claims redeemed"
ON public.offer_claims
FOR UPDATE
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.offers o
    WHERE o.id = offer_claims.offer_id AND o.owner_id = auth.uid()
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.offers o
    WHERE o.id = offer_claims.offer_id AND o.owner_id = auth.uid()
  )
);

-- Enforce immutability of sensitive columns via a trigger so merchants (or anyone
-- else going through UPDATE) cannot change user_id, offer_id, code, amount_cents,
-- group_id, or claimed_at. Only redeemed_at may transition.
CREATE OR REPLACE FUNCTION public.offer_claims_guard_update()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NEW.user_id      IS DISTINCT FROM OLD.user_id      THEN RAISE EXCEPTION 'user_id is immutable'; END IF;
  IF NEW.offer_id     IS DISTINCT FROM OLD.offer_id     THEN RAISE EXCEPTION 'offer_id is immutable'; END IF;
  IF NEW.code         IS DISTINCT FROM OLD.code         THEN RAISE EXCEPTION 'code is immutable'; END IF;
  IF NEW.amount_cents IS DISTINCT FROM OLD.amount_cents
     AND OLD.amount_cents IS NOT NULL                   THEN RAISE EXCEPTION 'amount_cents is immutable once set'; END IF;
  IF NEW.group_id     IS DISTINCT FROM OLD.group_id     THEN RAISE EXCEPTION 'group_id is immutable'; END IF;
  IF NEW.claimed_at   IS DISTINCT FROM OLD.claimed_at   THEN RAISE EXCEPTION 'claimed_at is immutable'; END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_offer_claims_guard_update ON public.offer_claims;
CREATE TRIGGER trg_offer_claims_guard_update
BEFORE UPDATE ON public.offer_claims
FOR EACH ROW EXECUTE FUNCTION public.offer_claims_guard_update();