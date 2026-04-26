const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY");

interface VenueCandidate {
  id: string;
  name: string;
  category: string | null;
  city: string | null;
  address: string | null;
  rating: number | null;
  price_level: number | null;
  offer_title?: string | null;
  offer_discount?: string | null;
}

interface Body {
  event: {
    title: string;
    type: string; // "1:1", "coffee chat", "lunch", "team", "interview", etc.
    start: string; // HH:MM
    end: string;
    notes?: string;
    attendees?: number;
  };
  candidates: VenueCandidate[];
  city?: string;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  try {
    if (!LOVABLE_API_KEY) throw new Error("LOVABLE_API_KEY not configured");

    const body = (await req.json()) as Body;
    if (!body?.event?.title || !Array.isArray(body.candidates)) {
      return new Response(JSON.stringify({ error: "Invalid request body" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const candidates = body.candidates.slice(0, 25);
    const ev = body.event;

    const system = `You are a concierge picking the best local venue for a calendar event.
Match vibe to event type:
- "1:1" / "coffee chat" → quiet cafés, low noise, comfy seating
- "lunch" / "team lunch" → restaurants with quick service
- "interview" → quiet, neutral, professional cafés
- "client meeting" → upscale, well-rated, calm
- "happy hour" / "after work" → bars, lively
Prefer venues with active offers when quality is comparable. Stay realistic — only pick from the supplied list.`;

    const user = `Event:
- Title: ${ev.title}
- Type: ${ev.type}
- Time: ${ev.start}–${ev.end}
- Attendees: ${ev.attendees ?? 2}
- Notes: ${ev.notes ?? "(none)"}
- City: ${body.city ?? "unknown"}

Candidate venues (id | name | category | rating | price | active offer):
${candidates
  .map(
    (c) =>
      `${c.id} | ${c.name} | ${c.category ?? "—"} | ${
        c.rating ?? "—"
      } | ${c.price_level ?? "—"} | ${
        c.offer_title ? `${c.offer_title} (${c.offer_discount ?? ""})` : "—"
      }`,
  )
  .join("\n")}

Pick up to 3 venues ranked best→worst. Reference the event vibe and any active offer.`;

    const aiRes = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LOVABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-2.5-flash",
        messages: [
          { role: "system", content: system },
          { role: "user", content: user },
        ],
        tools: [
          {
            type: "function",
            function: {
              name: "recommend_venues",
              description: "Return ranked venue recommendations for the event.",
              parameters: {
                type: "object",
                properties: {
                  picks: {
                    type: "array",
                    items: {
                      type: "object",
                      properties: {
                        venue_id: { type: "string", description: "Must match a candidate id" },
                        reason: {
                          type: "string",
                          description: "1 sentence — why this venue fits the event.",
                        },
                      },
                      required: ["venue_id", "reason"],
                      additionalProperties: false,
                    },
                  },
                  summary: {
                    type: "string",
                    description: "Short one-line recap of the recommendation strategy.",
                  },
                },
                required: ["picks", "summary"],
                additionalProperties: false,
              },
            },
          },
        ],
        tool_choice: { type: "function", function: { name: "recommend_venues" } },
      }),
    });

    if (!aiRes.ok) {
      if (aiRes.status === 429)
        return new Response(JSON.stringify({ error: "Rate limit exceeded — try again in a moment." }), {
          status: 429,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      if (aiRes.status === 402)
        return new Response(JSON.stringify({ error: "AI credits exhausted." }), {
          status: 402,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      const t = await aiRes.text();
      console.error("AI error", aiRes.status, t);
      return new Response(JSON.stringify({ error: "AI gateway error" }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const aiJson = await aiRes.json();
    const toolCall = aiJson.choices?.[0]?.message?.tool_calls?.[0];
    if (!toolCall) {
      return new Response(JSON.stringify({ error: "No recommendation returned" }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    const parsed = JSON.parse(toolCall.function.arguments);
    const candidateMap = new Map(candidates.map((c) => [c.id, c]));
    const picks = (parsed.picks ?? [])
      .filter((p: { venue_id: string }) => candidateMap.has(p.venue_id))
      .map((p: { venue_id: string; reason: string }) => ({
        ...candidateMap.get(p.venue_id)!,
        reason: p.reason,
      }));

    return new Response(
      JSON.stringify({ picks, summary: parsed.summary ?? "" }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  } catch (e) {
    console.error("suggest-event-venue error", e);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  }
});
