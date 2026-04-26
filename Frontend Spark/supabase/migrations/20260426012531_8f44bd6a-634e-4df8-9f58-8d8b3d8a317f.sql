ALTER TABLE public.offer_claims
  ADD COLUMN IF NOT EXISTS amount_cents integer;

COMMENT ON COLUMN public.offer_claims.amount_cents IS 'Order total in cents at the moment of redemption. NULL until redeemed.';

CREATE INDEX IF NOT EXISTS idx_offer_claims_offer_redeemed
  ON public.offer_claims (offer_id) WHERE redeemed_at IS NOT NULL;