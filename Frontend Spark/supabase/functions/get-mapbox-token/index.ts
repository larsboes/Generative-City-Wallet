const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve((req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  const token = Deno.env.get("MAPBOX_PUBLIC_TOKEN");
  if (!token) {
    return new Response(JSON.stringify({ error: "MAPBOX_PUBLIC_TOKEN not configured" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
  return new Response(JSON.stringify({ token }), {
    headers: { ...corsHeaders, "Content-Type": "application/json" },
    status: 200,
  });
});
