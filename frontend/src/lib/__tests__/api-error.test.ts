import { describe, expect, it } from 'vitest'
import { apiErrorMessage } from '@/lib/api-error'

describe('apiErrorMessage', () => {
  it('uses a string detail as is', () => {
    expect(apiErrorMessage({ detail: 'Application not found' }, 'x')).toBe(
      'Application not found',
    )
  })

  it('joins validation messages', () => {
    expect(
      apiErrorMessage(
        { detail: [{ msg: 'Field required' }, { msg: 'Not a UUID' }] },
        'x',
      ),
    ).toBe('Field required Not a UUID')
  })

  it.each([undefined, null, {}, { detail: '' }, { detail: [] }, 'oops'])(
    'falls back for %j',
    (error) => {
      expect(apiErrorMessage(error, 'Fallback')).toBe('Fallback')
    },
  )
})
