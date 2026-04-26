CREATE TABLE public.business_notification_prefs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id uuid NOT NULL UNIQUE,
  owner_id uuid NOT NULL,
  notify_redemptions boolean NOT NULL DEFAULT true,
  notify_new_claims boolean NOT NULL DEFAULT true,
  notify_offer_expiring boolean NOT NULL DEFAULT true,
  notify_low_performance boolean NOT NULL DEFAULT false,
  notify_weekly_digest boolean NOT NULL DEFAULT true,
  notify_suggestions boolean NOT NULL DEFAULT true,
  quiet_hours_start time without time zone DEFAULT '22:00',
  quiet_hours_end time without time zone DEFAULT '08:00',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.business_notification_prefs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Owners view own notif prefs"
  ON public.business_notification_prefs FOR SELECT
  USING (auth.uid() = owner_id);

CREATE POLICY "Owners insert own notif prefs"
  ON public.business_notification_prefs FOR INSERT
  WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "Owners update own notif prefs"
  ON public.business_notification_prefs FOR UPDATE
  USING (auth.uid() = owner_id);

CREATE TRIGGER set_business_notif_prefs_updated_at
  BEFORE UPDATE ON public.business_notification_prefs
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();