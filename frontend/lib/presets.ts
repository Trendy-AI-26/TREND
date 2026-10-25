import type { PlatformPreset } from '@/types'

export type PresetShortLabelKey =
  | 'post'
  | 'story'
  | 'reel'
  | 'header'
  | 'cover'
  | 'banner'
  | 'thumb'

export interface PresetInfo {
  width: number
  height: number
  shortLabelKey: PresetShortLabelKey
}

export const PLATFORM_PRESETS: Record<PlatformPreset, PresetInfo> = {
  instagram_post: { width: 1080, height: 1080, shortLabelKey: 'post' },
  instagram_story: { width: 1080, height: 1920, shortLabelKey: 'story' },
  instagram_reel_cover: { width: 1080, height: 1920, shortLabelKey: 'reel' },
  facebook_post: { width: 1200, height: 630, shortLabelKey: 'post' },
  facebook_cover: { width: 820, height: 312, shortLabelKey: 'cover' },
  facebook_story: { width: 1080, height: 1920, shortLabelKey: 'story' },
  twitter_post: { width: 1200, height: 675, shortLabelKey: 'post' },
  twitter_header: { width: 1500, height: 500, shortLabelKey: 'header' },
  linkedin_post: { width: 1200, height: 627, shortLabelKey: 'post' },
  linkedin_banner: { width: 1584, height: 396, shortLabelKey: 'banner' },
  tiktok_video_cover: { width: 1080, height: 1920, shortLabelKey: 'cover' },
  youtube_thumbnail: { width: 1280, height: 720, shortLabelKey: 'thumb' },
  youtube_banner: { width: 2560, height: 1440, shortLabelKey: 'banner' },
}

export function gcd(a: number, b: number): number {
  return b === 0 ? a : gcd(b, a % b)
}

export function aspectRatioLabel(width: number, height: number): string {
  const g = gcd(width, height)
  return `${width / g}:${height / g}`
}

// Platform group names (Instagram, Facebook, Twitter/X, LinkedIn, TikTok, YouTube)
// are product/brand names and are intentionally kept untranslated, consistent
// with how other brand names (OpenAI, Gemini) are handled in messages/ar.json.
export const PRESETS_BY_PLATFORM: Record<string, PlatformPreset[]> = {
  Instagram: ['instagram_post', 'instagram_story', 'instagram_reel_cover'],
  Facebook: ['facebook_post', 'facebook_cover', 'facebook_story'],
  'Twitter/X': ['twitter_post', 'twitter_header'],
  LinkedIn: ['linkedin_post', 'linkedin_banner'],
  TikTok: ['tiktok_video_cover'],
  YouTube: ['youtube_thumbnail', 'youtube_banner'],
}
