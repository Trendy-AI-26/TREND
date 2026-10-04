export type CampaignGoal =
    | 'brand_awareness'
    | 'product_launch'
    | 'product_showcase'
    | 'promotion_offer'
    | 'sales_conversion'
    | 'lead_generation'
    | 'engagement'
    | 'education'
    | 'announcement'
    | 'event_registration'
    | 'seasonal_campaign'
    | 'social_proof'
    | 'custom'

export type ContentType =
    | 'product_showcase'
    | 'service_showcase'
    | 'promotional_ad'
    | 'announcement'
    | 'educational'
    | 'testimonial'
    | 'brand_story'
    | 'event_promo'
    | 'seasonal_post'
    | 'quote_or_tip'
    | 'infographic'
    | 'social_proof'
    | 'custom'

export type VoiceTone =
    | 'friendly'
    | 'professional'
    | 'playful'
    | 'bold'
    | 'elegant'
    | 'warm'
    | 'educational'
    | 'inspirational'
    | 'minimal'
    | 'trustworthy'
    | 'youthful'
    | 'urgent'
    | 'custom'

export type TextLanguage = 'en' | 'ar'

export type AudienceAgeRange =
    | 'under_18'
    | '18_24'
    | '25_34'
    | '35_44'
    | '45_54'

export interface TargetAudienceBrief {
    /** One or two audience segments selected by the user. */
    segments: string[]
    /** Optional location, such as "Amman, Jordan". */
    location?: string | null
    /** Optional API age value, such as "25_34"; labels are translated separately. */
    age_range?: AudienceAgeRange | null
    /** Optional gender focus, such as "all" or "women". */
    gender_focus?: string | null
    /** Optional context about the audience's needs or motivations. */
    details?: string | null
}

export interface GenerationBrief {
    /** Required campaign goal. Empty string is used while the form is incomplete. */
    campaign_goal: CampaignGoal | ''
    /** Required only when campaign_goal is "custom". */
    campaign_goal_custom?: string | null

    /** Required content type. */
    content_type: ContentType | ''
    /** Required only when content_type is "custom". */
    content_type_custom?: string | null

    /** Structured audience information. */
    target_audience: TargetAudienceBrief

    /** Main idea supplied by the user, without building a prompt in the Frontend. */
    core_idea: string

    /** Required voice and tone selection. */
    voice_tone: VoiceTone | ''
    /** Required only when voice_tone is "custom". */
    voice_tone_custom?: string | null

    /** Optional visual direction or constraints. */
    optional_notes?: string | null
    /** Optional exact text to render inside the image. */
    text_to_include?: string | null
}

export interface CreativeDirection {
    campaign_goal: string
    content_type: string
    target_audience: string
    core_idea: string
    voice_tone: string
    platform: {
        name: string
        note: string
    }
    text_to_include?: string
    optional_notes?: string
    brand_identity?: {
        tagline?: string
        tone?: string
        colors?: string[]
        avoid_words?: string
    }
}

export interface PreviewBriefResponse {
    creative_direction: CreativeDirection
    brand_name: string
}
