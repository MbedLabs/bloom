// @vitest-environment jsdom
/**
 * Edit controls follow the server's effective permissions.
 *
 * A group policy can give an external user authoring rights on one kind of
 * artefact, or hold a maintainer to read-only. The hook reads the set the server
 * resolved and falls back to what the role alone allows while it has none.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

let currentUser: { id: number; role: string } | null = { id: 3, role: 'external' }

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: currentUser }),
}))

vi.mock('../api/client', () => ({
  projectMembersApi: { permissions: vi.fn() },
  projectsApi: { getByPrefix: vi.fn(async () => ({ id: 5, prefix: 'VCU' })) },
}))

const client = await import('../api/client')
const { allows, useProjectPermissions } = await import('../hooks/useProjectPermissions')

function Probe({ prefix, projectId }: { prefix?: string; projectId?: number }) {
  const { can, canAny } = useProjectPermissions(prefix, projectId)
  return (
    <ul>
      <li>test case create: {String(can('create', 'test_case'))}</li>
      <li>requirement create: {String(can('create', 'requirement'))}</li>
      <li>requirement view: {String(can('view', 'requirement'))}</li>
      <li>any create: {String(canAny('create'))}</li>
    </ul>
  )
}

function renderProbe(props: { prefix?: string; projectId?: number }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <Probe {...props} />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  currentUser = { id: 3, role: 'external' }
})

describe('useProjectPermissions', () => {
  it('uses the server set, so a group policy adds to an external role', async () => {
    vi.mocked(client.projectMembersApi.permissions).mockResolvedValue({
      '*': ['view', 'comment'],
      test_case: ['create', 'edit'],
    })
    renderProbe({ prefix: 'VCU' })
    await screen.findByText('test case create: true')
    expect(client.projectMembersApi.permissions).toHaveBeenCalledWith(5)
    expect(screen.getByText('requirement create: false')).toBeTruthy()
    expect(screen.getByText('any create: true')).toBeTruthy()
  })

  it('holds a maintainer to a read-only set', async () => {
    currentUser = { id: 4, role: 'maintainer' }
    vi.mocked(client.projectMembersApi.permissions).mockResolvedValue({ requirement: ['view'] })
    renderProbe({ projectId: 5 })
    await screen.findByText('requirement create: false')
    expect(screen.getByText('requirement view: true')).toBeTruthy()
    expect(client.projectsApi.getByPrefix).not.toHaveBeenCalled()
  })

  it('falls back to the role while the server set is missing', async () => {
    vi.mocked(client.projectMembersApi.permissions).mockRejectedValue(new Error('offline'))
    renderProbe({ projectId: 5 })
    await vi.waitFor(() => expect(client.projectMembersApi.permissions).toHaveBeenCalled())
    expect(screen.getByText('requirement view: true')).toBeTruthy()
    expect(screen.getByText('requirement create: false')).toBeTruthy()

    cleanup()
    currentUser = { id: 1, role: 'admin' }
    renderProbe({ projectId: 5 })
    expect(screen.getByText('requirement create: true')).toBeTruthy()

    cleanup()
    currentUser = null
    renderProbe({})
    expect(screen.getByText('requirement view: false')).toBeTruthy()
  })
})

describe('allows', () => {
  it('reads resource and wildcard entries', () => {
    expect(allows({ '*': ['*'] }, 'delete', 'member')).toBe(true)
    expect(allows({ design: ['*'] }, 'approve', 'design')).toBe(true)
    expect(allows({ design: ['view'] }, 'edit', 'design')).toBe(false)
    expect(allows({}, 'view', 'design')).toBe(false)
  })
})
