import type { LogoMode, PlatformPreset } from '@/types'
import type { AudienceAgeRange, GenerationBrief, TextLanguage } from '@/types/generation'
import type {
  AudienceSegment,
  CallToAction,
  ClientType,
  DesignTextLanguage,
  Feeling,
  LocationScope,
  LogoPlacement,
  Occasion,
  Offering,
  VisualStyle,
  WizardAgeRange,
  WizardAnswers,
} from './wizard-types'

// شكل الطلب اللي بيستقبله الباك إند على /brands/{id}/generate
export interface WizardGenerateRequest {
  brief: GenerationBrief & { language: TextLanguage }
  platform_preset: PlatformPreset
  logo_mode: LogoMode
  logo_placement: LogoPlacement
  product_asset_id?: string | null
  product_edit_instruction?: string | null
}

// =====================================================================
// جداول التحويل: من خيارات الواجهة إلى القيم اللي بيفهمها الباك إند
// =====================================================================

const SEGMENT_TO_API: Record<Exclude<AudienceSegment, 'other'>, string> = {
  individuals: 'general_consumers',
  companies: 'custom',
  students: 'students',
  business_owners: 'small_business_owners',
}

const OFFERING_TO_CONTENT_TYPE: Record<Offering, GenerationBrief['content_type']> = {
  product: 'product_showcase',
  service: 'service_showcase',
  personal_project: 'brand_story',
  other: 'promotional_ad',
}

const FEELING_TO_TONE: Record<Feeling, GenerationBrief['voice_tone']> = {
  trust: 'trustworthy',
  excitement: 'bold',
  comfort: 'warm',
  curiosity: 'playful',
}

const AGE_TO_API: Record<WizardAgeRange, AudienceAgeRange | null> = {
  under_18: 'under_18',
  '18_24': '18_24',
  '25_34': '25_34',
  '35_44': '35_44',
  // The backend has no 45+ band; keep the full range in audience details.
  '45_plus': null,
}

const CTA_TEXT: Record<Exclude<CallToAction, 'none' | 'other'>, Record<TextLanguage, string>> = {
  shop_now: { ar: 'تسوّق الآن', en: 'Shop now' },
  order_now: { ar: 'اطلب الآن', en: 'Order now' },
  book_now: { ar: 'احجز موعدك', en: 'Book now' },
  contact_us: { ar: 'تواصل معنا', en: 'Contact us' },
  sign_up: { ar: 'سجّل الآن', en: 'Sign up' },
  learn_more: { ar: 'اعرف أكثر', en: 'Learn more' },
}

// هاي النصوص بتروح للذكاء الاصطناعي، فكتبناها بالإنجليزي
const LOCATION_TEXT: Record<Exclude<LocationScope, 'country'>, string> = {
  local: 'Local market',
  arab_world: 'Arab world',
  global: 'Global',
}

const OFFERING_TEXT: Record<Offering, string> = {
  personal_project: 'a personal project',
  product: 'a product',
  service: 'a service',
  other: 'other',
}

const CLIENT_TYPE_TEXT: Record<ClientType, string> = {
  b2c: 'individuals and consumers (B2C)',
  b2b: 'companies and organizations (B2B)',
  both: 'both individuals and companies',
}

const VISUAL_STYLE_TEXT: Record<VisualStyle, string> = {
  simple: 'simple and clean',
  modern: 'modern',
  luxury: 'luxurious and premium',
  bold: 'bold and eye-catching',
}

const FEELING_TEXT: Record<Feeling, string> = {
  trust: 'trust',
  excitement: 'excitement',
  comfort: 'comfort',
  curiosity: 'curiosity',
}

const LOGO_PLACEMENT_TEXT: Record<Exclude<LogoPlacement, 'none'>, string> = {
  prominent: 'clear and prominent',
  corner: 'small in a corner',
  watermark: 'as a subtle watermark',
  auto: 'wherever it fits the design best',
}

const OCCASION_TEXT: Record<Exclude<Occasion, 'none' | 'other'>, string> = {
  ramadan: 'Ramadan',
  eid: 'Eid',
  national_day: 'National Day',
  white_friday: 'White Friday',
  year_end: 'End of year',
  seasonal_launch: 'Seasonal launch',
}

// =====================================================================

function textLanguage(choice: DesignTextLanguage | '', locale: string): TextLanguage {
  if (choice === 'en') return 'en'
  if (choice === 'auto') return locale === 'en' ? 'en' : 'ar'
  return 'ar' // عربي، أو عربي وإنجليزي مع بعض
}

function logoMode(placement: LogoPlacement | '', brandHasLogo: boolean): LogoMode {
  if (!brandHasLogo || placement === 'none') return 'none'
  if (placement === 'watermark') return 'watermark'
  return 'prompt'
}

