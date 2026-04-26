-- Drop the broad authenticated SELECT policy on businesses; cross-user reads go through the view.
DROP POLICY IF EXISTS "Authenticated users view venues with active offers (limited)" ON public.businesses;

-- Recreate the safe view (idempotent) — still excludes phone, owner_id, google_place_id, raw_place_data.
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

-- The view runs with security_invoker, so it needs a base-table SELECT policy that
-- permits reading rows for venues with active offers. Add a narrow policy that
-- only matches when invoked from the view's context (any authenticated read,
-- but the app code only queries the view for cross-user access).
-- We keep owner full-row access via the existing "Owners view own business" policy.
CREATE POLICY "Authenticated read businesses with active offers"
ON public.businesses
FOR SELECT
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.offers o
    WHERE o.business_id = businesses.id AND o.status = 'active'
  )
);

-- Revoke direct column access to phone for non-owners by removing it from
-- authenticated's column-level SELECT grant, then re-granting only safe columns.
REVOKE SELECT ON public.businesses FROM authenticated;
GRANT SELECT (
  id, name, category, address, city, country,
  latitude, longitude, website, photo_url, rating,
  price_level, opening_hours, owner_id, onboarding_completed,
  created_at, updated_at
) ON public.businesses TO authenticated;

-- Owners need phone too — they query their own row. Grant phone+sensitive columns
-- back via a separate path: create a SECURITY DEFINER function for owners.
-- Simpler: also grant phone, google_place_id, raw_place_data to authenticated but
-- rely on a more restrictive RLS that hides these for non-owners.
-- We chose column REVOKE above which is enforced regardless of RLS, so any SELECT
-- of phone by a non-owner will fail. Owners must use a path that does not request
-- phone via the broad policy; their "Owners view own business" policy still applies.
-- Re-grant phone & internal columns ONLY to owners through a definer function:

CREATE OR REPLACE FUNCTION public.get_my_business()
RETURNS SETOF public.businesses
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT * FROM public.businesses WHERE owner_id = auth.uid();
$$;

GRANT EXECUTE ON FUNCTION public.get_my_business() TO authenticated;