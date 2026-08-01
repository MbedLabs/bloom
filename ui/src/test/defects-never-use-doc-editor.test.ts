import { describe, expect, it } from 'vitest'

import docCreateSource from '../pages/DocCreate.tsx?raw'
import artefactDetailSource from '../pages/ArtefactDetail.tsx?raw'
import { dedicatedListUrl, usesDocumentEditor } from '../pages/docCreateIdPolicy'
import type { DocType } from '../types/doc'

/**
 * Defects have a dedicated page. They carry a severity, a resolution summary,
 * an external tracker link and a sync log, none of which the generic rich-text
 * document editor can show or save.
 *
 * The registry lists defects like any other document, so `docs/defects/…/edit`
 * resolved to DocCreate and opened the editor anyway - the one route by which a
 * defect could still be edited as a rich document.
 */

const DEDICATED: DocType[] = ['DEF', 'CMP', 'TS']
const EDITOR_TYPES: DocType[] = ['REQ', 'TC', 'DES', 'RSK', 'CHG', 'CPT', 'SPEC', 'PRT', 'RPT', 'STD']

describe('document editor ownership', () => {
  it.each(DEDICATED)('%s is owned by its dedicated page, not the editor', (docType) => {
    expect(usesDocumentEditor(docType)).toBe(false)
  })

  it.each(EDITOR_TYPES)('%s is edited as a document', (docType) => {
    expect(usesDocumentEditor(docType)).toBe(true)
  })

  it('sends defects and campaigns to their own list route', () => {
    expect(dedicatedListUrl('VCU', 'DEF')).toBe('/projects/VCU/defects')
    expect(dedicatedListUrl('VCU', 'CMP')).toBe('/projects/VCU/campaigns')
  })

  it('leaves types without a bespoke list route to the registry', () => {
    expect(dedicatedListUrl('VCU', 'TS')).toBeNull()
    expect(dedicatedListUrl('VCU', 'REQ')).toBeNull()
  })
})

describe('DocCreate', () => {
  it('redirects every dedicated type away before rendering the editor', () => {
    expect(docCreateSource).toContain('usesDocumentEditor(docType)')
  })

  it('no longer creates or loads defects', () => {
    expect(docCreateSource).not.toContain('defectsApi')
    expect(docCreateSource).not.toContain("'defect_id'")
  })
})

describe('ArtefactDetail', () => {
  it('edits a defect in place instead of routing to the document editor', () => {
    expect(artefactDetailSource).toContain("kind === 'defect'")
    expect(artefactDetailSource).toContain('setIsEditing(true)')
  })
})
