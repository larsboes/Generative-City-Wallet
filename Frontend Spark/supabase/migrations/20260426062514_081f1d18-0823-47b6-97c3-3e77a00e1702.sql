DO $$
DECLARE
  _owner uuid := 'a36991a1-077e-448c-827a-ee79c8c79f46'; -- existing demo business owner
  _bid uuid;
BEGIN
  INSERT INTO public.businesses (
    owner_id, name, category, address, city, country,
    latitude, longitude, phone, website, rating, price_level,
    onboarding_completed
  ) VALUES (
    _owner,
    'Landbäckerei IHLE GmbH',
    'Bakery',
    'Balanstraße 73',
    'München',
    'Germany',
    48.1198, 11.5968,
    NULL,
    'https://www.ihle-baeckerei.de',
    4.3, 1,
    true
  )
  RETURNING id INTO _bid;

  INSERT INTO public.offers (
    business_id, owner_id, title, description, discount_label,
    status, source, launched_at, expires_at
  ) VALUES
  (_bid, _owner,
    'Pick any 2 croissants',
    'Buttery, flaky and freshly baked — choose any two croissants from the counter and treat yourself.',
    '2 for 1 selection',
    'active', 'manual', now(), now() + interval '30 days'),
  (_bid, _owner,
    '4 + 1 free dusted Krapfen',
    'Sugar-dusted German doughnuts, still warm. Grab four and the fifth is on us.',
    'Buy 4, get 1 free',
    'active', 'manual', now(), now() + interval '30 days'),
  (_bid, _owner,
    'Quarkbällchen — 10% off',
    'Pillowy curd-cheese bites, golden outside and soft inside. Ten percent off, today only-ish.',
    '−10%',
    'active', 'manual', now(), now() + interval '30 days'),
  (_bid, _owner,
    '3 Bavarian pretzels, reduced',
    'Hand-twisted pretzels with that perfect salty crust. Take three at a friendlier price.',
    '3 for less',
    'active', 'manual', now(), now() + interval '30 days');
END $$;