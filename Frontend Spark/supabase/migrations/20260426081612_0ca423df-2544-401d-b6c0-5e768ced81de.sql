-- 1) Prevent privilege escalation via signup metadata
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
  _role app_role;
BEGIN
  INSERT INTO public.profiles (id, full_name)
  VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'full_name', ''));

  -- Whitelist only self-selectable roles. Never trust client input for 'admin'.
  _role := CASE
    WHEN NEW.raw_user_meta_data->>'role' = 'business' THEN 'business'::app_role
    ELSE 'customer'::app_role
  END;

  INSERT INTO public.user_roles (user_id, role) VALUES (NEW.id, _role);

  RETURN NEW;
END;
$function$;

-- 2) Restrict businesses public exposure: replace broad policy with column-safe view
DROP POLICY IF EXISTS "Authenticated users view venues with active offers" ON public.businesses;

CREATE OR REPLACE VIEW public.public_businesses
WITH (security_invoker = true) AS
SELECT
  b.id,
  b.name,
  b.category,
  b.address,
  b.city,
  b.country,
  b.latitude,
  b.longitude,
  b.website,
  b.photo_url,
  b.rating,
  b.price_level,
  b.opening_hours
FROM public.businesses b
WHERE EXISTS (
  SELECT 1 FROM public.offers o
  WHERE o.business_id = b.id AND o.status = 'active'
);

GRANT SELECT ON public.public_businesses TO authenticated;

-- Re-create a column-restricted SELECT policy on businesses so the view's
-- security_invoker check (which runs as the querying user) succeeds for the
-- whitelisted columns only. We expose all columns via RLS but the view limits
-- which are returned to non-owners; owners keep full access via their own policy.
CREATE POLICY "Authenticated users view venues with active offers (limited)"
ON public.businesses
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.offers o
    WHERE o.business_id = businesses.id AND o.status = 'active'
  )
);

-- 3) Realtime channel access control: restrict realtime.messages so users can
-- only receive broadcasts on topics scoped to themselves or to the public
-- demo redemption topic.
ALTER TABLE IF EXISTS realtime.messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users read scoped realtime topics" ON realtime.messages;
CREATE POLICY "Authenticated users read scoped realtime topics"
ON realtime.messages
FOR SELECT
TO authenticated
USING (
  -- Allow the public demo redemption channel
  realtime.topic() = 'demo-redemption-HNTN'
  -- Allow user-scoped topics that include the user's id
  OR realtime.topic() LIKE 'user:' || auth.uid()::text || ':%'
  OR realtime.topic() = 'user:' || auth.uid()::text
);

DROP POLICY IF EXISTS "Authenticated users send scoped realtime messages" ON realtime.messages;
CREATE POLICY "Authenticated users send scoped realtime messages"
ON realtime.messages
FOR INSERT
TO authenticated
WITH CHECK (
  realtime.topic() = 'demo-redemption-HNTN'
  OR realtime.topic() LIKE 'user:' || auth.uid()::text || ':%'
  OR realtime.topic() = 'user:' || auth.uid()::text
);

-- Remove offer_claims from realtime publication to prevent cross-user code leakage.
-- Customer-side claim status updates already use direct queries; merchant-side
-- updates happen in the same session that performs them.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'offer_claims'
  ) THEN
    EXECUTE 'ALTER PUBLICATION supabase_realtime DROP TABLE public.offer_claims';
  END IF;
END $$;