import { describe, expect, it } from 'vitest'
import { searchResultUrl } from '../lib/searchLinks'
import type { SearchResultItem } from '../api/client'

function item(overrides: Partial<SearchResultItem>): SearchResultItem {
  return {
    type: 'REQ',
    id: 7,
    doc_id: 'PRJ-REQ-001',
    title: 'Login',
    status: 'Draft',
    project_id: 1,
    project_prefix: 'PRJ',
    project_name: 'Alpha',
    ...overrides,
  }
}

describe('searchResultUrl', () => {
  it('routes doc-registry types to the unified doc detail page', () => {
    expect(searchResultUrl(item({ type: 'REQ', doc_id: 'PRJ-REQ-001' }))).toBe(
      '/projects/PRJ/docs/requirements/PRJ-REQ-001'
    )
    expect(searchResultUrl(item({ type: 'TC', doc_id: 'PRJ-TC-002' }))).toBe(
      '/projects/PRJ/docs/test-cases/PRJ-TC-002'
    )
    expect(searchResultUrl(item({ type: 'SPEC', doc_id: 'PRJ-SPEC-001' }))).toBe(
      '/projects/PRJ/docs/specifications/PRJ-SPEC-001'
    )
  })

  it('routes defects, suites and campaigns to their document pages by document ID', () => {
    expect(searchResultUrl(item({ type: 'DEF', id: 42, doc_id: 'PRJ-DEF-001' }))).toBe('/projects/PRJ/docs/defects/PRJ-DEF-001')
    expect(searchResultUrl(item({ type: 'TS', id: 9, doc_id: 'PRJ-TS-002' }))).toBe('/projects/PRJ/docs/test-suites/PRJ-TS-002')
    expect(searchResultUrl(item({ type: 'CMP', id: 3, doc_id: 'PRJ-CMP-003' }))).toBe('/projects/PRJ/docs/campaigns/PRJ-CMP-003')
  })

  it('falls back to the project page for unknown types or missing doc ids', () => {
    expect(searchResultUrl(item({ type: 'UNKNOWN' }))).toBe('/projects/PRJ')
    expect(searchResultUrl(item({ type: 'REQ', doc_id: null }))).toBe('/projects/PRJ')
  })
})
