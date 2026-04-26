-- Award Spark points for a redeemed claim. Called by the merchant after marking
-- the claim redeemed. Awards = round(amount_cents / 100). Idempotent per claim.
CREATE OR REPLACE FUNCTION public.award_redemption_points(_claim_id uuid)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  _claim RECORD;
  _is_owner BOOLEAN;
  _already INTEGER;
  _points INTEGER;
BEGIN
  SELECT c.id, c.user_id, c.offer_id, c.amount_cents, c.redeemed_at, o.owner_id
    INTO _claim
  FROM public.offer_claims c
  JOIN public.offers o ON o.id = c.offer_id
  WHERE c.id = _claim_id;

  IF _claim IS NULL THEN
    RAISE EXCEPTION 'Claim not found';
  END IF;

  -- Only the merchant who owns the offer may trigger this.
  IF auth.uid() IS NULL OR auth.uid() <> _claim.owner_id THEN
    RAISE EXCEPTION 'Not authorized';
  END IF;

  IF _claim.redeemed_at IS NULL THEN
    RAISE EXCEPTION 'Claim not redeemed yet';
  END IF;

  IF _claim.amount_cents IS NULL OR _claim.amount_cents <= 0 THEN
    RETURN 0;
  END IF;

  -- Idempotency: if we already awarded points for this claim, return prior amount.
  SELECT COALESCE(SUM(amount), 0) INTO _already
  FROM public.points_ledger
  WHERE claim_id = _claim_id AND source = 'offer_redeemed';

  IF _already > 0 THEN
    RETURN _already;
  END IF;

  -- Round euros to nearest integer point. €1 = 1 point.
  _points := GREATEST(1, ROUND(_claim.amount_cents::numeric / 100.0)::integer);

  INSERT INTO public.points_ledger (user_id, amount, source, claim_id, note)
  VALUES (_claim.user_id, _points, 'offer_redeemed', _claim_id,
          'Earned from €' || (_claim.amount_cents::numeric / 100.0)::text || ' purchase');

  INSERT INTO public.customer_points (user_id, points)
  VALUES (_claim.user_id, _points)
  ON CONFLICT (user_id) DO UPDATE
    SET points = public.customer_points.points + EXCLUDED.points,
        updated_at = now();

  RETURN _points;
END;
$$;