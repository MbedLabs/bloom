import { describe, expect, it, vi } from 'vitest'

import type { DocShell, PaginatedResponse } from '../api/client'
import { fetchAllTopologyDocs } from '../lib/projectTopology'

function makeDoc(id: number, docType: string): DocShell {
  return {
    id,
    doc_id: `${docType}-${id}`,
    doc_type: docType,
    title: `${docType} ${id}`,
    status: 'draft',
    visibility: 'internal',
    priority: null,
    req_type: null,
    req_origin: null,
    project_id: 1,
    reviewer_id: null,
    incoming_links: 0,
    outgoing_links: 0,
    suspect_links: 0,
    last_execution_status: null,
    last_executed_at: null,
    created_at: '2026-05-27T00:00:00Z',
    updated_at: '2026-05-27T00:00:00Z',
  }
}

describe('fetchAllTopologyDocs', () => {
  it('loads every page so topology is not capped at the first 200 docs', async () => {
    const firstPage: PaginatedResponse<DocShell> = {
      items: Array.from({ length: 500 }, (_, idx) => makeDoc(idx + 1, 'TC')),
      total: 620,
      skip: 0,
      limit: 500,
    }
    const secondPage: PaginatedResponse<DocShell> = {
      items: [
        ...Array.from({ length: 100 }, (_, idx) => makeDoc(idx + 501, 'TC')),
        ...Array.from({ length: 20 }, (_, idx) => makeDoc(idx + 1, 'REQ')),
      ],
      total: 620,
      skip: 500,
      limit: 500,
    }

    const listDocs = vi
      .fn<(
        projectRef: string,
        params?: { includeLinkCounts?: boolean; skip?: number; limit?: number }
      ) => Promise<PaginatedResponse<DocShell>>>()
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce(secondPage)

    const docs = await fetchAllTopologyDocs('FLT', listDocs)

    expect(listDocs).toHaveBeenCalledTimes(2)
    expect(listDocs).toHaveBeenNthCalledWith(
      1,
      'FLT',
      expect.objectContaining({ includeLinkCounts: true, skip: 0, limit: 500 }),
    )
    expect(listDocs).toHaveBeenNthCalledWith(
      2,
      'FLT',
      expect.objectContaining({ includeLinkCounts: true, skip: 500, limit: 500 }),
    )
    expect(docs).toHaveLength(620)
    expect(docs.filter((doc) => doc.doc_type === 'REQ')).toHaveLength(20)
  })
})
