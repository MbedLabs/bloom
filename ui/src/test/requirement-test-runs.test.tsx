/**
 * A requirement lists the Bud runs linked to it, each opening the run in Bud, where
 * the user signs in with their own Bud account and downloads its report.
 */
import { renderPage } from './render'
import type { ReactNode } from 'react'
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'

const requirement = {
  id: 3001,
  project_id: 7,
  parent_id: null,
  req_id: 'PRJ-REQ-3001',
  title: 'Response time',
  description: '',
  status: 'Approved',
  visibility: 'internal',
  priority: 'High',
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
  linked_test_runs: [
    {
      id: 1,
      requirement_id: 3001,
      test_run_id: 77,
      test_run_name: 'Nightly run',
      teststation_url: null,
      status: 'Passed',
      created_at: '2026-07-02T00:00:00Z',
    },
  ],
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
    useQuery: ({ queryKey }: { queryKey: unknown[] }) => {
      let data: unknown = requirement
      if (queryKey[0] === 'project') data = { id: 7, name: 'Project', prefix: 'PRJ' }
      else if (queryKey[0] === 'mentionableUsers' || queryKey[0] === 'users') data = []
      return { data, isLoading: false, error: null }
    },
    useMutation: () => ({ mutate: vi.fn(), isPending: false }),
    useQueryClient: () => ({ invalidateQueries: vi.fn(), setQueryData: vi.fn() }),
  }
})

vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router')
  return {
    ...actual,
    useParams: () => ({ prefix: 'PRJ', itemId: '3001' }),
    useNavigate: () => vi.fn(),
    useLocation: () => ({ state: null }),
    Link: ({ children, to }: { children: ReactNode; to: string }) => <a href={to}>{children}</a>,
  }
})

vi.mock('../components/DocumentLinksPanel', () => ({ DocumentLinksPanel: () => null }))
vi.mock('../components/DocumentActivityPanel', () => ({ default: () => null }))

describe('a requirement lists its linked Bud runs', () => {
  beforeAll(() => {
    vi.stubGlobal('localStorage', { getItem: vi.fn(() => null) })
    vi.stubGlobal('window', { ...globalThis.window, runtimeConfig: { BUD_APP_URL: 'https://bud.example.com' } })
  })
  afterAll(() => vi.unstubAllGlobals())

  it('links each run to Bud with its name and status', async () => {
    const { default: RequirementDetail } = await import('../pages/RequirementDetail')
    const html = renderPage(<RequirementDetail resolvedId={requirement.id} />)
    expect(html).toContain('Test runs')
    expect(html).toContain('href="https://bud.example.com/runs/77"')
    expect(html).toContain('Nightly run')
    expect(html).toContain('Passed')
  })
})
