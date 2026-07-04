import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { renderToString } from 'react-dom/server'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

let mockParams: Record<string, string> = {}
let mockQueryData: Record<string, unknown> = {}
let mockProject: { id: number; name: string; prefix: string } | null = null

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { role: 'maintainer' },
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}))

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query')
  return {
    ...actual,
    useQuery: ({ queryKey }: { queryKey: unknown[] }) => ({
      data: mockQueryData[String(queryKey[0])],
      isLoading: false,
    }),
    useMutation: () => ({
      mutate: vi.fn(),
      isPending: false,
    }),
    useQueryClient: () => ({
      invalidateQueries: vi.fn(),
      setQueryData: vi.fn(),
    }),
  }
})

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useParams: () => mockParams,
    useNavigate: () => vi.fn(),
    useLocation: () => ({ state: null }),
    Link: ({ children, to }: { children: ReactNode; to: string }) => <a href={to}>{children}</a>,
  }
})

vi.mock('../hooks/useProjectByPrefix', () => ({
  useProjectByPrefix: () => ({
    data: mockProject,
    isLoading: false,
  }),
}))

vi.mock('../contexts/PageMetaContext', () => ({
  usePageMeta: () => ({
    setCrumbLabel: vi.fn(),
  }),
}))

vi.mock('../components/editor', () => ({
  DocEditor: () => null,
}))

vi.mock('../components/DocumentLinksPanel', () => ({
  DocumentLinksPanel: () => null,
}))

vi.mock('../components/DocumentActivityPanel', () => ({
  default: () => null,
}))

vi.mock('../components/DocDetailShell', () => ({
  default: ({ children, rightRail }: { children?: ReactNode; rightRail?: ReactNode }) => (
    <div>
      <div>{children}</div>
      <div>{rightRail}</div>
    </div>
  ),
  MetaItem: ({ label, value }: { label: string; value: ReactNode }) => (
    <div>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  ),
  SectionCard: ({ title, children }: { title: string; children: ReactNode }) => (
    <section>
      <h3>{title}</h3>
      {children}
    </section>
  ),
}))

function renderPage(element: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return renderToString(
    <QueryClientProvider client={queryClient}>
      {element}
    </QueryClientProvider>,
  )
}

describe('Bloom Bud run links', () => {
  beforeEach(() => {
    mockParams = {}
    mockProject = { id: 7, name: 'Vehicle Controls', prefix: 'VCU' }
    mockQueryData = {}
    const storage = { getItem: vi.fn(() => null), setItem: vi.fn() }
    vi.stubGlobal('window', {
      runtimeConfig: { BUD_APP_URL: 'https://bud.embedlabs.net/api' },
      localStorage: storage,
    })
    vi.stubGlobal('localStorage', storage)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the TC last Bud run as a clickable Bud link', async () => {
    mockParams = { prefix: 'VCU', itemId: '42' }
    mockQueryData = {
      testCase: {
        id: 42,
        project_id: 7,
        tc_id: 'VCU-TC-001',
        title: 'Clickable TC',
        description: '',
        preconditions: '',
        steps: [],
        status: 'Draft',
        visibility: 'customer',
        created_at: '2026-07-04T00:00:00Z',
        updated_at: '2026-07-04T00:00:00Z',
        requirement_count: 0,
        linked_requirements: [],
        verifies: [],
        suite_memberships: [],
        last_execution_status: 'Passed',
        last_executed_at: '2026-07-04T09:30:00Z',
        last_execution_comment: 'Last result from Bud run 987',
        last_bud_run_id: 987,
      },
      users: [],
      project: mockProject,
    }

    const { default: TestCaseDetail } = await import('../pages/TestCaseDetail')

    const html = renderPage(<TestCaseDetail />)

    expect(html).toContain('Bud run #987')
    expect(html).toContain('href="https://bud.embedlabs.net/runs/987"')
  })

  it('renders the suite latest Bud run as a clickable Bud link', async () => {
    mockParams = { prefix: 'VCU', suiteId: '12' }
    mockQueryData = {
      testSuite: {
        id: 12,
        project_id: 7,
        suite_id: 'VCU-TS-001',
        name: 'Nightly Suite',
        description: '',
        status: 'Active',
        visibility: 'customer',
        total_items: 1,
        last_execution_status: 'Passed',
        last_executed_at: '2026-07-04T09:30:00Z',
        last_bud_run_id: 987,
        items: [],
        related_requirements: [],
        linked_campaigns: [],
        related_concepts: [],
      },
      testCases: { items: [] },
      'bud-test-runs': { runs: [] },
    }

    const { default: SuiteDetail } = await import('../pages/SuiteDetail')

    const html = renderPage(<SuiteDetail />)

    expect(html).toContain('Bud run #987')
    expect(html).toContain('href="https://bud.embedlabs.net/runs/987"')
  })
})
