-- ============== POINTS ==============
CREATE TABLE public.customer_points (
  user_id UUID PRIMARY KEY,
  points INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.customer_points ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own points"
  ON public.customer_points FOR SELECT USING (auth.uid() = user_id);

CREATE TRIGGER trg_customer_points_updated
  BEFORE UPDATE ON public.customer_points
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============== LEDGER ==============
CREATE TYPE public.points_source AS ENUM (
  'offer_redeemed',
  'photo_verified',
  'badge_unlocked'
);

CREATE TABLE public.points_ledger (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  amount INTEGER NOT NULL,
  source public.points_source NOT NULL,
  claim_id UUID REFERENCES public.offer_claims(id) ON DELETE SET NULL,
  photo_id UUID,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_points_ledger_user ON public.points_ledger(user_id, created_at DESC);
ALTER TABLE public.points_ledger ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own ledger"
  ON public.points_ledger FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Merchants view ledger of own offers"
  ON public.points_ledger FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.offer_claims c
      JOIN public.offers o ON o.id = c.offer_id
      WHERE c.id = points_ledger.claim_id
        AND o.owner_id = auth.uid()
    )
  );

-- ============== PHOTOS ==============
CREATE TYPE public.photo_status AS ENUM ('verified', 'rejected');

CREATE TABLE public.redemption_photos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  claim_id UUID NOT NULL REFERENCES public.offer_claims(id) ON DELETE CASCADE,
  offer_id UUID NOT NULL REFERENCES public.offers(id) ON DELETE CASCADE,
  business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,
  taken_at TIMESTAMPTZ,
  status public.photo_status NOT NULL,
  reject_reason TEXT,
  points_awarded INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_redemption_photos_claim ON public.redemption_photos(claim_id);
CREATE INDEX idx_redemption_photos_user ON public.redemption_photos(user_id, created_at DESC);
ALTER TABLE public.redemption_photos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own photos"
  ON public.redemption_photos FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Merchants view photos on own offers"
  ON public.redemption_photos FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.offers o
      WHERE o.id = redemption_photos.offer_id
        AND o.owner_id = auth.uid()
    )
  );

-- ============== BADGES ==============
CREATE TABLE public.customer_badges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  badge_key TEXT NOT NULL,
  label TEXT NOT NULL,
  description TEXT,
  awarded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, badge_key)
);
CREATE INDEX idx_customer_badges_user ON public.customer_badges(user_id, awarded_at DESC);
ALTER TABLE public.customer_badges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own badges"
  ON public.customer_badges FOR SELECT USING (auth.uid() = user_id);

-- ============== STORAGE ==============
INSERT INTO storage.buckets (id, name, public)
VALUES ('redemption-photos', 'redemption-photos', false);

-- Customers can read/upload their own photos. Path convention: {user_id}/{claim_id}/{filename}
CREATE POLICY "Users read own redemption photos"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'redemption-photos'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Users upload own redemption photos"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'redemption-photos'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Users delete own redemption photos"
  ON storage.objects FOR DELETE
  USING (
    bucket_id = 'redemption-photos'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

-- Merchants can read photos linked to their own redemptions
CREATE POLICY "Merchants read photos for their offers"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'redemption-photos'
    AND EXISTS (
      SELECT 1 FROM public.redemption_photos rp
      JOIN public.offers o ON o.id = rp.offer_id
      WHERE rp.storage_path = storage.objects.name
        AND o.owner_id = auth.uid()
    )
  );