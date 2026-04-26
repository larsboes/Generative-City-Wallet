ALTER TABLE public.offer_claims REPLICA IDENTITY FULL;
ALTER PUBLICATION supabase_realtime ADD TABLE public.offer_claims;