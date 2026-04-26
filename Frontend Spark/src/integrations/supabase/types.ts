export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      business_notification_prefs: {
        Row: {
          business_id: string
          created_at: string
          id: string
          notify_low_performance: boolean
          notify_new_claims: boolean
          notify_offer_expiring: boolean
          notify_redemptions: boolean
          notify_suggestions: boolean
          notify_weekly_digest: boolean
          owner_id: string
          quiet_hours_end: string | null
          quiet_hours_start: string | null
          updated_at: string
        }
        Insert: {
          business_id: string
          created_at?: string
          id?: string
          notify_low_performance?: boolean
          notify_new_claims?: boolean
          notify_offer_expiring?: boolean
          notify_redemptions?: boolean
          notify_suggestions?: boolean
          notify_weekly_digest?: boolean
          owner_id: string
          quiet_hours_end?: string | null
          quiet_hours_start?: string | null
          updated_at?: string
        }
        Update: {
          business_id?: string
          created_at?: string
          id?: string
          notify_low_performance?: boolean
          notify_new_claims?: boolean
          notify_offer_expiring?: boolean
          notify_redemptions?: boolean
          notify_suggestions?: boolean
          notify_weekly_digest?: boolean
          owner_id?: string
          quiet_hours_end?: string | null
          quiet_hours_start?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      businesses: {
        Row: {
          address: string | null
          category: string | null
          city: string | null
          country: string | null
          created_at: string
          google_place_id: string | null
          id: string
          latitude: number | null
          longitude: number | null
          name: string
          onboarding_completed: boolean
          opening_hours: Json | null
          owner_id: string
          phone: string | null
          photo_url: string | null
          price_level: number | null
          rating: number | null
          raw_place_data: Json | null
          updated_at: string
          website: string | null
        }
        Insert: {
          address?: string | null
          category?: string | null
          city?: string | null
          country?: string | null
          created_at?: string
          google_place_id?: string | null
          id?: string
          latitude?: number | null
          longitude?: number | null
          name: string
          onboarding_completed?: boolean
          opening_hours?: Json | null
          owner_id: string
          phone?: string | null
          photo_url?: string | null
          price_level?: number | null
          rating?: number | null
          raw_place_data?: Json | null
          updated_at?: string
          website?: string | null
        }
        Update: {
          address?: string | null
          category?: string | null
          city?: string | null
          country?: string | null
          created_at?: string
          google_place_id?: string | null
          id?: string
          latitude?: number | null
          longitude?: number | null
          name?: string
          onboarding_completed?: boolean
          opening_hours?: Json | null
          owner_id?: string
          phone?: string | null
          photo_url?: string | null
          price_level?: number | null
          rating?: number | null
          raw_place_data?: Json | null
          updated_at?: string
          website?: string | null
        }
        Relationships: []
      }
      customer_badges: {
        Row: {
          awarded_at: string
          badge_key: string
          description: string | null
          id: string
          label: string
          user_id: string
        }
        Insert: {
          awarded_at?: string
          badge_key: string
          description?: string | null
          id?: string
          label: string
          user_id: string
        }
        Update: {
          awarded_at?: string
          badge_key?: string
          description?: string | null
          id?: string
          label?: string
          user_id?: string
        }
        Relationships: []
      }
      customer_points: {
        Row: {
          created_at: string
          points: number
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          points?: number
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          points?: number
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      customer_prefs: {
        Row: {
          city: string
          created_at: string
          lat: number | null
          lng: number | null
          notify_evening: boolean
          notify_lunch: boolean
          notify_weather: boolean
          updated_at: string
          user_id: string
        }
        Insert: {
          city?: string
          created_at?: string
          lat?: number | null
          lng?: number | null
          notify_evening?: boolean
          notify_lunch?: boolean
          notify_weather?: boolean
          updated_at?: string
          user_id: string
        }
        Update: {
          city?: string
          created_at?: string
          lat?: number | null
          lng?: number | null
          notify_evening?: boolean
          notify_lunch?: boolean
          notify_weather?: boolean
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      demo_redemptions: {
        Row: {
          code: string
          created_at: string
          redeemed_at: string | null
          updated_at: string
        }
        Insert: {
          code: string
          created_at?: string
          redeemed_at?: string | null
          updated_at?: string
        }
        Update: {
          code?: string
          created_at?: string
          redeemed_at?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      offer_bookmarks: {
        Row: {
          created_at: string
          id: string
          offer_id: string
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          offer_id: string
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          offer_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "offer_bookmarks_offer_id_fkey"
            columns: ["offer_id"]
            isOneToOne: false
            referencedRelation: "offers"
            referencedColumns: ["id"]
          },
        ]
      }
      offer_claims: {
        Row: {
          amount_cents: number | null
          claimed_at: string
          code: string
          group_id: string | null
          id: string
          offer_id: string
          redeemed_at: string | null
          user_id: string
        }
        Insert: {
          amount_cents?: number | null
          claimed_at?: string
          code: string
          group_id?: string | null
          id?: string
          offer_id: string
          redeemed_at?: string | null
          user_id: string
        }
        Update: {
          amount_cents?: number | null
          claimed_at?: string
          code?: string
          group_id?: string | null
          id?: string
          offer_id?: string
          redeemed_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "offer_claims_offer_id_fkey"
            columns: ["offer_id"]
            isOneToOne: false
            referencedRelation: "offers"
            referencedColumns: ["id"]
          },
        ]
      }
      offer_groups: {
        Row: {
          expires_at: string
          id: string
          offer_id: string
          share_code: string
          started_at: string
          starter_user_id: string
          threshold: number
          unlocked_at: string | null
        }
        Insert: {
          expires_at: string
          id?: string
          offer_id: string
          share_code: string
          started_at?: string
          starter_user_id: string
          threshold: number
          unlocked_at?: string | null
        }
        Update: {
          expires_at?: string
          id?: string
          offer_id?: string
          share_code?: string
          started_at?: string
          starter_user_id?: string
          threshold?: number
          unlocked_at?: string | null
        }
        Relationships: []
      }
      offers: {
        Row: {
          accepted_count: number
          audience: string | null
          business_id: string
          created_at: string
          days_of_week: string[] | null
          description: string
          discount_label: string | null
          end_time: string | null
          estimated_uplift: string | null
          expires_at: string | null
          goal: string | null
          id: string
          is_locked: boolean
          items: string | null
          launched_at: string | null
          owner_id: string
          reasoning: string | null
          source: string
          start_time: string | null
          status: Database["public"]["Enums"]["offer_status"]
          title: string
          unlock_threshold: number | null
          unlock_window_minutes: number | null
          updated_at: string
          views_count: number
        }
        Insert: {
          accepted_count?: number
          audience?: string | null
          business_id: string
          created_at?: string
          days_of_week?: string[] | null
          description: string
          discount_label?: string | null
          end_time?: string | null
          estimated_uplift?: string | null
          expires_at?: string | null
          goal?: string | null
          id?: string
          is_locked?: boolean
          items?: string | null
          launched_at?: string | null
          owner_id: string
          reasoning?: string | null
          source?: string
          start_time?: string | null
          status?: Database["public"]["Enums"]["offer_status"]
          title: string
          unlock_threshold?: number | null
          unlock_window_minutes?: number | null
          updated_at?: string
          views_count?: number
        }
        Update: {
          accepted_count?: number
          audience?: string | null
          business_id?: string
          created_at?: string
          days_of_week?: string[] | null
          description?: string
          discount_label?: string | null
          end_time?: string | null
          estimated_uplift?: string | null
          expires_at?: string | null
          goal?: string | null
          id?: string
          is_locked?: boolean
          items?: string | null
          launched_at?: string | null
          owner_id?: string
          reasoning?: string | null
          source?: string
          start_time?: string | null
          status?: Database["public"]["Enums"]["offer_status"]
          title?: string
          unlock_threshold?: number | null
          unlock_window_minutes?: number | null
          updated_at?: string
          views_count?: number
        }
        Relationships: [
          {
            foreignKeyName: "offers_business_id_fkey"
            columns: ["business_id"]
            isOneToOne: false
            referencedRelation: "businesses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "offers_business_id_fkey"
            columns: ["business_id"]
            isOneToOne: false
            referencedRelation: "public_businesses"
            referencedColumns: ["id"]
          },
        ]
      }
      payone_hourly_stats: {
        Row: {
          avg_basket: number
          business_id: string
          created_at: string
          day_of_week: number
          hour: number
          id: string
          owner_id: string
          revenue: number
          transactions: number
        }
        Insert: {
          avg_basket?: number
          business_id: string
          created_at?: string
          day_of_week: number
          hour: number
          id?: string
          owner_id: string
          revenue?: number
          transactions?: number
        }
        Update: {
          avg_basket?: number
          business_id?: string
          created_at?: string
          day_of_week?: number
          hour?: number
          id?: string
          owner_id?: string
          revenue?: number
          transactions?: number
        }
        Relationships: [
          {
            foreignKeyName: "payone_hourly_stats_business_id_fkey"
            columns: ["business_id"]
            isOneToOne: false
            referencedRelation: "businesses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "payone_hourly_stats_business_id_fkey"
            columns: ["business_id"]
            isOneToOne: false
            referencedRelation: "public_businesses"
            referencedColumns: ["id"]
          },
        ]
      }
      points_ledger: {
        Row: {
          amount: number
          claim_id: string | null
          created_at: string
          id: string
          note: string | null
          photo_id: string | null
          source: Database["public"]["Enums"]["points_source"]
          user_id: string
        }
        Insert: {
          amount: number
          claim_id?: string | null
          created_at?: string
          id?: string
          note?: string | null
          photo_id?: string | null
          source: Database["public"]["Enums"]["points_source"]
          user_id: string
        }
        Update: {
          amount?: number
          claim_id?: string | null
          created_at?: string
          id?: string
          note?: string | null
          photo_id?: string | null
          source?: Database["public"]["Enums"]["points_source"]
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "points_ledger_claim_id_fkey"
            columns: ["claim_id"]
            isOneToOne: false
            referencedRelation: "offer_claims"
            referencedColumns: ["id"]
          },
        ]
      }
      profiles: {
        Row: {
          created_at: string
          full_name: string | null
          id: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          full_name?: string | null
          id: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          full_name?: string | null
          id?: string
          updated_at?: string
        }
        Relationships: []
      }
      redemption_photos: {
        Row: {
          business_id: string
          claim_id: string
          created_at: string
          id: string
          offer_id: string
          points_awarded: number
          reject_reason: string | null
          status: Database["public"]["Enums"]["photo_status"]
          storage_path: string
          taken_at: string | null
          user_id: string
        }
        Insert: {
          business_id: string
          claim_id: string
          created_at?: string
          id?: string
          offer_id: string
          points_awarded?: number
          reject_reason?: string | null
          status: Database["public"]["Enums"]["photo_status"]
          storage_path: string
          taken_at?: string | null
          user_id: string
        }
        Update: {
          business_id?: string
          claim_id?: string
          created_at?: string
          id?: string
          offer_id?: string
          points_awarded?: number
          reject_reason?: string | null
          status?: Database["public"]["Enums"]["photo_status"]
          storage_path?: string
          taken_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "redemption_photos_business_id_fkey"
            columns: ["business_id"]
            isOneToOne: false
            referencedRelation: "businesses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "redemption_photos_business_id_fkey"
            columns: ["business_id"]
            isOneToOne: false
            referencedRelation: "public_businesses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "redemption_photos_claim_id_fkey"
            columns: ["claim_id"]
            isOneToOne: false
            referencedRelation: "offer_claims"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "redemption_photos_offer_id_fkey"
            columns: ["offer_id"]
            isOneToOne: false
            referencedRelation: "offers"
            referencedColumns: ["id"]
          },
        ]
      }
      user_roles: {
        Row: {
          created_at: string
          id: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      public_businesses: {
        Row: {
          address: string | null
          category: string | null
          city: string | null
          country: string | null
          id: string | null
          latitude: number | null
          longitude: number | null
          name: string | null
          opening_hours: Json | null
          photo_url: string | null
          price_level: number | null
          rating: number | null
          website: string | null
        }
        Insert: {
          address?: string | null
          category?: string | null
          city?: string | null
          country?: string | null
          id?: string | null
          latitude?: number | null
          longitude?: number | null
          name?: string | null
          opening_hours?: Json | null
          photo_url?: string | null
          price_level?: number | null
          rating?: number | null
          website?: string | null
        }
        Update: {
          address?: string | null
          category?: string | null
          city?: string | null
          country?: string | null
          id?: string | null
          latitude?: number | null
          longitude?: number | null
          name?: string | null
          opening_hours?: Json | null
          photo_url?: string | null
          price_level?: number | null
          rating?: number | null
          website?: string | null
        }
        Relationships: []
      }
    }
    Functions: {
      award_redemption_points: { Args: { _claim_id: string }; Returns: number }
      get_my_business: {
        Args: never
        Returns: {
          address: string | null
          category: string | null
          city: string | null
          country: string | null
          created_at: string
          google_place_id: string | null
          id: string
          latitude: number | null
          longitude: number | null
          name: string
          onboarding_completed: boolean
          opening_hours: Json | null
          owner_id: string
          phone: string | null
          photo_url: string | null
          price_level: number | null
          rating: number | null
          raw_place_data: Json | null
          updated_at: string
          website: string | null
        }[]
        SetofOptions: {
          from: "*"
          to: "businesses"
          isOneToOne: false
          isSetofReturn: true
        }
      }
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
      seed_payone_mock: { Args: { _business_id: string }; Returns: undefined }
    }
    Enums: {
      app_role: "customer" | "business" | "admin"
      offer_status: "suggested" | "active" | "paused" | "expired" | "dismissed"
      photo_status: "verified" | "rejected"
      points_source: "offer_redeemed" | "photo_verified" | "badge_unlocked"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: ["customer", "business", "admin"],
      offer_status: ["suggested", "active", "paused", "expired", "dismissed"],
      photo_status: ["verified", "rejected"],
      points_source: ["offer_redeemed", "photo_verified", "badge_unlocked"],
    },
  },
} as const
