import { describe, expect, it } from 'vitest'

import documentDetailSource from '../pages/DocumentDetail.tsx?raw'
import requirementDetailSource from '../pages/RequirementDetail.tsx?raw'
import testCaseDetailSource from '../pages/TestCaseDetail.tsx?raw'

/**
 * Editing a document must open the full document editor.
 *
 * RequirementDetail used to flip a local `isEditing` flag and render a small
 * inline form (title, description, status, priority) instead of navigating to
 * the editor, so a requirement could never be edited as a document - regardless
 * of whether it predated rich content. The other detail pages already navigated
 * to `docEditUrl`, which left requirements the odd one out.
 */

const DETAIL_PAGES: [string, string][] = [
  ['RequirementDetail', requirementDetailSource],
  ['TestCaseDetail', testCaseDetailSource],
  ['DocumentDetail', documentDetailSource],
]

describe.each(DETAIL_PAGES)('%s', (_name, source) => {
  it('routes editing to the full document editor', () => {
    expect(source).toContain('docEditUrl')
  })

  it('does not fall back to an inline edit form', () => {
    expect(source).not.toContain('setIsEditing(true)')
  })
})

describe('detail pages render the stored body', () => {
  it.each([
    ['RequirementDetail', requirementDetailSource],
    ['TestCaseDetail', testCaseDetailSource],
  ])('%s shows rich content read-only', (_name, source) => {
    expect(source).toContain('content_json')
    expect(source).toContain('DocEditor')
    expect(source).toContain('editable={false}')
  })

  it.each([
    ['RequirementDetail', requirementDetailSource],
    ['TestCaseDetail', testCaseDetailSource],
  ])('%s falls back to the description for pre-rich-content documents', (_name, source) => {
    expect(source).toContain('SectionCard title="Description"')
  })
})

describe('RequirementDetail content', () => {
  it('still shows the description when a document predates rich content', () => {
    // Legacy requirements carry only `description`; they must not render blank.
    expect(requirementDetailSource).toContain('No description provided.')
  })
})
