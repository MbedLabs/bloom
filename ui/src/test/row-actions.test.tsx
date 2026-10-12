// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({ docsApi: { get: vi.fn() } }))
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: null }) }))
vi.mock('../hooks/useProjectByPrefix', () => ({ useProjectByPrefix: () => ({ data: undefined }) }))

const { docsApi } = await import('../api/client')
const { useRowActions } = await import('../hooks/useProjectPermissions')

function Probe({ docId, given }: { docId?: string | null; given?: string[] }) {
  const can = useRowActions('PRJ', 'REQ', docId, given)
  return <div>edit: {String(can('edit'))}; delete: {String(can('delete'))}</div>
}

function renderProbe(props: { docId?: string | null; given?: string[] }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  render(<QueryClientProvider client={client}><Probe {...props} /></QueryClientProvider>)
  return client
}

afterEach(() => { cleanup(); vi.clearAllMocks() })

describe('row actions require an explicit server answer', () => {
  it('does not infer mutation rights for a missing identifier', () => {
    renderProbe({ docId: null })
    expect(screen.getByText('edit: false; delete: false')).toBeTruthy()
    expect(docsApi.get).not.toHaveBeenCalled()
  })

  it('keeps controls unavailable after a failed row read', async () => {
    vi.mocked(docsApi.get).mockRejectedValue(new Error('Access denied'))
    const client = renderProbe({ docId: 'PRJ-REQ-001' })
    await waitFor(() => expect(client.getQueryCache().findAll().some(query => query.state.status === 'error')).toBe(true))
    expect(screen.getByText('edit: false; delete: false')).toBeTruthy()
  })

  it('keeps controls unavailable while the row answer is pending', () => {
    vi.mocked(docsApi.get).mockImplementation(() => new Promise(() => {}))
    renderProbe({ docId: 'PRJ-REQ-001' })
    expect(screen.getByText('edit: false; delete: false')).toBeTruthy()
  })

  it('uses supplied row actions without requesting another row', () => {
    renderProbe({ docId: 'PRJ-REQ-001', given: ['edit'] })
    expect(screen.getByText('edit: true; delete: false')).toBeTruthy()
    expect(docsApi.get).not.toHaveBeenCalled()
  })

  it('shows only the actions returned for the fetched row', async () => {
    vi.mocked(docsApi.get).mockResolvedValue({ allowed_actions: ['delete'] } as never)
    renderProbe({ docId: 'PRJ-REQ-001' })
    expect(await screen.findByText('edit: false; delete: true')).toBeTruthy()
  })
})