// نحذف الفراغات، والنص الفاضي بيصير null
function clean(value: string | null | undefined): string | null {
  const trimmed = value?.trim()
  return trimmed ? trimmed : null
}

interface BuildRequestOptions {
  answers: WizardAnswers
  brandHasLogo: boolean
  /** لغة الواجهة الحالية، نستخدمها لما يختار "خليها تلقائي" */
  locale: string
  productAssetId: string | null
}

export function buildGenerateRequest({
  answers,
  brandHasLogo,
  locale,
  productAssetId,
}: BuildRequestOptions): WizardGenerateRequest {
  const { idea, audience, style, platform } = answers
  const language = textLanguage(idea.textLanguage, locale)

  // ----- النص اللي بيظهر جوا الصورة + زر الـ CTA -----
  let ctaText: string | null = null
  if (idea.cta === 'other') ctaText = clean(idea.ctaCustom)
  else if (idea.cta && idea.cta !== 'none') ctaText = CTA_TEXT[idea.cta][language]

  const textToInclude = [clean(idea.textInImage), ctaText].filter(Boolean).join('\n')

  // ----- الجمهور -----
  const segments = Array.from(new Set(audience.segments.map((segment) =>
    segment === 'other' ? 'custom' : SEGMENT_TO_API[segment],
  )))

  const audienceDetails = [
    audience.segments.includes('companies') ? 'Audience segment: businesses and organizations' : null,
    audience.segments.includes('other') ? clean(audience.segmentOther) : null,
    audience.clientType ? `Client type: ${CLIENT_TYPE_TEXT[audience.clientType]}` : null,
    audience.ageRange === '45_plus' ? 'Age: 45 and above' : null,
  ].filter(Boolean)

  const location =
    audience.location === 'country'
      ? clean(audience.country)
      : audience.location
        ? LOCATION_TEXT[audience.location]
        : null

  // ----- الحقول الجديدة اللي ما إلها مكان بالباك إند لسا: بنحطها كملاحظات منظمة -----
  const notes = [
    idea.offering ? `Offering: ${OFFERING_TEXT[idea.offering]}` : null,
    style.visualStyle ? `Visual style: ${VISUAL_STYLE_TEXT[style.visualStyle]}` : null,
    style.feeling ? `The audience should feel: ${FEELING_TEXT[style.feeling]}` : null,
    brandHasLogo && style.logoPlacement && style.logoPlacement !== 'none'
      ? `Logo placement: ${LOGO_PLACEMENT_TEXT[style.logoPlacement]}`
      : null,
    idea.textLanguage === 'both' ? 'Text in the design: Arabic and English together' : null,
    style.occasion === 'other'
      ? `Occasion: ${clean(style.occasionCustom)}`
      : style.occasion && style.occasion !== 'none'
        ? `Occasion: ${OCCASION_TEXT[style.occasion]}`
        : null,
    clean(platform.notes)
      ? `Additional notes from the user: ${clean(platform.notes)}`
      : null,
  ].filter(Boolean)

  // ----- صورة المنتج -----
  let productEditInstruction: string | null = null
  if (productAssetId) {
    productEditInstruction =
      style.hasProductPhotos === 'yes_needs_edit'
        ? 'Retouch and enhance the product photo: clean the background and improve lighting and colors, while keeping the product shape, label and identity unchanged.'
        : 'Use the product photo as the hero of the design without changing the product itself.'
  }

  return {
    brief: {
      language,
      campaign_goal: idea.goal,
      campaign_goal_custom: idea.goal === 'custom' ? clean(idea.goalCustom) : null,
      content_type: idea.offering ? OFFERING_TO_CONTENT_TYPE[idea.offering] : '',
      content_type_custom: null,
      target_audience: {
        segments,
        location,
        age_range: audience.ageRange ? AGE_TO_API[audience.ageRange] : null,
        gender_focus: audience.gender || null,
        details: audienceDetails.length > 0 ? audienceDetails.join('. ') : null,
      },
      core_idea: idea.coreIdea.trim(),
      voice_tone: style.feeling ? FEELING_TO_TONE[style.feeling] : '',
      voice_tone_custom: null,
      optional_notes: notes.length > 0 ? notes.join('\n').slice(0, 2000) : null,
      text_to_include: textToInclude || null,
    },
    platform_preset: platform.preset || 'instagram_post',
    logo_mode: logoMode(style.logoPlacement, brandHasLogo),
    logo_placement: brandHasLogo ? style.logoPlacement || 'none' : 'none',
    product_asset_id: productAssetId,
    product_edit_instruction: productEditInstruction,
  }
}
