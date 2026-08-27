/**
 * Turning reviewer and approver ids into names on a detail page.
 *
 * These fields are sign-off records, so a name matters. The page used to read
 * them out of `/users`, the admin-only directory, which handed every
 * maintainer a 403 - and a failed list is indistinguishable from an empty one
 * here, so a maintainer saw "User #5" where a colleague's name belonged.
 *
 * It now reads the project's own people, and admins additionally read the
 * directory. That second query is what keeps a *historical* actor resolvable:
 * whoever approved something last quarter may since have left the project, so
 * they are not in its member list any more. A maintainer falls back to the
 * bare id for those, which is the accepted trade-off - an id still identifies
 * the person who signed off.
 */
import { renderPage } from './render'
import type { ReactNode } from 'react'
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

/** The signed-off requirement: reviewed by a member, approved by someone gone. */
const requirement = {
  id: 2001,
  project_id: 7,
  parent_id: null,
  req_id: 'FLT-REQ-2001',
  title: 'Brake actuator response time',
  description: 'Stop within budget.',
  status: 'Approved',
  visibility: 'internal',
  priority: 'High',
  req_type: 'Safety',
  req_origin: 'Internal',
  reviewer_id: 5,
  approver_id: 12,
  reviewed_by_id: 5,
  approved_by_id: 12,
  reviewed_at: '2026-07-02T00:00:00Z',
  approved_at: '2026-07-03T00:00:00Z',
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
  children: [],
  linked_test_runs: [],
  suite_backlinks: [],
  campaign_backlinks: [],
}

const ON_THE_PROJECT = [{ id: 5, full_name: 'Grace Hopper' }]
const DIRECTORY = [
  { id: 5, full_name: 'Grace Hopper' },
  { id: 12, full_name: 'Departed Approver' },
]

const auth = { role: 'maintainer' }

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { role: auth.role } }),
}))

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query')
  return {
    ...actual,
    // `enabled` is honoured so a role-gated query really is absent, which is
    // the whole difference between the two readers below.
    useQuery: ({ queryKey, enabled = true }: { queryKey: unknown[]; enabled?: boolean }) => {
      let data: unknown = requirement
      if (queryKey[0] === 'project') data = { id: 7, name: 'Flight', prefix: 'FLT' }
      else if (queryKey[0] === 'mentionableUsers') data = ON_THE_PROJECT
      else if (queryKey[0] === 'users') data = DIRECTORY
      return { data: enabled === false ? undefined : data, isLoading: false, error: null }
    },
    useMutation: () => ({ mutate: vi.fn(), isPending: false }),
    useQueryClient: () => ({ invalidateQueries: vi.fn(), setQueryData: vi.fn() }),
  }
})

vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router')
  return {
    ...actual,
    useParams: () => ({ prefix: 'FLT', itemId: '2001' }),
    useNavigate: () => vi.fn(),
    useLocation: () => ({ state: null }),
    Link: ({ children, to }: { children: ReactNode; to: string }) => <a href={to}>{children}</a>,
  }
})

vi.mock('../components/DocumentLinksPanel', () => ({ DocumentLinksPanel: () => null }))
vi.mock('../components/DocumentActivityPanel', () => ({ default: () => null }))

async function renderAs(role: string): Promise<string> {
  auth.role = role
  const { default: RequirementDetail } = await import('../pages/RequirementDetail')
  return renderPage(<RequirementDetail resolvedId={requirement.id} />)
}

describe('reviewer and approver names on a detail page', () => {
  beforeAll(() => {
    vi.stubGlobal('localStorage', { getItem: vi.fn(() => null) })
  })

  afterEach(() => {
    auth.role = 'maintainer'
  })

  afterAll(() => {
    vi.unstubAllGlobals()
  })

  it('names a reviewer who is on the project, for a maintainer', async () => {
    const html = await renderAs('maintainer')

    // The bug: this used to render "User #5".
    expect(html).toContain('Grace Hopper')
    expect(html).not.toContain('User #5')
  })

  it('falls back to the id for someone who has left, for a maintainer', async () => {
    const html = await renderAs('maintainer')

    // Accepted trade-off: the project list cannot name a former member, and an
    // id still says who signed off.
    expect(html).toContain('User #12')
  })

  it('still names a departed approver for an admin', async () => {
    const html = await renderAs('admin')

    // Admins read the directory too, so this must not regress to an id.
    expect(html).toContain('Departed Approver')
    expect(html).not.toContain('User #12')
  })
})
