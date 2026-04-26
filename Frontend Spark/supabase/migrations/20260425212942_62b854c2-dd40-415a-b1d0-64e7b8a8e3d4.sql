-- Offer status enum
CREATE TYPE public.offer_status AS ENUM ('suggested', 'active', 'paused', 'expired', 'dismissed');

-- Offers table
CREATE TABLE public.offers (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
  owner_id UUID NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  goal TEXT,
  discount_label TEXT,
  items TEXT,
  start_time TIME,
  end_time TIME,
  days_of_week TEXT[],
  audience TEXT,
  estimated_uplift TEXT,
  reasoning TEXT,
  source TEXT NOT NULL DEFAULT 'manual',
  status public.offer_status NOT NULL DEFAULT 'suggested',
  launched_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  accepted_count INT NOT NULL DEFAULT 0,
  views_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.offers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Owners view own offers" ON public.offers FOR SELECT USING (auth.uid() = owner_id);
CREATE POLICY "Owners insert own offers" ON public.offers FOR INSERT WITH CHECK (auth.uid() = owner_id);
CREATE POLICY "Owners update own offers" ON public.offers FOR UPDATE USING (auth.uid() = owner_id);
CREATE POLICY "Owners delete own offers" ON public.offers FOR DELETE USING (auth.uid() = owner_id);

CREATE TRIGGER set_offers_updated_at BEFORE UPDATE ON public.offers
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE INDEX idx_offers_business ON public.offers(business_id);
CREATE INDEX idx_offers_status ON public.offers(status);

-- Mock Payone hourly transaction data
CREATE TABLE public.payone_hourly_stats (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
  owner_id UUID NOT NULL,
  day_of_week SMALLINT NOT NULL, -- 0=Sun..6=Sat
  hour SMALLINT NOT NULL, -- 0..23
  transactions INT NOT NULL DEFAULT 0,
  revenue NUMERIC(10,2) NOT NULL DEFAULT 0,
  avg_basket NUMERIC(10,2) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (business_id, day_of_week, hour)
);

ALTER TABLE public.payone_hourly_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Owners view own payone stats" ON public.payone_hourly_stats FOR SELECT USING (auth.uid() = owner_id);
CREATE POLICY "Owners insert own payone stats" ON public.payone_hourly_stats FOR INSERT WITH CHECK (auth.uid() = owner_id);
CREATE POLICY "Owners update own payone stats" ON public.payone_hourly_stats FOR UPDATE USING (auth.uid() = owner_id);
CREATE POLICY "Owners delete own payone stats" ON public.payone_hourly_stats FOR DELETE USING (auth.uid() = owner_id);

CREATE INDEX idx_payone_business ON public.payone_hourly_stats(business_id);

-- Function to seed mock payone data for a business with a realistic 1-2pm dip
CREATE OR REPLACE FUNCTION public.seed_payone_mock(_business_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  _owner UUID;
  d INT;
  h INT;
  base_tx INT;
  multiplier NUMERIC;
  basket NUMERIC;
BEGIN
  SELECT owner_id INTO _owner FROM public.businesses WHERE id = _business_id;
  IF _owner IS NULL THEN
    RAISE EXCEPTION 'Business not found';
  END IF;
  IF auth.uid() <> _owner THEN
    RAISE EXCEPTION 'Not authorized';
  END IF;

  DELETE FROM public.payone_hourly_stats WHERE business_id = _business_id;

  FOR d IN 0..6 LOOP
    FOR h IN 7..21 LOOP
      -- Base hourly profile: morning coffee peak (8-10), lunch peak (12,13), DIP at 14, afternoon coffee (15-16), dinner (18-20)
      multiplier := CASE
        WHEN h IN (8,9) THEN 1.6
        WHEN h = 10 THEN 1.2
        WHEN h = 11 THEN 1.0
        WHEN h IN (12,13) THEN 2.0
        WHEN h = 14 THEN 0.35  -- the dip
        WHEN h = 15 THEN 0.8
        WHEN h = 16 THEN 1.0
        WHEN h = 17 THEN 1.1
        WHEN h IN (18,19,20) THEN 1.5
        ELSE 0.6
      END;
      -- Weekday vs weekend: Sat/Sun stronger brunch, weaker lunch dip not as harsh
      IF d IN (0,6) THEN
        IF h IN (10,11,12) THEN multiplier := multiplier * 1.4; END IF;
        IF h = 14 THEN multiplier := 0.6; END IF;
      END IF;
      base_tx := GREATEST(1, ROUND(18 * multiplier + (random()*4 - 2))::INT);
      basket := ROUND((6.5 + random()*3)::NUMERIC, 2);
      INSERT INTO public.payone_hourly_stats(business_id, owner_id, day_of_week, hour, transactions, revenue, avg_basket)
      VALUES (_business_id, _owner, d, h, base_tx, ROUND((base_tx * basket)::NUMERIC, 2), basket);
    END LOOP;
  END LOOP;
END;
$$;