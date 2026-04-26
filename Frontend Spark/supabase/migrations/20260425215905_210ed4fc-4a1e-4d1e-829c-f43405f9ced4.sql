-- Customer preferences
CREATE TABLE public.customer_prefs (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  city TEXT NOT NULL DEFAULT 'Stuttgart',
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  notify_lunch BOOLEAN NOT NULL DEFAULT true,
  notify_evening BOOLEAN NOT NULL DEFAULT true,
  notify_weather BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.customer_prefs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own prefs" ON public.customer_prefs FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own prefs" ON public.customer_prefs FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users update own prefs" ON public.customer_prefs FOR UPDATE USING (auth.uid() = user_id);

CREATE TRIGGER trg_customer_prefs_updated BEFORE UPDATE ON public.customer_prefs
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Offer bookmarks
CREATE TABLE public.offer_bookmarks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  offer_id UUID NOT NULL REFERENCES public.offers(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, offer_id)
);
ALTER TABLE public.offer_bookmarks ENABLE ROW LEVEL SECURITY;
CREATE INDEX idx_bookmarks_user ON public.offer_bookmarks(user_id);

CREATE POLICY "Users view own bookmarks" ON public.offer_bookmarks FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own bookmarks" ON public.offer_bookmarks FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users delete own bookmarks" ON public.offer_bookmarks FOR DELETE USING (auth.uid() = user_id);

-- Offer claims
CREATE TABLE public.offer_claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  offer_id UUID NOT NULL REFERENCES public.offers(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  claimed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  redeemed_at TIMESTAMPTZ,
  UNIQUE (user_id, offer_id)
);
ALTER TABLE public.offer_claims ENABLE ROW LEVEL SECURITY;
CREATE INDEX idx_claims_user ON public.offer_claims(user_id);
CREATE INDEX idx_claims_offer ON public.offer_claims(offer_id);

CREATE POLICY "Users view own claims" ON public.offer_claims
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own claims" ON public.offer_claims
  FOR INSERT WITH CHECK (auth.uid() = user_id);
-- Merchant can view claims on their own offers
CREATE POLICY "Merchants view claims on own offers" ON public.offer_claims
  FOR SELECT USING (EXISTS (
    SELECT 1 FROM public.offers o WHERE o.id = offer_id AND o.owner_id = auth.uid()
  ));
-- Merchant can mark claims redeemed
CREATE POLICY "Merchants update claims on own offers" ON public.offer_claims
  FOR UPDATE USING (EXISTS (
    SELECT 1 FROM public.offers o WHERE o.id = offer_id AND o.owner_id = auth.uid()
  ));

-- Public read of active offers for any signed-in user
CREATE POLICY "Authenticated users view active offers" ON public.offers
  FOR SELECT TO authenticated
  USING (status = 'active');

-- Public read of businesses that have at least one active offer
CREATE POLICY "Authenticated users view venues with active offers" ON public.businesses
  FOR SELECT TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.offers o WHERE o.business_id = businesses.id AND o.status = 'active'
  ));