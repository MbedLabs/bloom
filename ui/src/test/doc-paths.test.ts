import { describe, expect, it } from 'vitest'

import { docCreateUrl, docListUrl, getAllowedDocLinkRoles, getDocLinkOptions, getDocLinkRoleLabel, normalizeDocTypeParam } from '../types/doc'

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
    expect(normalizeDocTypeParam('TCO')).toBe('CPT')
    expect(normalizeDocTypeParam('PROT')).toBe('PRT')
  })

  it('returns null for unknown values', () => {
    expect(normalizeDocTypeParam('DOC')).toBeNull()
    expect(normalizeDocTypeParam('documents')).toBeNull()
  })
})

describe('getDocLinkOptions', () => {
  it('projects reverse semantics when the current document is the target side', () => {
    expect(getDocLinkOptions('REQ', 'TC')).toEqual([
      {
        key: 'TC:verifies:REQ:incoming',
        label: 'verified by',
        role: 'verifies',
        sourceType: 'TC',
        targetType: 'REQ',
        displayDirection: 'incoming',
      },
    ])
  })

  it('keeps forward semantics when the current document is the source side', () => {
    expect(getDocLinkOptions('CPT', 'TC')).toEqual([
      {
        key: 'CPT:implements:TC:outgoing',
        label: 'implements',
        role: 'implements',
        sourceType: 'CPT',
        targetType: 'TC',
        displayDirection: 'outgoing',
      },
    ])
  })

  it('returns no options for pairs that are not allowed in either direction', () => {
    expect(getDocLinkOptions('TC', 'DES')).toEqual([])
  })
})

describe('getAllowedDocLinkRoles', () => {
  it('summarizes the pair-aware relationship table as a deduplicated role list', () => {
    expect(getAllowedDocLinkRoles('REQ', 'TC')).toEqual(['verifies'])
    expect(getAllowedDocLinkRoles('REQ', 'DES')).toEqual(['satisfies', 'implements', 'references'])
    expect(getAllowedDocLinkRoles('REQ', 'SPEC')).toEqual(['derives_from', 'refines', 'references'])
    expect(getAllowedDocLinkRoles('TC', 'DES')).toEqual([])
    expect(getAllowedDocLinkRoles('CPT', 'SPEC')).toEqual(['covers', 'verifies', 'references'])
    expect(getAllowedDocLinkRoles('CMP', 'REQ')).toEqual(['covers', 'references'])
    expect(getAllowedDocLinkRoles('TS', 'REQ')).toEqual(['covers', 'references'])
  })

  it('returns no roles for unknown document kinds', () => {
    expect(getAllowedDocLinkRoles('REQ', 'UNKNOWN' as never)).toEqual([])
  })
})

describe('docListUrl', () => {
  it('builds typed list URLs with slugs', () => {
    expect(docListUrl('VCU', 'REQ')).toBe('/projects/VCU/docs?type=requirements')
    expect(docListUrl('VCU', 'CMP')).toBe('/projects/VCU/docs?type=campaigns')
    expect(docListUrl('VCU', 'TS')).toBe('/projects/VCU/docs?type=test-suites')
  })

  it('appends extra search params', () => {
    expect(docListUrl('VCU', 'REQ', 'sort=doc_id&dir=asc')).toBe('/projects/VCU/docs?type=requirements&sort=doc_id&dir=asc')
  })
})

describe('getDocLinkRoleLabel', () => {
  it('provides directional human labels', () => {
    expect(getDocLinkRoleLabel('derives_from', 'outgoing')).toBe('derives from')
    expect(getDocLinkRoleLabel('derives_from', 'incoming')).toBe('derived by')
    expect(getDocLinkRoleLabel('references', 'incoming')).toBe('referenced by')
    expect(getDocLinkRoleLabel('covers', 'incoming')).toBe('covered by')
    expect(getDocLinkRoleLabel('contains', 'incoming')).toBe('contained by')
  })
})
