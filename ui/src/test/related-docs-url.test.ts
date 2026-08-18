import { describe, expect, it } from 'vitest'
import { relatedDocsUrl } from '../types/doc'

describe('relatedDocsUrl', () => {
  it('points at the documents registry for the project', () => {
    const url = relatedDocsUrl('FLT', 'FLT-REQ-001')

    expect(url.startsWith('/projects/FLT/docs?')).toBe(true)
  })

  it('carries the anchor document so the registry can filter by relationship', () => {
    const params = new URLSearchParams(relatedDocsUrl('FLT', 'FLT-REQ-001').split('?')[1])

    expect(params.get('related_to')).toBe('FLT-REQ-001')
    expect(params.get('role')).toBeNull()
    expect(params.get('direction')).toBeNull()
  })

  it('narrows to a single relationship role and direction when given', () => {
    const params = new URLSearchParams(
      relatedDocsUrl('FLT', 'FLT-REQ-001', { role: 'verifies', direction: 'incoming' }).split('?')[1],
    )

    expect(params.get('related_to')).toBe('FLT-REQ-001')
    expect(params.get('role')).toBe('verifies')
    expect(params.get('direction')).toBe('incoming')
  })

  it('encodes values so ids and roles survive the query string', () => {
    const url = relatedDocsUrl('FLT', 'FLT-REQ-001', { role: 'is verified by' })

    expect(url).toContain('role=is+verified+by')
  })
})
