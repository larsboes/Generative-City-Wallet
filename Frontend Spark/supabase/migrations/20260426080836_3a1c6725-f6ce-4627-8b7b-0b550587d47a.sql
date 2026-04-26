CREATE TABLE IF NOT EXISTS public.demo_redemptions (
  code TEXT PRIMARY KEY,
  redeemed_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  CONSTRAINT demo_redemptions_code_check CHECK (code = 'HNTN')
);

ALTER TABLE public.demo_redemptions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'demo_redemptions'
      AND policyname = 'Authenticated users view demo redemptions'
  ) THEN
    CREATE POLICY "Authenticated users view demo redemptions"
    ON public.demo_redemptions
    FOR SELECT
    TO authenticated
    USING (code = 'HNTN');
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'demo_redemptions'
      AND policyname = 'Authenticated users create demo redemptions'
  ) THEN
    CREATE POLICY "Authenticated users create demo redemptions"
    ON public.demo_redemptions
    FOR INSERT
    TO authenticated
    WITH CHECK (code = 'HNTN');
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'demo_redemptions'
      AND policyname = 'Authenticated users update demo redemptions'
  ) THEN
    CREATE POLICY "Authenticated users update demo redemptions"
    ON public.demo_redemptions
    FOR UPDATE
    TO authenticated
    USING (code = 'HNTN')
    WITH CHECK (code = 'HNTN');
  END IF;
END $$;

CREATE TRIGGER update_demo_redemptions_updated_at
BEFORE UPDATE ON public.demo_redemptions
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

ALTER PUBLICATION supabase_realtime ADD TABLE public.demo_redemptions;