/**
 * Spark shared contracts — TypeScript interfaces.
 * Consumed by `apps/mobile` and `apps/web-dashboard` via workspace `@spark/shared`.
 * Mirror `apps/api/src/spark/models/contracts.py` (Pydantic) — keep fields in sync.
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

export interface MerchantDemand {
  density_score: number;
  drop_pct: number;
  signal: DensitySignalType;
  offer_eligible: boolean;
  current_occupancy_pct?: number;
  predicted_occupancy_pct?: number;
}

export interface ActiveCoupon {
  type?: CouponType;
  max_discount_pct: number;
  valid_window_min: number;
  config?: Record<string, unknown>;
}

export interface MerchantContext {
  id: string;
  name: string;
  category: string;
  distance_m: number;
  address: string;
  demand: MerchantDemand;
  active_coupon: ActiveCoupon;
  inventory_signal?: string;
  tone_preference?: string;
}

export interface UserContext {
  intent: IntentVector;
  preference_scores: Record<string, number>;
  social_preference: SocialPreference;
  price_tier: PriceTier;
}

export interface EnvironmentContext {
  weather_condition: string;
  temp_celsius: number;
  feels_like_celsius: number;
  weather_need: string;
  vibe_signal: string;
}

export interface ConflictResolutionContext {
  recommendation: ConflictRecommendation;
  framing_band?: string;
  allowed_vocabulary: string[];
  banned_vocabulary: string[];
}

export interface DecisionTraceItem {
  code: string;
  reason: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface OfferDecisionTrace {
  recommendation: ConflictRecommendation;
  selected_merchant_id?: string;
  selected_merchant_score: number;
  recheck_in_minutes?: number;
  candidate_scores: Record<string, unknown>[];
  trace: DecisionTraceItem[];
}

export interface CompositeContextState {
  timestamp: string;
  session_id: string;
  user: UserContext;
  merchant: MerchantContext;
  environment: EnvironmentContext;
  conflict_resolution: ConflictResolutionContext;
  decision_trace?: OfferDecisionTrace;
}

// ── LLM Output (raw, pre-rails) ──────────────────────────────────────────────

export interface LLMContent {
  headline: string;
  subtext: string;
  cta_text: string;
  emotional_hook?: string;
}

export interface LLMGenUI {
  color_palette: ColorPalette;
  typography_weight: string;
  background_style: string;
  imagery_prompt: string;
  urgency_style: string;
  card_mood: CardMood;
}

export interface LLMOfferOutput {
  content: LLMContent;
  genui: LLMGenUI;
  framing_band_used: string;
}

// ── Offer Object (sent to mobile) ────────────────────────────────────────────

export type DiscountType = "percentage" | "cover_refund" | "drink" | "none";

export interface DiscountInfo {
  value: number;
  type: DiscountType;
  source: string;
}

export interface MerchantInfo {
  id: string;
  name: string;
  distance_m: number;
  address: string;
  category: string;
}

export interface AuditInfo {
  rails_applied: boolean;
  discount_original_llm: number;
  discount_capped_to: number;
  composite_state_hash: string;
}

export interface ExplainabilityReason {
  code: string;
  reason: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface OfferObject {
  offer_id: string;
  session_id: string;
  merchant: MerchantInfo;
  discount: DiscountInfo;
  content: LLMContent;
  genui: LLMGenUI;
  expires_at: string;
  qr_payload?: string;
  explainability: ExplainabilityReason[];
  _audit?: AuditInfo;
}

// ── QR Redemption ─────────────────────────────────────────────────────────────

export interface QRPayload {
  offer_id: string;
  token_hash: string;
  expiry_unix: number;
}

export interface RedemptionValidationRequest {
  qr_payload: string;
  merchant_id: string;
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

// ── Conflict Resolution (standalone endpoint) ────────────────────────────────

export interface ConflictResolveRequest {
  merchant_id: string;
  user_social_pref: SocialPreference;
  current_txn_rate: number;
  current_dt: string;
  active_coupon?: Record<string, unknown>;
}

export interface ConflictResolveResponse {
  recommendation: ConflictRecommendation;
  framing_band?: string;
  coupon_mechanism?: string;
  reason: string;
  recheck_in_minutes?: number;
}
