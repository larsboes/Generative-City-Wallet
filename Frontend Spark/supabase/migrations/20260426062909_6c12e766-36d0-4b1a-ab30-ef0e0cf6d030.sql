UPDATE public.businesses
SET photo_url = '/venues/landbaeckerei-ihle.jpg'
WHERE name = 'Landbäckerei IHLE GmbH';

UPDATE public.offers
SET status = 'paused'
WHERE business_id = (SELECT id FROM public.businesses WHERE name = 'Landbäckerei IHLE GmbH')
  AND title <> '4 + 1 free dusted Krapfen';