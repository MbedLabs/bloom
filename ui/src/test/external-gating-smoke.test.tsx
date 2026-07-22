import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToString } from 'react-dom/server'
import type { ReactNode } from 'react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

type MockUser = {
  role: 'admin' | 'maintainer' | 'external'
} | null

let mockUser: MockUser = { role: 'external' }
let mockParams: Record<string, string> = {}
let mockLocationState: { returnTo?: string } | null = null
let mockQueryData: Record<string, unknown> = {}
let mockProject: { id: number; name: string; prefix: string } | null = null

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isLoading: false,
    isAuthenticated: !!mockUser,
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
    useLocation: () => ({ state: mockLocationState }),
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
  default: ({ actions, children, rightRail }: { actions?: ReactNode; children?: ReactNode; rightRail?: ReactNode }) => (
    <div>
      <div>{actions}</div>
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
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return renderToString(
    <QueryClientProvider client={queryClient}>
      {element}
    </QueryClientProvider>,
  )
}

describe('external user mutation gating smoke', () => {
  beforeEach(() => {
    mockUser = { role: 'external' }
    mockParams = {}
    mockLocationState = null
    mockProject = { id: 7, name: 'Vehicle Controls', prefix: 'VCU' }
    mockQueryData = {}
    const storage = { getItem: vi.fn(() => null) }
    vi.stubGlobal('window', {
      runtimeConfig: {},
      localStorage: storage,
    })
    vi.stubGlobal('localStorage', storage)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('hides document edit/delete actions for external users', async () => {
    mockParams = { prefix: 'VCU', docId: '42', kind: 'specifications' }
    mockQueryData = {
      document: {
        id: 42,
        project_id: 7,
        doc_id: 'VCU-SPEC-001',
        title: 'System Specification',
        status: 'Draft',
        visibility: 'customer',
        version: 1,
        created_at: '2026-06-01T00:00:00Z',
        updated_at: '2026-06-01T00:00:00Z',
        sections: [],
        content_json: null,
      },
      project: mockProject,
    }

    const { default: DocumentDetail } = await import('../pages/DocumentDetail')
    const html = renderPage(<DocumentDetail />)

    expect(html).not.toContain('>Edit<')
    expect(html).not.toContain('>Delete<')
  })

  it('hides suite mutation actions for external users', async () => {
    mockParams = { prefix: 'VCU', suiteId: '12' }
    mockQueryData = {
      testSuite: {
        id: 12,
        suite_id: 'VCU-TS-001',
        name: 'Nightly Suite',
        description: 'Regression',
        status: 'Active',
        visibility: 'customer',
        items: [],
      },
      testCases: { items: [] },
      'bud-test-runs': { runs: [] },
    }

    const { default: SuiteDetail } = await import('../pages/SuiteDetail')
    const html = renderPage(<SuiteDetail />)

    expect(html).not.toContain('>Edit<')
    expect(html).not.toContain('>Delete<')
    expect(html).not.toContain('Add Test Case')
    expect(html).not.toContain('Create Campaign Scope')
  })

  it('hides campaign edit/delete actions for external users', async () => {
    mockParams = { prefix: 'VCU', campaignId: '22' }
    mockQueryData = {
      campaign: {
        id: 22,
        campaign_id: 'VCU-CMP-001',
        name: 'Scope Campaign',
        description: 'Visible to customer',
        status: 'Scope',
        visibility: 'customer',
        bud_run_id: null,
        suite_scopes: [],
        ad_hoc_items: [],
      },
      'campaign-scope-links': [],
    }

    const { default: CampaignDetail } = await import('../pages/CampaignDetail')
    const html = renderPage(<CampaignDetail />)

    expect(html).not.toContain('>Edit<')
    expect(html).not.toContain('>Delete<')
  })

  it('shows project parameters as read-only denied for external users', async () => {
    mockParams = { prefix: 'VCU' }

    const { default: ProjectParameters } = await import('../pages/ProjectParameters')
    const html = renderPage(<ProjectParameters />)

    expect(html).toContain('Only admins and maintainers can view or edit project parameters.')
    expect(html).not.toContain('Add Item')
  })
})
