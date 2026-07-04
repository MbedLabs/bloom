import { describe, expect, it } from 'vitest'

import { isServerAssignedDocIdOnCreate } from '../pages/docCreateIdPolicy'
import type { DocType } from '../types/doc'

const CREATABLE_DOC_TYPES: DocType[] = [
  'REQ',
  'SPEC',
  'TC',
  'DES',
  'RSK',
  'CHG',
  'CPT',
  'DEF',
  'PRT',
  'RPT',
  'STD',
]

describe('docCreateIdPolicy', () => {
  it('assigns public IDs on the server for every DocCreate kind', () => {
    for (const docType of CREATABLE_DOC_TYPES) {
      expect(isServerAssignedDocIdOnCreate(docType)).toBe(true)
    }
  })

  it('does not treat operational kinds as DocCreate server-assigned kinds', () => {
    expect(isServerAssignedDocIdOnCreate('CMP')).toBe(false)
    expect(isServerAssignedDocIdOnCreate('TS')).toBe(false)
  })
})
