export interface Page<T> { items: T[]; page: number; per_page: number; total: number }
export interface GenerationRow {
  id: string; status: 'pending' | 'processing' | 'succeeded' | 'failed'; provider: string; model: string; platform_preset: string
  error_code: string | null; error_message: string | null; created_at: string; completed_at: string | null; image_url: string | null; needs_review: boolean
  brand: { id: string; name: string }; user: { id: string; email: string }
}
export interface AdminUser {
  id: string; email: string; full_name: string | null; email_verified: boolean; disabled: boolean; is_admin: boolean; created_at: string; trial_ends_at: string | null
  brands_count: number; generations_count: number; generations_succeeded: number
  quota: { limit: number; consumed: number; reserved: number; remaining: number } | null
  credits: { balance: number; reserved: number; available: number } | null
  today: { limit: number; consumed: number; reserved: number } | null
}
export interface UserDetail extends AdminUser {
  brands: { id: string; name: string; kit_status: string; generation_count: number; created_at: string }[]
  recent_generations: GenerationRow[]
  credit_ledger: { id: string; operation: string; amount: number; metadata: object; created_at: string }[]
}
export interface AdminBrand { id: string; name: string; owner: { id: string; email: string; full_name: string | null }; kit_status: string; colors_count: number; has_logo: boolean; generation_count: number; created_at: string }
export const tagFields = ['industry', 'region', 'platform', 'audience', 'visual_style', 'content_patterns', 'keywords', 'avoid_patterns'] as const
export type TagField = typeof tagFields[number]
export type Trend = Record<TagField, string[]> & {
  id: string; name: string; slug: string; description: string; category: string; popularity_score: number; growth_score: number; relevance_score: number
  status: 'active' | 'inactive' | 'expired'; source: string; observed_at: string | null; expires_at: string | null; created_at: string; updated_at: string
}
export interface AuditRow { id: string; admin_email: string; action: string; target_type: string; target_id: string; details: object; created_at: string }
export interface Overview {
  users: { total: number; verified: number; new_7d: number; disabled: number }; brands: { total: number; kits_complete: number }
  generations: { total: number; today: number; last_7d: number; last_30d: number; succeeded: number; failed: number; pending: number; processing: number; success_rate_30d: number | null }
  cost: { credits_charged_30d: number; estimated_provider_cost_30d: number | null }
  daily: { date: string; succeeded: number; failed: number }[]
  attention: { needs_review: GenerationRow[]; recent_failures: GenerationRow[] }
}
