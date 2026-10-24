import { describe, expect, it } from 'vitest'
import { buildGenerateRequest } from './build-request'
import {
  EMPTY_WIZARD_ANSWERS,
  validateAudienceStep,
  type AudienceSegment,
  type WizardAgeRange,
  type WizardAnswers,
} from './wizard-types'

function audienceRequest(audience: Partial<WizardAnswers['audience']>) {
  return buildGenerateRequest({
    answers: {
      ...EMPTY_WIZARD_ANSWERS,
      audience: { ...EMPTY_WIZARD_ANSWERS.audience, ...audience },
    },
    brandHasLogo: false,
    locale: 'en',
    productAssetId: null,
  }).brief.target_audience
}

describe('wizard audience request mapping', () => {
  it('accepts only a required segment and omits optional audience fields', () => {
    const answers = { ...EMPTY_WIZARD_ANSWERS.audience, segments: ['individuals'] as AudienceSegment[] }
    expect(validateAudienceStep(EMPTY_WIZARD_ANSWERS.audience)).toEqual({
      segments: 'error_segments_required',
    })
    expect(validateAudienceStep(answers)).toEqual({})
    expect(audienceRequest(answers)).toEqual({
      segments: ['general_consumers'],
      location: null,
      age_range: null,
      gender_focus: null,
      details: null,
    })
  })

  it('requires country only when Specific country is selected', () => {
    const answers = { ...EMPTY_WIZARD_ANSWERS.audience, segments: ['individuals'] as AudienceSegment[] }
    expect(validateAudienceStep({ ...answers, location: 'country' })).toEqual({
      country: 'error_country_required',
    })
    expect(validateAudienceStep({ ...answers, location: 'global' })).toEqual({})
    expect(validateAudienceStep({ ...answers, location: 'country', country: 'Jordan' })).toEqual({})
  })

  it.each([
    ['individuals', 'general_consumers'],
    ['companies', 'custom'],
    ['students', 'students'],
    ['business_owners', 'small_business_owners'],
    ['other', 'custom'],
  ] as const)('maps %s to %s', (choice, expected) => {
    const audience = audienceRequest({
      segments: [choice as AudienceSegment],
      segmentOther: choice === 'other' ? 'Healthcare teams' : '',
    })

    expect(audience.segments).toEqual([expected])
    if (choice === 'companies') {
      expect(audience.details).toContain('businesses and organizations')
    }
    if (choice === 'other') {
      expect(audience.details).toContain('Healthcare teams')
    }
  })

  it('keeps companies and other distinct in details without duplicating custom', () => {
    const audience = audienceRequest({
      segments: ['companies', 'other', 'students'],
      segmentOther: 'Healthcare teams',
    })

    expect(audience.segments).toEqual(['custom', 'students'])
    expect(audience.details).toContain('businesses and organizations')
    expect(audience.details).toContain('Healthcare teams')
  })

  it.each([
    ['under_18', 'under_18'],
    ['18_24', '18_24'],
    ['25_34', '25_34'],
    ['35_44', '35_44'],
    ['45_plus', null],
  ] as const)('maps age %s without narrowing its meaning', (choice, expected) => {
    const audience = audienceRequest({
      segments: ['individuals'],
      ageRange: choice as WizardAgeRange,
    })

    expect(audience.age_range).toBe(expected)
    if (choice === '45_plus') {
      expect(audience.details).toContain('Age: 45 and above')
      expect(audience.details).not.toContain('45-54')
    }
  })

  it('retains the other audience fields', () => {
    const audience = audienceRequest({
      segments: ['business_owners'],
      clientType: 'b2b',
      ageRange: '25_34',
      gender: 'all',
      location: 'country',
      country: 'Jordan',
    })

    expect(audience).toEqual({
      segments: ['small_business_owners'],
      location: 'Jordan',
      age_range: '25_34',
      gender_focus: 'all',
      details: 'Client type: companies and organizations (B2B)',
    })
  })
})
