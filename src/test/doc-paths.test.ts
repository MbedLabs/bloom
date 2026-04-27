import { describe, expect, it } from 'vitest'

import { docCreateUrl, normalizeDocTypeParam } from '../types/doc'

describe('docCreateUrl', () => {
  it('uses normalized kind slugs in create routes', () => {
    expect(docCreateUrl('VCU', 'SPEC')).toBe('/projects/VCU/docs/new?type=specifications')
    expect(docCreateUrl('VCU', 'TC')).toBe('/projects/VCU/docs/new?type=test-cases')
  })
})

describe('normalizeDocTypeParam', () => {
  it('accepts both canonical codes and normalized slugs', () => {
    expect(normalizeDocTypeParam('SPEC')).toBe('SPEC')
    expect(normalizeDocTypeParam('specifications')).toBe('SPEC')
    expect(normalizeDocTypeParam('test-cases')).toBe('TC')
  })

  it('returns null for unknown values', () => {
    expect(normalizeDocTypeParam('DOC')).toBeNull()
    expect(normalizeDocTypeParam('documents')).toBeNull()
  })
})
