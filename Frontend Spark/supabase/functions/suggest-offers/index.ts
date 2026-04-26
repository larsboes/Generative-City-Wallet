import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY");
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  try {
    if (!LOVABLE_API_KEY) throw new Error("LOVABLE_API_KEY not configured");

    const authHeader = req.headers.get("Authorization");
    if (!authHeader) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      global: { headers: { Authorization: authHeader } },
    });

    const { data: userData } = await supabase.auth.getUser();
    const user = userData?.user;
    if (!user) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const { data: business, error: bizErr } = await supabase
      .from("businesses")
      .select("id, name, category, address, city, country, latitude, longitude, phone, website, photo_url, rating, price_level, opening_hours")
      .eq("owner_id", user.id)
      .maybeSingle();
    if (bizErr || !business) {
      return new Response(JSON.stringify({ error: "Business not found" }), {
        status: 404,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const { data: stats } = await supabase
      .from("payone_hourly_stats")
      .select("day_of_week, hour, transactions, revenue")
      .eq("business_id", business.id);

    // Aggregate hour-of-day averages
    const hourly: Record<number, { tx: number; rev: number; n: number }> = {};
    (stats ?? []).forEach((s: any) => {
      hourly[s.hour] ??= { tx: 0, rev: 0, n: 0 };
      hourly[s.hour].tx += s.transactions;
      hourly[s.hour].rev += Number(s.revenue);
      hourly[s.hour].n += 1;
    });
    const avgHourly = Object.entries(hourly)
      .map(([h, v]) => ({ hour: Number(h), avg_tx: v.tx / v.n, avg_rev: v.rev / v.n }))
      .sort((a, b) => a.hour - b.hour);
    const overallAvg =
      avgHourly.reduce((s, h) => s + h.avg_tx, 0) / Math.max(1, avgHourly.length);

    // Today's context
    const now = new Date();
    const today = DAY_NAMES[now.getDay()];
    const currentHour = now.getHours();
    // Mock weather (deterministic-ish)
    const conditions = ["sunny", "cloudy", "rainy", "cold", "warm"];
    const weather = conditions[now.getDate() % conditions.length];
    const tempC = 12 + ((now.getDate() * 7) % 18);

    const systemPrompt = `You are Spark, an AI that recommends hyper-personalized, context-aware offers for local restaurants and cafés. You analyze sales data and live context to surface concrete, actionable offer suggestions that drive footfall during quiet windows or capitalize on peak moments. Be specific, data-driven and concise. Each suggestion must reference the data signal that motivates it.`;

    const userPrompt = `Business: ${business.name} (${business.category ?? "café/restaurant"}) in ${business.city ?? business.address ?? "the area"}.

Today: ${today}, current hour ${currentHour}:00. Weather: ${weather}, ${tempC}°C.

Hourly transaction averages (from Payone POS data, last 7 days):
${avgHourly.map((h) => `  ${String(h.hour).padStart(2, "0")}:00 → ${h.avg_tx.toFixed(1)} tx, €${h.avg_rev.toFixed(0)} rev`).join("\n")}

Overall hourly average: ${overallAvg.toFixed(1)} tx.

Generate 3 distinct, high-impact offer suggestions. Each should target a different opportunity (e.g. quiet window, weather reaction, customer retention). Reference specific hours and data points in the reasoning.`;

    const aiRes = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LOVABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-3-flash-preview",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        tools: [
          {
            type: "function",
            function: {
              name: "propose_offers",
              description: "Return 3 offer suggestions",
              parameters: {
                type: "object",
                properties: {
                  suggestions: {
                    type: "array",
                    items: {
                      type: "object",
                      properties: {
                        title: { type: "string", description: "Short headline, ≤8 words" },
                        description: { type: "string", description: "1-sentence offer description shown to customers" },
                        goal: {
                          type: "string",
                          enum: ["fill_quiet_window", "weather_react", "win_back", "acquire_locals", "move_stock", "event_capture"],
                        },
                        discount_label: { type: "string", description: "e.g. '-20% lunch combo' or '€6 fixed price'" },
                        items: { type: "string", description: "Items the offer applies to" },
                        start_time: { type: "string", description: "HH:MM 24h" },
                        end_time: { type: "string", description: "HH:MM 24h" },
                        audience: { type: "string", description: "Who it targets, e.g. 'within 400m', 'lapsed regulars'" },
                        estimated_uplift: { type: "string", description: "e.g. '+18 covers' or '+€220 revenue'" },
                        reasoning: { type: "string", description: "1-2 sentences referencing the data signal" },
                      },
                      required: ["title", "description", "goal", "discount_label", "start_time", "end_time", "audience", "estimated_uplift", "reasoning"],
                      additionalProperties: false,
                    },
                  },
                },
                required: ["suggestions"],
                additionalProperties: false,
              },
            },
          },
        ],
        tool_choice: { type: "function", function: { name: "propose_offers" } },
      }),
    });

    if (!aiRes.ok) {
      if (aiRes.status === 429)
        return new Response(JSON.stringify({ error: "Rate limit exceeded, please try again later." }), { status: 429, headers: { ...corsHeaders, "Content-Type": "application/json" } });
      if (aiRes.status === 402)
        return new Response(JSON.stringify({ error: "Lovable AI credits exhausted. Add funds in Workspace → Usage." }), { status: 402, headers: { ...corsHeaders, "Content-Type": "application/json" } });
      const t = await aiRes.text();
      console.error("AI error", aiRes.status, t);
      return new Response(JSON.stringify({ error: "AI gateway error" }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }

    const aiJson = await aiRes.json();
    const toolCall = aiJson.choices?.[0]?.message?.tool_calls?.[0];
    if (!toolCall) {
      return new Response(JSON.stringify({ error: "No suggestions returned" }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }
    const parsed = JSON.parse(toolCall.function.arguments);
    const suggestions = parsed.suggestions ?? [];

    // Insert into offers table as 'suggested'
    const rows = suggestions.map((s: any) => ({
      business_id: business.id,
      owner_id: user.id,
      title: s.title,
      description: s.description,
      goal: s.goal,
      discount_label: s.discount_label,
      items: s.items ?? null,
      start_time: s.start_time,
      end_time: s.end_time,
      audience: s.audience,
      estimated_uplift: s.estimated_uplift,
      reasoning: s.reasoning,
      source: "ai_suggested",
      status: "suggested",
    }));

    const { data: inserted, error: insErr } = await supabase.from("offers").insert(rows).select();
    if (insErr) {
      console.error("Insert error", insErr);
      return new Response(JSON.stringify({ error: insErr.message }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }

    return new Response(JSON.stringify({ suggestions: inserted }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("suggest-offers error", e);
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
