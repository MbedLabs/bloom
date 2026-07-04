import { describe, expect, it } from 'vitest'

import {
  projectDeleteConfirmationMatches,
  projectDeleteConfirmationPhrase,
} from '../lib/projectDelete'

describe('projectDeleteConfirmationPhrase', () => {
  it('uses the project prefix, not a generic PRJ example', () => {
    expect(projectDeleteConfirmationPhrase('vcu')).toBe('Delete VCU')
    expect(projectDeleteConfirmationPhrase('FLT')).toBe('Delete FLT')
  })

  it('matches only the exact expected phrase', () => {
    const expected = projectDeleteConfirmationPhrase('VCU')
    expect(projectDeleteConfirmationMatches('Delete VCU', expected)).toBe(true)
    expect(projectDeleteConfirmationMatches('Delete PRJ', expected)).toBe(false)
    expect(projectDeleteConfirmationMatches(' Delete VCU ', expected)).toBe(true)
  })
})
