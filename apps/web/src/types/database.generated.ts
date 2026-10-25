export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[]

export type Database = {
  
  "public": {
          Tables: {
            "saxo_source_units": {
                  Row: {
                    "ciphertext": string,"content_hash": string,"created_at": string,"environment": string,"id": string,"kind": string,"retrieved_at": string,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "ciphertext": string,"content_hash": string,"created_at"?: string,"environment": string,"id"?: string,"kind": string,"retrieved_at": string,"user_id": string
                  }
                  Update: {
                    "ciphertext"?: string,"content_hash"?: string,"created_at"?: string,"environment"?: string,"id"?: string,"kind"?: string,"retrieved_at"?: string,"user_id"?: string
                  }
                  Relationships: [
                    
                  ]
                },"saxo_token_vault": {
                  Row: {
                    "ciphertext": string,"environment": string,"generation": number,"rotated_at": string | null,"status": string,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "ciphertext": string,"environment": string,"generation"?: number,"rotated_at"?: string | null,"status"?: string,"user_id": string
                  }
                  Update: {
                    "ciphertext"?: string,"environment"?: string,"generation"?: number,"rotated_at"?: string | null,"status"?: string,"user_id"?: string
                  }
                  Relationships: [
                    
                  ]
                },"user_settings": {
                  Row: {
                    "created_at": string,"locale": string,"timezone": string,"updated_at": string,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "created_at"?: string,"locale"?: string,"timezone"?: string,"updated_at"?: string,"user_id": string
                  }
                  Update: {
                    "created_at"?: string,"locale"?: string,"timezone"?: string,"updated_at"?: string,"user_id"?: string
                  }
                  Relationships: [
                    
                  ]
                },"wealth_accounts": {
                  Row: {
                    "created_at": string,"currency": string,"environment": string,"id": string,"last_attempted_refresh_at": string | null,"last_successful_refresh_at": string | null,"name": string,"provider": string,"source_status": string,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "created_at"?: string,"currency": string,"environment": string,"id"?: string,"last_attempted_refresh_at"?: string | null,"last_successful_refresh_at"?: string | null,"name": string,"provider": string,"source_status"?: string,"user_id": string
                  }
                  Update: {
                    "created_at"?: string,"currency"?: string,"environment"?: string,"id"?: string,"last_attempted_refresh_at"?: string | null,"last_successful_refresh_at"?: string | null,"name"?: string,"provider"?: string,"source_status"?: string,"user_id"?: string
                  }
                  Relationships: [
                    
                  ]
                },"wealth_allocation_targets": {
                  Row: {
                    "asset_class": string,"target_weight_bps": number,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "asset_class": string,"target_weight_bps": number,"user_id": string
                  }
                  Update: {
                    "asset_class"?: string,"target_weight_bps"?: number,"user_id"?: string
                  }
                  Relationships: [
                    
                  ]
                },"wealth_financial_events": {
                  Row: {
                    "account_id": string,"amount_minor": number,"created_at": string,"currency": string,"event_type": string,"id": string,"note": string | null,"occurred_on": string,"related_instrument_id": string | null,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "account_id": string,"amount_minor": number,"created_at"?: string,"currency": string,"event_type": string,"id"?: string,"note"?: string | null,"occurred_on": string,"related_instrument_id"?: string | null,"user_id": string
                  }
                  Update: {
                    "account_id"?: string,"amount_minor"?: number,"created_at"?: string,"currency"?: string,"event_type"?: string,"id"?: string,"note"?: string | null,"occurred_on"?: string,"related_instrument_id"?: string | null,"user_id"?: string
                  }
                  Relationships: [
                    {
      foreignKeyName: "wealth_financial_events_account_id_fkey"
      columns: ["account_id"]
isOneToOne: false
      referencedRelation: "wealth_accounts"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "wealth_financial_events_related_instrument_id_fkey"
      columns: ["related_instrument_id"]
isOneToOne: false
      referencedRelation: "wealth_instruments"
      referencedColumns: ["id"]
    }
                  ]
                },"wealth_fx_rates": {
                  Row: {
                    "base_currency": string,"created_at": string,"id": string,"observation_date": string,"quote_currency": string,"rate": number,"retrieved_at": string,"source": string,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "base_currency": string,"created_at"?: string,"id"?: string,"observation_date": string,"quote_currency": string,"rate": number,"retrieved_at": string,"source": string,"user_id": string
                  }
                  Update: {
                    "base_currency"?: string,"created_at"?: string,"id"?: string,"observation_date"?: string,"quote_currency"?: string,"rate"?: number,"retrieved_at"?: string,"source"?: string,"user_id"?: string
                  }
                  Relationships: [
                    
                  ]
                },"wealth_import_batches": {
                  Row: {
                    "created_at": string,"error_summary": string | null,"id": string,"idempotency_key": string,"source_label": string,"status": string,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "created_at"?: string,"error_summary"?: string | null,"id"?: string,"idempotency_key": string,"source_label": string,"status": string,"user_id": string
                  }
                  Update: {
                    "created_at"?: string,"error_summary"?: string | null,"id"?: string,"idempotency_key"?: string,"source_label"?: string,"status"?: string,"user_id"?: string
                  }
                  Relationships: [
                    
                  ]
                },"wealth_instruments": {
                  Row: {
                    "asset_class": string,"created_at": string,"currency": string,"id": string,"isin": string | null,"name": string,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "asset_class": string,"created_at"?: string,"currency": string,"id"?: string,"isin"?: string | null,"name": string,"user_id": string
                  }
                  Update: {
                    "asset_class"?: string,"created_at"?: string,"currency"?: string,"id"?: string,"isin"?: string | null,"name"?: string,"user_id"?: string
                  }
                  Relationships: [
                    
                  ]
                },"wealth_journal_events": {
                  Row: {
                    "account_id": string,"batch_id": string | null,"cash_amount_minor": number | null,"correction_of": string | null,"created_at": string,"currency": string,"event_type": string,"fees_minor": number,"fx_rate_id": string | null,"id": string,"idempotency_key": string,"instrument_id": string | null,"occurred_on": string,"quantity": number | null,"settled_on": string | null,"source_ref": string | null,"source_type": string,"split_denominator": number | null,"split_numerator": number | null,"tax_minor": number,"transfer_group_id": string | null,"unit_price_minor": number | null,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "account_id": string,"batch_id"?: string | null,"cash_amount_minor"?: number | null,"correction_of"?: string | null,"created_at"?: string,"currency": string,"event_type": string,"fees_minor"?: number,"fx_rate_id"?: string | null,"id"?: string,"idempotency_key": string,"instrument_id"?: string | null,"occurred_on": string,"quantity"?: number | null,"settled_on"?: string | null,"source_ref"?: string | null,"source_type": string,"split_denominator"?: number | null,"split_numerator"?: number | null,"tax_minor"?: number,"transfer_group_id"?: string | null,"unit_price_minor"?: number | null,"user_id": string
                  }
                  Update: {
                    "account_id"?: string,"batch_id"?: string | null,"cash_amount_minor"?: number | null,"correction_of"?: string | null,"created_at"?: string,"currency"?: string,"event_type"?: string,"fees_minor"?: number,"fx_rate_id"?: string | null,"id"?: string,"idempotency_key"?: string,"instrument_id"?: string | null,"occurred_on"?: string,"quantity"?: number | null,"settled_on"?: string | null,"source_ref"?: string | null,"source_type"?: string,"split_denominator"?: number | null,"split_numerator"?: number | null,"tax_minor"?: number,"transfer_group_id"?: string | null,"unit_price_minor"?: number | null,"user_id"?: string
                  }
                  Relationships: [
                    {
      foreignKeyName: "wealth_journal_events_account_id_fkey"
      columns: ["account_id"]
isOneToOne: false
      referencedRelation: "wealth_accounts"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "wealth_journal_events_batch_id_fkey"
      columns: ["batch_id"]
isOneToOne: false
      referencedRelation: "wealth_import_batches"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "wealth_journal_events_correction_of_fkey"
      columns: ["correction_of"]
isOneToOne: false
      referencedRelation: "wealth_journal_events"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "wealth_journal_events_fx_rate_id_fkey"
      columns: ["fx_rate_id"]
isOneToOne: false
      referencedRelation: "wealth_fx_rates"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "wealth_journal_events_instrument_id_fkey"
      columns: ["instrument_id"]
isOneToOne: false
      referencedRelation: "wealth_instruments"
      referencedColumns: ["id"]
    }
                  ]
                },"wealth_profiles": {
                  Row: {
                    "created_at": string,"reporting_currency": string,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "created_at"?: string,"reporting_currency"?: string,"user_id": string
                  }
                  Update: {
                    "created_at"?: string,"reporting_currency"?: string,"user_id"?: string
                  }
                  Relationships: [
                    
                  ]
                },"wealth_valuations": {
                  Row: {
                    "account_id": string,"amount_minor": number,"as_of": string,"created_at": string,"currency": string,"id": string,"import_batch_id": string | null,"instrument_id": string,"provenance": string,"quantity": number,"user_id": string
                  }
                  ComputedFields: never
                  Insert: {
                    "account_id": string,"amount_minor": number,"as_of": string,"created_at"?: string,"currency": string,"id"?: string,"import_batch_id"?: string | null,"instrument_id": string,"provenance": string,"quantity": number,"user_id": string
                  }
                  Update: {
                    "account_id"?: string,"amount_minor"?: number,"as_of"?: string,"created_at"?: string,"currency"?: string,"id"?: string,"import_batch_id"?: string | null,"instrument_id"?: string,"provenance"?: string,"quantity"?: number,"user_id"?: string
                  }
                  Relationships: [
                    {
      foreignKeyName: "wealth_valuations_account_id_fkey"
      columns: ["account_id"]
isOneToOne: false
      referencedRelation: "wealth_accounts"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "wealth_valuations_import_batch_id_fkey"
      columns: ["import_batch_id"]
isOneToOne: false
      referencedRelation: "wealth_import_batches"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "wealth_valuations_instrument_id_fkey"
      columns: ["instrument_id"]
isOneToOne: false
      referencedRelation: "wealth_instruments"
      referencedColumns: ["id"]
    }
                  ]
                }
          }
          Views: {
            [_ in never]: never
          }
          Functions: {
            [_ in never]: never
          }
          Enums: {
            [_ in never]: never
          }
          CompositeTypes: {
            [_ in never]: never
          }
        }
}

type DatabaseWithoutInternals = Omit<Database, '__InternalSupabase'>

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
    : never = never
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
  ? (DefaultSchema["Tables"] & DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
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
    : never = never
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
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
    : never = never
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
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
    : never = never
> = DefaultSchemaEnumNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
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
    : never = never
> = PublicCompositeTypeNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
  ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
  : never

export const Constants = {
  "public": {
          Enums: {
            
          }
        }
} as const
