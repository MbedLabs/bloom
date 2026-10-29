// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../lib/queryClient'

vi.mock('../api/client', () => ({
  docsApi: {
    get: vi.fn().mockResolvedValue({ id: 4711, doc_id: 'ABC-REQ-0005', doc_type: 'REQ', allowed_actions: [] }),
  },
}))

vi.mock('../hooks/useProjectByPrefix', () => ({
  useProjectByPrefix: () => ({ data: { id: 2, prefix: 'ABC' }, error: null }),
}))

vi.mock('../pages/RequirementDetail', () => ({
  default: ({ resolvedId }: { resolvedId: number }) => <div>requirement {resolvedId}</div>,
}))
vi.mock('../pages/TestCaseDetail', () => ({ default: () => null }))
vi.mock('../pages/DocumentDetail', () => ({ default: () => null }))
vi.mock('../pages/ArtefactDetail', () => ({ default: () => null }))
vi.mock('../pages/CampaignDetail', () => ({ default: () => null }))
vi.mock('../pages/SuiteDetail', () => ({ default: () => null }))
vi.mock('../components/AccessDenied', () => ({ default: () => null }))

const UnifiedDocDetail = (await import('../pages/UnifiedDocDetail')).default

/** The current address, for the assertions. */
function Address() {
  return <output>{useLocation().pathname}</output>
}

afterEach(cleanup)

describe('a document address with a database id', () => {
  it('opens the document and shows its document ID in the address', async () => {
    const client = createQueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/projects/ABC/docs/requirements/4711']}>
          <Routes>
            <Route path="/projects/:prefix/docs/:kind/:docId" element={<><UnifiedDocDetail /><Address /></>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('requirement 4711')).toBeTruthy()
    expect(await screen.findByText('/projects/ABC/docs/requirements/ABC-REQ-0005')).toBeTruthy()
  })
})
