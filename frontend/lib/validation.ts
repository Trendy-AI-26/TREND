import type { GenerationBrief } from '@/types/generation'

export type BriefFieldErrors = Partial<{
    campaign_goal: string
    campaign_goal_custom: string
    content_type: string
    content_type_custom: string
    audience_segments: string
    core_idea: string
    voice_tone: string
    voice_tone_custom: string
    optional_notes: string
    text_to_include: string
}>

export function validateGenerationBrief(
    brief: GenerationBrief,
): BriefFieldErrors {
    const errors: BriefFieldErrors = {}
    const audience = brief.target_audience

    if (!brief.campaign_goal) {
        errors.campaign_goal = 'Please choose a campaign goal.'
    }

    if (
        brief.campaign_goal === 'custom' &&
        !brief.campaign_goal_custom?.trim()
    ) {
        errors.campaign_goal_custom = 'Please describe your campaign goal.'
    }

    if (!brief.content_type) {
        errors.content_type = 'Please choose a content type.'
    }

    if (
        brief.content_type === 'custom' &&
        !brief.content_type_custom?.trim()
    ) {
        errors.content_type_custom = 'Please describe your content type.'
    }

    if (audience.segments.length === 0) {
        errors.audience_segments = 'Please choose at least one audience group.'
       } else if (audience.segments.length > 3) {
        errors.audience_segments = 'You can select up to three audience groups.'
    }

    const ideaLength = brief.core_idea.trim().length

    if (ideaLength === 0) {
        errors.core_idea = 'Please describe the main idea.'
    } else if (ideaLength < 3) {
        errors.core_idea = 'The main idea must be at least 3 characters.'
    } else if (ideaLength > 1000) {
        errors.core_idea = 'The main idea cannot exceed 1000 characters.'
    }

    if (!brief.voice_tone) {
        errors.voice_tone = 'Please choose a voice and tone.'
    }

    if (brief.voice_tone === 'custom' && !brief.voice_tone_custom?.trim()) {
        errors.voice_tone_custom = 'Please describe your custom tone.'
    }

    const notesLength = (brief.optional_notes ?? '').length
    if (notesLength > 2000) {
        errors.optional_notes = 'Additional notes cannot exceed 2000 characters.'
    }

    const textLength = (brief.text_to_include ?? '').length
    if (textLength > 500) {
        errors.text_to_include = 'Text to include cannot exceed 500 characters.'
    }

    return errors
}

export function isGenerationBriefValid(brief: GenerationBrief): boolean {
    return Object.keys(validateGenerationBrief(brief)).length === 0
}
