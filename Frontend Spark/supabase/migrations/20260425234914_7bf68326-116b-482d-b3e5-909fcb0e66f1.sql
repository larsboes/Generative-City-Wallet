
ALTER TABLE public.offers
  ADD COLUMN IF NOT EXISTS is_locked boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS unlock_threshold integer,
  ADD COLUMN IF NOT EXISTS unlock_window_minutes integer;

ALTER TABLE public.offer_claims
  ADD COLUMN IF NOT EXISTS group_id uuid;

CREATE TABLE IF NOT EXISTS public.offer_groups (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  offer_id uuid NOT NULL,
  starter_user_id uuid NOT NULL,
  share_code text NOT NULL UNIQUE,
  threshold integer NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  unlocked_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_offer_claims_group_id ON public.offer_claims(group_id);
CREATE INDEX IF NOT EXISTS idx_offer_groups_offer_id ON public.offer_groups(offer_id);

ALTER TABLE public.offer_groups ENABLE ROW LEVEL SECURITY;

-- Any authenticated user can look up a group by share_code (needed for the join landing page).
CREATE POLICY "Authenticated can view offer groups"
  ON public.offer_groups FOR SELECT
  TO authenticated
  USING (true);
