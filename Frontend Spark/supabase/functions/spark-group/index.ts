import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.4";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const ANON = Deno.env.get("SUPABASE_ANON_KEY")!;
const SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const randCode = (prefix = "SPARK") =>
  `${prefix}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;

const newShareCode = (venueName?: string | null) => {
  const slug = (venueName ?? "SPARK")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, 6) || "SPARK";
  return `${slug}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  try {
    const authHeader = req.headers.get("Authorization") ?? "";
    const userClient = createClient(SUPABASE_URL, ANON, {
      global: { headers: { Authorization: authHeader } },
    });
    const admin = createClient(SUPABASE_URL, SERVICE);

    const { data: userData } = await userClient.auth.getUser();
    const user = userData.user;
    if (!user) return json({ error: "unauthorized" }, 401);

    const body = await req.json().catch(() => ({}));
    const action = body?.action as string;

    if (action === "start") {
      const offerId = body?.offer_id as string;
      if (!offerId) return json({ error: "offer_id required" }, 400);

      const { data: offer } = await admin
        .from("offers")
        .select("id, business_id, is_locked, unlock_threshold, unlock_window_minutes, status")
        .eq("id", offerId)
        .maybeSingle();
      if (!offer) return json({ error: "offer not found" }, 404);
      if (!offer.is_locked) return json({ error: "offer is not a Spark" }, 400);
      if (offer.status !== "active") return json({ error: "offer not active" }, 400);

      const threshold = Math.max(2, offer.unlock_threshold ?? 4);
      const windowMin = Math.max(5, offer.unlock_window_minutes ?? 30);
      const expiresAt = new Date(Date.now() + windowMin * 60_000).toISOString();

      const { data: venue } = await admin
        .from("businesses").select("name").eq("id", offer.business_id).maybeSingle();

      let groupRow: any = null;
      for (let i = 0; i < 4; i++) {
        const code = newShareCode(venue?.name);
        const { data, error } = await admin
          .from("offer_groups")
          .insert({
            offer_id: offerId, starter_user_id: user.id, share_code: code,
            threshold, expires_at: expiresAt,
          })
          .select("*").single();
        if (!error) { groupRow = data; break; }
      }
      if (!groupRow) return json({ error: "could not create group" }, 500);

      // Auto-join the starter
      const { data: claim, error: cErr } = await admin
        .from("offer_claims")
        .insert({ user_id: user.id, offer_id: offerId, code: randCode(), group_id: groupRow.id })
        .select("code").single();
      if (cErr) return json({ error: cErr.message }, 500);

      return json({
        share_code: groupRow.share_code,
        group_id: groupRow.id,
        threshold,
        expires_at: groupRow.expires_at,
        count: 1,
        unlocked_at: null,
        claim_code: claim.code,
      });
    }

    if (action === "join") {
      const shareCode = body?.share_code as string;
      if (!shareCode) return json({ error: "share_code required" }, 400);

      const { data: group } = await admin
        .from("offer_groups").select("*").eq("share_code", shareCode).maybeSingle();
      if (!group) return json({ error: "group not found" }, 404);

      const expired = new Date(group.expires_at).getTime() < Date.now();

      // Already a member?
      const { data: existing } = await admin
        .from("offer_claims").select("code")
        .eq("group_id", group.id).eq("user_id", user.id).maybeSingle();

      let claimCode = existing?.code as string | undefined;
      if (!existing) {
        if (expired && !group.unlocked_at) return json({ error: "group expired" }, 410);
        const { data: claim, error } = await admin
          .from("offer_claims")
          .insert({ user_id: user.id, offer_id: group.offer_id, code: randCode(), group_id: group.id })
          .select("code").single();
        if (error) return json({ error: error.message }, 500);
        claimCode = claim.code;
      }

      const { count } = await admin
        .from("offer_claims").select("id", { count: "exact", head: true })
        .eq("group_id", group.id);

      let unlockedAt = group.unlocked_at as string | null;
      if (!unlockedAt && (count ?? 0) >= group.threshold && !expired) {
        const { data: up } = await admin
          .from("offer_groups").update({ unlocked_at: new Date().toISOString() })
          .eq("id", group.id).is("unlocked_at", null)
          .select("unlocked_at").maybeSingle();
        unlockedAt = up?.unlocked_at ?? new Date().toISOString();
      }

      return json({
        group_id: group.id,
        offer_id: group.offer_id,
        share_code: group.share_code,
        threshold: group.threshold,
        expires_at: group.expires_at,
        unlocked_at: unlockedAt,
        count: count ?? 0,
        claim_code: claimCode,
        status: unlockedAt ? "unlocked" : expired ? "expired" : "locked",
      });
    }

    if (action === "status") {
      const shareCode = body?.share_code as string;
      if (!shareCode) return json({ error: "share_code required" }, 400);
      const { data: group } = await admin
        .from("offer_groups").select("*").eq("share_code", shareCode).maybeSingle();
      if (!group) return json({ error: "group not found" }, 404);

      const { count } = await admin
        .from("offer_claims").select("id", { count: "exact", head: true })
        .eq("group_id", group.id);

      const { data: mine } = await admin
        .from("offer_claims").select("code")
        .eq("group_id", group.id).eq("user_id", user.id).maybeSingle();

      const expired = new Date(group.expires_at).getTime() < Date.now();
      return json({
        group_id: group.id,
        offer_id: group.offer_id,
        share_code: group.share_code,
        threshold: group.threshold,
        expires_at: group.expires_at,
        unlocked_at: group.unlocked_at,
        count: count ?? 0,
        claim_code: mine?.code ?? null,
        is_member: !!mine,
        status: group.unlocked_at ? "unlocked" : expired ? "expired" : "locked",
      });
    }

    return json({ error: "unknown action" }, 400);
  } catch (e) {
    console.error("spark-group error", e);
    return json({ error: "Internal server error" }, 500);
  }
});
