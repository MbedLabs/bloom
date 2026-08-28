/**
 * A save has to clear the cache entry the page you land on actually reads.
 *
 * The registry lists are keyed by project, but each detail page reads its one
 * record under a singular key keyed by the record id. DocCreate's invalidation
 * listed only 'document', so saving a requirement, a test case or any artefact
 * returned you to a page still holding its cached copy: the edit appeared only
 * after a manual reload, and only the plain document kinds looked fine.
 *
 * This reads the sources rather than driving the UI because the failure is a
 * missing name in a list - a page adding a new key, or an artefact kind being
 * introduced, is exactly how it would come back.
 */
import { describe, expect, it } from 'vitest'

import docCreateSource from '../pages/DocCreate.tsx?raw'
import artefactDetailSource from '../pages/ArtefactDetail.tsx?raw'
import testCaseDetailSource from '../pages/TestCaseDetail.tsx?raw'
import requirementDetailSource from '../pages/RequirementDetail.tsx?raw'
import documentDetailSource from '../pages/DocumentDetail.tsx?raw'

/** The names DocCreate clears after a save. */
function invalidatedDetailKeys(): string[] {
  const block = /const DETAIL_QUERY_KEYS = \[([\s\S]*?)\] as const/.exec(docCreateSource)
  expect(block, 'DETAIL_QUERY_KEYS should still be declared in DocCreate').toBeTruthy()
  return Array.from(block![1].matchAll(/'([^']+)'/g)).map((match) => match[1])
}

/** The singular key a detail page reads its own record under. */
function detailKeyFrom(source: string): string[] {
  return Array.from(source.matchAll(/queryKey: \['([A-Za-z]+)', \w+\]/g)).map((m) => m[1])
}

describe('saving a document refreshes the page you go back to', () => {
  it('clears the key TestCaseDetail reads', () => {
    expect(detailKeyFrom(testCaseDetailSource)).toContain('testCase')
    expect(invalidatedDetailKeys()).toContain('testCase')
  })

  it('clears the key RequirementDetail reads', () => {
    expect(detailKeyFrom(requirementDetailSource)).toContain('requirement')
    expect(invalidatedDetailKeys()).toContain('requirement')
  })

  it('clears the key DocumentDetail reads', () => {
    expect(detailKeyFrom(documentDetailSource)).toContain('document')
    expect(invalidatedDetailKeys()).toContain('document')
  })

  it('clears every artefact kind ArtefactDetail can show', () => {
    // ArtefactDetail picks its key from a per-kind config, so a new kind added
    // there is the most likely way for this to drift back out of step.
    const kinds = Array.from(artefactDetailSource.matchAll(/queryKey: '([A-Za-z]+)'/g)).map((m) => m[1])
    expect(kinds.length).toBeGreaterThan(0)

    const cleared = invalidatedDetailKeys()
    for (const kind of kinds) {
      expect(cleared, `saving should clear the '${kind}' detail cache`).toContain(kind)
    }
  })

  it('still clears the record on the same id the detail pages use', () => {
    // The pages key on `resolvedId || parseInt(itemId)`, which is the same
    // numeric id DocCreate holds as resolvedDocId - so the loop must use it.
    expect(docCreateSource).toMatch(/for \(const key of DETAIL_QUERY_KEYS\)[\s\S]{0,120}\[key, resolvedDocId\]/)
  })
})
