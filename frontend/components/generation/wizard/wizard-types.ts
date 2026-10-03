import type { CampaignGoal, PlatformPreset } from '@/types'

// ===== خيارات الخطوة الأولى: فكرة المنشور =====

export type Offering = 'personal_project' | 'product' | 'service' | 'other'

// نستخدم نفس قيم الباك إند الموجودة حتى يسهل الربط لاحقاً
export type WizardGoal = Extract<
  CampaignGoal,
  'engagement' | 'brand_awareness' | 'product_launch' | 'sales_conversion' | 'custom'
>

export type CallToAction =
  | 'shop_now'
  | 'order_now'
  | 'book_now'
  | 'contact_us'
  | 'sign_up'
  | 'learn_more'
  | 'none'
  | 'other'

export type DesignTextLanguage = 'ar' | 'en' | 'both' | 'auto'

export interface IdeaStepAnswers {
  coreIdea: string
  offering: Offering | ''
  goal: WizardGoal | ''
  goalCustom: string
  textInImage: string
  cta: CallToAction | ''
  ctaCustom: string
  textLanguage: DesignTextLanguage | ''
}

// ===== خيارات الخطوة الثانية: الجمهور =====

export type AudienceSegment = 'individuals' | 'companies' | 'students' | 'business_owners' | 'other'

export type ClientType = 'b2c' | 'b2b' | 'both'

export type WizardAgeRange = 'under_18' | '18_24' | '25_34' | '35_44' | '45_plus'

export type GenderFocus = 'men' | 'women' | 'all'

export type LocationScope = 'local' | 'country' | 'arab_world' | 'global'

export interface AudienceStepAnswers {
  segments: AudienceSegment[]
  segmentOther: string
  clientType: ClientType | ''
  ageRange: WizardAgeRange | ''
  gender: GenderFocus | ''
  location: LocationScope | ''
  country: string
}

// ===== كل إجابات النموذج =====
// سنضيف باقي الخطوات هنا بالمراحل القادمة.
export interface WizardAnswers {
  idea: IdeaStepAnswers
  audience: AudienceStepAnswers
  style: StyleStepAnswers
  platform: PlatformStepAnswers
}

export const EMPTY_WIZARD_ANSWERS: WizardAnswers = {
  idea: {
    coreIdea: '',
    offering: '',
    goal: '',
    goalCustom: '',
    textInImage: '',
    cta: '',
    ctaCustom: '',
    textLanguage: '',
  },
  audience: {
    segments: [],
    segmentOther: '',
    clientType: '',
    ageRange: '',
    gender: '',
    location: '',
    country: '',
  },
  style: {
    visualStyle: '',
    feeling: '',
    logoPlacement: '',
    hasProductPhotos: '',
    productImage: null,
    occasion: '',
    occasionCustom: '',
  },
  platform: {
    preset: 'instagram_post',
    withCaption: true,
    hasNotes: 'no',
    notes: '',
  },
}

export const LIMITS = {
  coreIdea: 300,
  textInImage: 60,
  custom: 120,
  // الباك إند يقبل 3 شرائح كحد أقصى
  segments: 3,
  country: 60,
}

// الأخطاء نخزنها كمفاتيح ترجمة، والواجهة تترجمها
export type StepErrors<T> = Partial<Record<keyof T, string>>
export type IdeaErrors = StepErrors<IdeaStepAnswers>
export type AudienceErrors = StepErrors<AudienceStepAnswers>

export function validateIdeaStep(answers: IdeaStepAnswers): IdeaErrors {
  const errors: IdeaErrors = {}
  const ideaLength = answers.coreIdea.trim().length

  if (ideaLength === 0) errors.coreIdea = 'error_core_idea_required'
  else if (ideaLength < 3) errors.coreIdea = 'error_core_idea_short'

  if (!answers.offering) errors.offering = 'error_required_choice'

  if (!answers.goal) errors.goal = 'error_required_choice'
  else if (answers.goal === 'custom' && !answers.goalCustom.trim()) {
    errors.goalCustom = 'error_custom_required'
  }

  if (!answers.cta) errors.cta = 'error_required_choice'
  else if (answers.cta === 'other' && !answers.ctaCustom.trim()) {
    errors.ctaCustom = 'error_custom_required'
  }

  if (!answers.textLanguage) errors.textLanguage = 'error_required_choice'

  return errors
}

