import { renderPage } from './render'
import type { ReactNode } from 'react'
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'

const requirement = {
  id: 1064,
  project_id: 7,
  parent_id: null,
  req_id: 'FLT-REQ-1064',
  title: 'Audit Stats Top-User Count Consistency',
  description: 'Keep audit statistics consistent.',
  status: 'Draft',
  visibility: 'internal',
  priority: 'Medium',
  req_type: 'Functional',
  req_origin: 'Internal',
  reviewer_id: null,
  approver_id: null,
  reviewed_by_id: null,
  approved_by_id: null,
  reviewed_at: null,
  approved_at: null,
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
  children: [],
  linked_test_runs: [],
  suite_backlinks: [],
  campaign_backlinks: [],
}

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'maintainer' } }),
}))

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query')
  return {
    ...actual,
    useQuery: ({ queryKey }: { queryKey: unknown[] }) => ({
      data: queryKey[0] === 'project'
        ? { id: 7, name: 'Flight', prefix: 'FLT' }
        : queryKey[0] === 'users'
          ? []
          : requirement,
      isLoading: false,
      error: null,
    }),
    useMutation: () => ({ mutate: vi.fn(), isPending: false }),
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
    useParams: () => ({ prefix: 'FLT', itemId: '1064' }),
    useNavigate: () => vi.fn(),
    useLocation: () => ({ state: null }),
    Link: ({ children, to }: { children: ReactNode; to: string }) => <a href={to}>{children}</a>,
  }
})

vi.mock('../components/DocumentLinksPanel', () => ({
  DocumentLinksPanel: () => null,
}))

vi.mock('../components/DocumentActivityPanel', () => ({
  default: () => null,
}))

describe('requirement origin presentation', () => {
  beforeAll(() => {
    vi.stubGlobal('localStorage', { getItem: vi.fn(() => null) })
  })

  afterAll(() => {
    vi.unstubAllGlobals()
  })

  it('shows origin without duplicating derived visibility', async () => {
    const { default: RequirementDetail } = await import('../pages/RequirementDetail')

    const html = renderPage(<RequirementDetail resolvedId={requirement.id} />)

    expect(html).toContain('Audit Stats Top-User Count Consistency')
    expect(html).toMatch(/>Origin<\/div>/)
    expect(html).toMatch(/>Internal<\/span>/)
    expect(html).not.toMatch(/>Visibility<\/div>/)
    expect(html).not.toContain('Internal Only')
  })
})
