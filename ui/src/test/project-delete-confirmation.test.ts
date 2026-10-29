import { describe, expect, it } from 'vitest'

import {
  projectDeleteConfirmationMatches,
  projectDeleteConfirmationPhrase,
} from '../lib/projectDelete'

describe('projectDeleteConfirmationPhrase', () => {
  it('uses the project prefix, not a generic PRJ example', () => {
    expect(projectDeleteConfirmationPhrase('abc')).toBe('Delete ABC')
    expect(projectDeleteConfirmationPhrase('XYZ')).toBe('Delete XYZ')
  })

  it('matches only the exact expected phrase', () => {
    const expected = projectDeleteConfirmationPhrase('ABC')
    expect(projectDeleteConfirmationMatches('Delete ABC', expected)).toBe(true)
    expect(projectDeleteConfirmationMatches('Delete PRJ', expected)).toBe(false)
    expect(projectDeleteConfirmationMatches(' Delete ABC ', expected)).toBe(true)
  })
})
