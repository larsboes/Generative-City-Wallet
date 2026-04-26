import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

const APIFY_TOKEN = Deno.env.get("APIFY_API_TOKEN");
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;

interface LookupBody {
  name: string;
  location: string;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  try {
    // --- AuthN: require a valid JWT ---
    const authHeader = req.headers.get("Authorization") ?? "";
    if (!authHeader.startsWith("Bearer ")) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    const userClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      global: { headers: { Authorization: authHeader } },
    });
    const { data: userData, error: userErr } = await userClient.auth.getUser();
    if (userErr || !userData?.user) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    const userId = userData.user.id;

    // --- AuthZ: only business-role users can call this expensive endpoint ---
    const { data: roleRow } = await userClient
      .from("user_roles")
      .select("role")
      .eq("user_id", userId)
      .eq("role", "business")
      .maybeSingle();
    if (!roleRow) {
      return new Response(JSON.stringify({ error: "Forbidden" }), {
        status: 403,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (!APIFY_TOKEN) throw new Error("APIFY_API_TOKEN not configured");

    const body = (await req.json()) as LookupBody;
    const name = (body.name || "").trim();
    const location = (body.location || "").trim();
    if (!name || name.length > 200 || !location || location.length > 200) {
      return new Response(JSON.stringify({ error: "Invalid name or location" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const url = `https://api.apify.com/v2/acts/compass~crawler-google-places/run-sync-get-dataset-items?token=${APIFY_TOKEN}`;
    const input = {
      searchStringsArray: [`${name} ${location}`],
      locationQuery: location,
      maxCrawledPlacesPerSearch: 5,
      language: "en",
      skipClosedPlaces: false,
    };

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });

    if (!res.ok) {
      const text = await res.text();
      console.error("Apify error", res.status, text);
      return new Response(
        JSON.stringify({ error: "Upstream lookup failed" }),
        { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    const items = (await res.json()) as any[];
    const matches = (items || []).slice(0, 5).map((p) => ({
      placeId: p.placeId ?? p.placeIdHash ?? null,
      name: p.title ?? p.name ?? "",
      category: p.categoryName ?? (Array.isArray(p.categories) ? p.categories[0] : null) ?? null,
      address: p.address ?? p.street ?? "",
      city: p.city ?? null,
      country: p.countryCode ?? p.country ?? null,
      latitude: p.location?.lat ?? null,
      longitude: p.location?.lng ?? null,
      phone: p.phone ?? p.phoneUnformatted ?? null,
      website: p.website ?? null,
      photoUrl: p.imageUrl ?? (Array.isArray(p.imageUrls) ? p.imageUrls[0] : null) ?? null,
      rating: p.totalScore ?? p.rating ?? null,
      priceLevel: typeof p.price === "string" ? p.price.length : null,
      openingHours: p.openingHours ?? null,
      raw: p,
    }));

    return new Response(JSON.stringify({ matches }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error("lookup-business error:", err);
    return new Response(JSON.stringify({ error: "Internal server error" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
