import { describe, expect, it } from 'vitest'
import { searchResultUrl } from '../lib/searchLinks'
import type { SearchResultItem } from '../api/client'

function item(overrides: Partial<SearchResultItem>): SearchResultItem {
  return {
    type: 'REQ',
    id: 7,
    doc_id: 'ALP-REQ-001',
    title: 'Login',
    status: 'Draft',
    project_id: 1,
    project_prefix: 'ALP',
    project_name: 'Alpha',
    ...overrides,
  }
}

describe('searchResultUrl', () => {
  it('routes doc-registry types to the unified doc detail page', () => {
    expect(searchResultUrl(item({ type: 'REQ', doc_id: 'ALP-REQ-001' }))).toBe(
      '/projects/ALP/docs/requirements/ALP-REQ-001'
    )
    expect(searchResultUrl(item({ type: 'TC', doc_id: 'ALP-TC-002' }))).toBe(
      '/projects/ALP/docs/test-cases/ALP-TC-002'
    )
    expect(searchResultUrl(item({ type: 'SPEC', doc_id: 'ALP-SPEC-001' }))).toBe(
      '/projects/ALP/docs/specifications/ALP-SPEC-001'
    )
  })

  it('routes defects, suites and campaigns to their dedicated pages by numeric id', () => {
    expect(searchResultUrl(item({ type: 'DEF', id: 42 }))).toBe('/projects/ALP/defects/42')
    expect(searchResultUrl(item({ type: 'TS', id: 9 }))).toBe('/projects/ALP/suites/9')
    expect(searchResultUrl(item({ type: 'CMP', id: 3 }))).toBe('/projects/ALP/campaigns/3')
  })

  it('falls back to the project page for unknown types or missing doc ids', () => {
    expect(searchResultUrl(item({ type: 'UNKNOWN' }))).toBe('/projects/ALP')
    expect(searchResultUrl(item({ type: 'REQ', doc_id: null }))).toBe('/projects/ALP')
  })
})
