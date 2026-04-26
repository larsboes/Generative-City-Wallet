// Verifies a customer-uploaded photo for a redeemed offer:
//  1. Confirms the claim belongs to the caller and is redeemed.
//  2. Reads the uploaded photo from storage.
//  3. Parses EXIF DateTimeOriginal.
//  4. Accepts only if taken within ±2h of redemption (strict EXIF).
//  5. Awards points + (optionally) a badge. Stores result in redemption_photos.
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

const POINTS_PER_PHOTO = 10;
const MAX_PHOTOS_PER_CLAIM = 3;
const EXIF_WINDOW_MS = 2 * 60 * 60 * 1000; // ±2h

// ---------- Minimal EXIF DateTimeOriginal parser (JPEG only) ----------
// Walks JPEG markers to find APP1 (EXIF), then locates tag 0x9003.
const parseExifDateTimeOriginal = (buf: Uint8Array): Date | null => {
  if (buf.length < 4 || buf[0] !== 0xff || buf[1] !== 0xd8) return null; // not JPEG
  let i = 2;
  while (i < buf.length) {
    if (buf[i] !== 0xff) return null;
    const marker = buf[i + 1];
    if (marker === 0xda || marker === 0xd9) return null; // SOS / EOI — done
    const size = (buf[i + 2] << 8) | buf[i + 3];
    if (marker === 0xe1 && size > 8) {
      // APP1 — EXIF
      const start = i + 4;
      // "Exif\0\0"
      if (
        buf[start] !== 0x45 || buf[start + 1] !== 0x78 ||
        buf[start + 2] !== 0x69 || buf[start + 3] !== 0x66
      ) {
        i += 2 + size;
        continue;
      }
      const tiffStart = start + 6;
      const little = buf[tiffStart] === 0x49 && buf[tiffStart + 1] === 0x49;
      const u16 = (o: number) =>
        little ? buf[o] | (buf[o + 1] << 8) : (buf[o] << 8) | buf[o + 1];
      const u32 = (o: number) =>
        little
          ? buf[o] | (buf[o + 1] << 8) | (buf[o + 2] << 16) | (buf[o + 3] << 24)
          : (buf[o] << 24) | (buf[o + 1] << 16) | (buf[o + 2] << 8) | buf[o + 3];

      const ifd0Offset = tiffStart + u32(tiffStart + 4);
      const numEntries = u16(ifd0Offset);
      let exifIfdOffset = 0;
      for (let n = 0; n < numEntries; n++) {
        const entry = ifd0Offset + 2 + n * 12;
        const tag = u16(entry);
        if (tag === 0x8769) {
          exifIfdOffset = tiffStart + u32(entry + 8);
          break;
        }
      }
      if (!exifIfdOffset) return null;

      const exifEntries = u16(exifIfdOffset);
      for (let n = 0; n < exifEntries; n++) {
        const entry = exifIfdOffset + 2 + n * 12;
        const tag = u16(entry);
        if (tag === 0x9003) {
          // ASCII string, count bytes, value offset
          const count = u32(entry + 4);
          const valOffset = count <= 4 ? entry + 8 : tiffStart + u32(entry + 8);
          const bytes = buf.slice(valOffset, valOffset + count - 1); // strip null
          const str = new TextDecoder().decode(bytes);
          // Format: "YYYY:MM:DD HH:MM:SS"
          const m = str.match(/^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
          if (!m) return null;
          // Treat as local time of the camera; we have no offset here.
          // Compare as UTC since both reference points are normalised below.
          return new Date(
            Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]),
          );
        }
      }
      return null;
    }
    i += 2 + size;
  }
  return null;
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const auth = req.headers.get("Authorization") ?? "";
    if (!auth.startsWith("Bearer ")) {
      return json({ error: "Unauthorized" }, 401);
    }
    const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
    const ANON = Deno.env.get("SUPABASE_ANON_KEY")!;
    const SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

    const userClient = createClient(SUPABASE_URL, ANON, {
      global: { headers: { Authorization: auth } },
    });
    const admin = createClient(SUPABASE_URL, SERVICE);

    const { data: userRes } = await userClient.auth.getUser();
    const user = userRes?.user;
    if (!user) return json({ error: "Unauthorized" }, 401);

    const body = await req.json().catch(() => null) as
      | { claim_id?: string; storage_path?: string }
      | null;
    if (!body?.claim_id || !body?.storage_path) {
      return json({ error: "claim_id and storage_path required" }, 400);
    }
    if (typeof body.claim_id !== "string" || typeof body.storage_path !== "string") {
      return json({ error: "Invalid input" }, 400);
    }
    // Storage path must be inside the user's folder
    if (!body.storage_path.startsWith(`${user.id}/`)) {
      return json({ error: "Path does not match caller" }, 403);
    }

    // Verify claim belongs to user + is redeemed
    const { data: claim, error: claimErr } = await admin
      .from("offer_claims")
      .select("id, user_id, offer_id, redeemed_at")
      .eq("id", body.claim_id)
      .maybeSingle();
    if (claimErr || !claim) return json({ error: "Claim not found" }, 404);
    if (claim.user_id !== user.id) return json({ error: "Not your claim" }, 403);
    if (!claim.redeemed_at) return json({ error: "Claim not redeemed yet" }, 400);

    // Photo cap per claim
    const { count: existing } = await admin
      .from("redemption_photos")
      .select("id", { count: "exact", head: true })
      .eq("claim_id", claim.id)
      .eq("status", "verified");
    if ((existing ?? 0) >= MAX_PHOTOS_PER_CLAIM) {
      return json({ error: `Max ${MAX_PHOTOS_PER_CLAIM} photos per redemption` }, 400);
    }

    // Resolve offer + business for FK columns
    const { data: offer } = await admin
      .from("offers")
      .select("id, business_id")
      .eq("id", claim.offer_id)
      .maybeSingle();
    if (!offer) return json({ error: "Offer missing" }, 404);

    // Download the photo from storage
    const { data: file, error: dlErr } = await admin.storage
      .from("redemption-photos")
      .download(body.storage_path);
    if (dlErr || !file) {
      return json({ error: `Could not read photo: ${dlErr?.message ?? "unknown"}` }, 400);
    }
    const buf = new Uint8Array(await file.arrayBuffer());

    const takenAt = parseExifDateTimeOriginal(buf);
    const redeemedAt = new Date(claim.redeemed_at);

    // Strict EXIF: reject if missing
    if (!takenAt) {
      await admin.from("redemption_photos").insert({
        user_id: user.id,
        claim_id: claim.id,
        offer_id: offer.id,
        business_id: offer.business_id,
        storage_path: body.storage_path,
        taken_at: null,
        status: "rejected",
        reject_reason: "No EXIF DateTimeOriginal — please share the original camera photo, not a screenshot.",
        points_awarded: 0,
      });
      // Also delete the file so we don't keep junk
      await admin.storage.from("redemption-photos").remove([body.storage_path]);
      return json({
        verified: false,
        reason: "no_exif",
        message: "We couldn't find EXIF metadata. Please upload the original camera photo (not a screenshot).",
      }, 200);
    }

    const drift = Math.abs(takenAt.getTime() - redeemedAt.getTime());
    if (drift > EXIF_WINDOW_MS) {
      await admin.from("redemption_photos").insert({
        user_id: user.id,
        claim_id: claim.id,
        offer_id: offer.id,
        business_id: offer.business_id,
        storage_path: body.storage_path,
        taken_at: takenAt.toISOString(),
        status: "rejected",
        reject_reason: `Photo taken ${Math.round(drift / 60000)} min from redemption (window is ±120 min).`,
        points_awarded: 0,
      });
      await admin.storage.from("redemption-photos").remove([body.storage_path]);
      return json({
        verified: false,
        reason: "out_of_window",
        message: "This photo wasn't taken around the time of your visit.",
      }, 200);
    }

    // ✅ Verified — insert record + ledger + bump points
    const { data: photo, error: insErr } = await admin.from("redemption_photos").insert({
      user_id: user.id,
      claim_id: claim.id,
      offer_id: offer.id,
      business_id: offer.business_id,
      storage_path: body.storage_path,
      taken_at: takenAt.toISOString(),
      status: "verified",
      points_awarded: POINTS_PER_PHOTO,
    }).select("id").maybeSingle();
    if (insErr || !photo) {
      return json({ error: insErr?.message ?? "Insert failed" }, 500);
    }

    // Upsert points total
    const { data: current } = await admin
      .from("customer_points")
      .select("points")
      .eq("user_id", user.id)
      .maybeSingle();
    const newTotal = (current?.points ?? 0) + POINTS_PER_PHOTO;
    await admin.from("customer_points").upsert({
      user_id: user.id,
      points: newTotal,
    });

    await admin.from("points_ledger").insert({
      user_id: user.id,
      amount: POINTS_PER_PHOTO,
      source: "photo_verified",
      claim_id: claim.id,
      photo_id: photo.id,
      note: "Verified post-meal photo",
    });

    // Award badges
    const newBadges: { key: string; label: string; description: string }[] = [];

    // First Bite — first verified photo ever
    const { count: totalVerified } = await admin
      .from("redemption_photos")
      .select("id", { count: "exact", head: true })
      .eq("user_id", user.id)
      .eq("status", "verified");
    if (totalVerified === 1) {
      newBadges.push({
        key: "first_bite",
        label: "First Bite",
        description: "Posted your first verified photo",
      });
    }
    // Photographer — 10 verified photos
    if (totalVerified === 10) {
      newBadges.push({
        key: "photographer",
        label: "Photographer",
        description: "10 verified photos",
      });
    }

    for (const b of newBadges) {
      const { error: badgeErr } = await admin.from("customer_badges").insert({
        user_id: user.id,
        badge_key: b.key,
        label: b.label,
        description: b.description,
      });
      if (!badgeErr) {
        await admin.from("points_ledger").insert({
          user_id: user.id,
          amount: 25,
          source: "badge_unlocked",
          claim_id: claim.id,
          note: `Badge: ${b.label}`,
        });
        await admin.from("customer_points").upsert({
          user_id: user.id,
          points: newTotal + 25,
        });
      }
    }

    return json({
      verified: true,
      points_awarded: POINTS_PER_PHOTO,
      total_points: newTotal + newBadges.length * 25,
      badges: newBadges,
      taken_at: takenAt.toISOString(),
    }, 200);
  } catch (e) {
    console.error("verify-redemption-photo error", e);
    return json({ error: "Internal server error" }, 500);
  }
});

const json = (data: unknown, status: number) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
