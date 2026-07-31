import type { ReactNode } from 'react'
import { renderToString } from 'react-dom/server'
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'

let mockParams: Record<string, string> = {}
let mockQueryData: Record<string, unknown> = {}

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'maintainer' } }),
}))

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query')
  return {
    ...actual,
    useQuery: ({ queryKey }: { queryKey: unknown[] }) => ({
      data: mockQueryData[String(queryKey[0])],
      isLoading: false,
      error: null,
    }),
    useMutation: () => ({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
    }),
    useQueryClient: () => ({
      invalidateQueries: vi.fn(),
      setQueryData: vi.fn(),
    }),
  }
})

vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router')
  return {
    ...actual,
    useParams: () => mockParams,
    useNavigate: () => vi.fn(),
    useLocation: () => ({ state: null }),
    Link: ({ children, to }: { children: ReactNode; to: string }) => <a href={to}>{children}</a>,
  }
})

vi.mock('../components/editor', () => ({
  DocEditor: () => null,
}))

vi.mock('../components/DocumentLinksPanel', () => ({
  DocumentLinksPanel: () => null,
}))

vi.mock('../components/DocumentActivityPanel', () => ({
  default: () => null,
}))

function expectNoVisibilityPresentation(html: string) {
  expect(html).not.toMatch(/>Visibility<\/(?:div|span|label)>/)
  expect(html).not.toContain('Internal Only')
  expect(html).not.toContain('Customer Visible')
}

describe('detail visibility presentation', () => {
  beforeAll(() => {
    vi.stubGlobal('localStorage', { getItem: vi.fn(() => null) })
  })

  afterAll(() => {
    vi.unstubAllGlobals()
  })

  it('does not repeat visibility on shared-document details', async () => {
    mockParams = { prefix: 'FLT', docId: '41', kind: 'specifications' }
    mockQueryData = {
      document: {
        id: 41,
        project_id: 7,
        doc_id: 'FLT-SPEC-041',
        title: 'Flight specification',
        status: 'Draft',
        visibility: 'internal',
        version: 1,
        created_at: '2026-07-01T00:00:00Z',
        updated_at: '2026-07-01T00:00:00Z',
        sections: [],
        content_json: null,
      },
      project: { id: 7, name: 'Flight', prefix: 'FLT' },
    }

    const { default: DocumentDetail } = await import('../pages/DocumentDetail')
    const html = renderToString(<DocumentDetail />)

    expect(html).toContain('Flight specification')
    expectNoVisibilityPresentation(html)
  })

  it('does not repeat visibility on test-case details', async () => {
    mockParams = { prefix: 'FLT', itemId: '42' }
    mockQueryData = {
      testCase: {
        id: 42,
        project_id: 7,
        tc_id: 'FLT-TC-042',
        title: 'Audit test case',
        description: '',
        status: 'Draft',
        visibility: 'internal',
        steps: [],
        reviewer_id: null,
        approver_id: null,
        reviewed_by_id: null,
        approved_by_id: null,
        reviewed_at: null,
        approved_at: null,
        created_at: '2026-07-01T00:00:00Z',
        updated_at: '2026-07-01T00:00:00Z',
        suite_memberships: [],
        campaign_memberships: [],
        linked_requirements: [],
        verifies: [],
      },
      project: { id: 7, name: 'Flight', prefix: 'FLT' },
      users: [],
    }

    const { default: TestCaseDetail } = await import('../pages/TestCaseDetail')
    const html = renderToString(<TestCaseDetail />)

    expect(html).toContain('Audit test case')
    expectNoVisibilityPresentation(html)
  })

  it('does not repeat visibility on controlled-artefact details', async () => {
    mockParams = { prefix: 'FLT', itemId: '43' }
    mockQueryData = {
      design: {
        id: 43,
        project_id: 7,
        design_id: 'FLT-DES-043',
        title: 'Audit design',
        description: '',
        status: 'Draft',
        visibility: 'internal',
        design_type: 'Architecture',
        priority: 'Medium',
        content_json: null,
        created_at: '2026-07-01T00:00:00Z',
        updated_at: '2026-07-01T00:00:00Z',
      },
      project: { id: 7, name: 'Flight', prefix: 'FLT' },
      artefactComments: [],
      artefactActivity: [],
      artefactRelated: {
        project: { id: 7, name: 'Flight', prefix: 'FLT' },
        linked_requirements: [],
        related_test_cases: [],
        related_documents: [],
      },
    }

    const { default: ArtefactDetail } = await import('../pages/ArtefactDetail')
    const html = renderToString(<ArtefactDetail kind="design" />)

    expect(html).toContain('Audit design')
    expectNoVisibilityPresentation(html)
  })
})
