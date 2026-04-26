-- 1) Restrict offer_groups SELECT to starter or members
DROP POLICY IF EXISTS "Authenticated can view offer groups" ON public.offer_groups;

CREATE POLICY "Starter or members view offer groups"
ON public.offer_groups
FOR SELECT
TO authenticated
USING (
  starter_user_id = auth.uid()
  OR EXISTS (
    SELECT 1 FROM public.offer_claims c
    WHERE c.group_id = offer_groups.id
      AND c.user_id = auth.uid()
  )
);

-- 2) Prevent raw_place_data leakage to non-owners via column privileges.
-- Owners still see everything via "Owners view own business" policy (RLS is row-level;
-- column privileges are enforced in addition). We revoke column access from the
-- 'authenticated' role for sensitive columns and grant the rest explicitly.
REVOKE SELECT ON public.businesses FROM authenticated;

GRANT SELECT (
  id, owner_id, name, category, address, city, country,
  latitude, longitude, website, photo_url, price_level, rating,
  opening_hours, google_place_id, onboarding_completed,
  created_at, updated_at, phone
) ON public.businesses TO authenticated;
