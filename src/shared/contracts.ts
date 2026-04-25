/**
 * Spark shared contracts — TypeScript interfaces.
 * Single source of truth for dashboard and mobile teams.
 * Mirror of src/backend/models/contracts.py.
 */

// ── Mobile → Backend ──────────────────────────────────────────────────────────

export type MovementMode =
  | "browsing"
  | "commuting"
  | "stationary"
  | "transit_waiting"
  | "exercising"
  | "post_workout"
  | "cycling";

export type WeatherNeed =
  | "warmth_seeking"
  | "refreshment_seeking"
  | "shelter_seeking"
  | "neutral";

export type SocialPreference = "social" | "quiet" | "neutral";
export type PriceTier = "low" | "mid" | "high";

export interface IntentVector {
  grid_cell: string;
  movement_mode: MovementMode;
  time_bucket: string;
  weather_need: WeatherNeed;
  social_preference: SocialPreference;
  price_tier: PriceTier;
  recent_categories: string[];
  dwell_signal: boolean;
  battery_low: boolean;
  session_id: string;
}

// ── Density Signal ────────────────────────────────────────────────────────────

export type DensitySignalType =
  | "FLASH"
  | "PRIORITY"
  | "QUIET"
  | "NORMAL"
  | "NORMALLY_CLOSED";

export interface DensitySignal {
  merchant_id: string;
  density_score: number;
  drop_pct: number;
  signal: DensitySignalType;
  offer_eligible: boolean;
  historical_avg: number;
  current_rate: number;
  current_occupancy_pct?: number;
  predicted_occupancy_pct?: number;
  confidence: number;
  timestamp: string;
}

// ── Composite Context State ──────────────────────────────────────────────────

export type CouponType =
  | "FLASH"
  | "MILESTONE"
  | "TIME_BOUND"
  | "DRINK"
  | "VISIBILITY_ONLY";

export type ColorPalette =
  | "warm_amber"
  | "cool_blue"
  | "deep_green"
  | "electric_purple"
  | "soft_cream"
  | "dark_contrast"
  | "sunset_orange";

export type CardMood =
  | "cozy"
  | "energetic"
  | "refreshing"
  | "celebratory"
  | "calm";

export type ConflictRecommendation =
  | "RECOMMEND"
  | "RECOMMEND_WITH_FRAMING"
  | "DO_NOT_RECOMMEND";

// ── Offer Object (sent to mobile) ────────────────────────────────────────────

export interface OfferObject {
  offer_id: string;
  session_id: string;
  merchant: {
    id: string;
    name: string;
    distance_m: number;
    address: string;
    category: string;
  };
  discount: {
    value: number;
    type: string;
    source: string;
  };
  content: {
    headline: string;
    subtext: string;
    cta_text: string;
    emotional_hook?: string;
  };
  genui: {
    color_palette: ColorPalette;
    typography_weight: string;
    background_style: string;
    imagery_prompt: string;
    urgency_style: string;
    card_mood: CardMood;
  };
  expires_at: string;
  qr_payload?: string;
  explainability?: {
    code: string;
    reason: string;
    score: number;
    metadata?: Record<string, unknown>;
  }[];
}

// ── QR Redemption ─────────────────────────────────────────────────────────────

export interface QRPayload {
  offer_id: string;
  token_hash: string;
  expiry_unix: number;
}

export interface RedemptionValidationResponse {
  valid: boolean;
  offer_id?: string;
  discount_value?: number;
  discount_type?: string;
  error?: "EXPIRED" | "ALREADY_REDEEMED" | "INVALID_TOKEN" | "WRONG_MERCHANT";
}

// ── Cashback Credit ──────────────────────────────────────────────────────────

export interface CashbackCredit {
  session_id: string;
  offer_id: string;
  amount_eur: number;
  merchant_name: string;
  credited_at: string;
  wallet_balance_eur: number;
}

// ── Demo Overrides (Context Slider) ──────────────────────────────────────────

export interface DemoOverrides {
  temp_celsius?: number;
  weather_condition?: string;
  merchant_occupancy_pct?: number;
  social_preference?: SocialPreference;
  time_bucket?: string;
}

export interface GenerateOfferRequest {
  intent: IntentVector;
  merchant_id?: string;
  demo_overrides?: DemoOverrides;
}