export function validateAudienceStep(answers: AudienceStepAnswers): AudienceErrors {
  const errors: AudienceErrors = {}

  if (answers.segments.length === 0) errors.segments = 'error_segments_required'
  else if (answers.segments.includes('other') && !answers.segmentOther.trim()) {
    errors.segmentOther = 'error_custom_required'
  }

  if (!answers.clientType) errors.clientType = 'error_required_choice'
  if (!answers.ageRange) errors.ageRange = 'error_required_choice'
  if (!answers.gender) errors.gender = 'error_required_choice'

  if (!answers.location) errors.location = 'error_required_choice'
  else if (answers.location === 'country' && !answers.country.trim()) {
    errors.country = 'error_country_required'
  }

  return errors
} 
// ===== خيارات الخطوة الثالثة: الأسلوب والهوية =====

export type VisualStyle = 'simple' | 'modern' | 'luxury' | 'bold'

export type Feeling = 'trust' | 'excitement' | 'comfort' | 'curiosity'

export type LogoPlacement = 'prominent' | 'corner' | 'watermark' | 'auto' | 'none'

export type ProductPhotos = 'yes' | 'yes_needs_edit' | 'no'

export type Occasion =
  | 'none'
  | 'ramadan'
  | 'eid'
  | 'national_day'
  | 'white_friday'
  | 'year_end'
  | 'seasonal_launch'
  | 'other'

export interface StyleStepAnswers {
  visualStyle: VisualStyle | ''
  feeling: Feeling | ''
  logoPlacement: LogoPlacement | ''
  hasProductPhotos: ProductPhotos | ''
  /** الملف محفوظ بالمتصفح فقط، رح نرفعه لما نربط التوليد */
  productImage: File | null
  occasion: Occasion | ''
  occasionCustom: string
}

export type StyleErrors = StepErrors<StyleStepAnswers>

export const PRODUCT_IMAGE_MAX_MB = 10

export function validateStyleStep(answers: StyleStepAnswers, brandHasLogo: boolean): StyleErrors {
  const errors: StyleErrors = {}

  if (!answers.visualStyle) errors.visualStyle = 'error_required_choice'
  if (!answers.feeling) errors.feeling = 'error_required_choice'

  // سؤال الشعار إجباري بس إذا البراند عنده شعار
  if (brandHasLogo && !answers.logoPlacement) errors.logoPlacement = 'error_required_choice'

  if (!answers.hasProductPhotos) errors.hasProductPhotos = 'error_required_choice'

  // المناسبة اختيارية، بس إذا اختار "مناسبة أخرى" لازم يكتبها
  if (answers.occasion === 'other' && !answers.occasionCustom.trim()) {
    errors.occasionCustom = 'error_custom_required'
  }

  return errors
} 
// ===== خيارات الخطوة الرابعة: المنصة والنتيجة =====

export type YesNo = 'yes' | 'no'

export interface PlatformStepAnswers {
  preset: PlatformPreset | ''
  withCaption: boolean
  hasNotes: YesNo
  notes: string
}

export type PlatformErrors = StepErrors<PlatformStepAnswers>

export const PLATFORM_NOTES_MAX = 400

export function validatePlatformStep(answers: PlatformStepAnswers): PlatformErrors {
  const errors: PlatformErrors = {}

  if (!answers.preset) errors.preset = 'error_required_choice'

  // إذا قال "نعم" عندي ملاحظات، لازم يكتبها
  if (answers.hasNotes === 'yes' && !answers.notes.trim()) {
    errors.notes = 'error_notes_required'
  }

  return errors
}