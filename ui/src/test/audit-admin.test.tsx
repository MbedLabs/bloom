import { changeControl, optionValues } from './change-control'
import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom
/**
 * The admin audit log screen: it lists events newest first and filters them by
 * event group and outcome.
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const page = {
  total: 2,
  items: [
    {
      id: 2, occurred_at: '2026-09-24T10:00:00', actor_user_id: 1, actor_name: 'Ada Admin',
      actor_type: 'user', action: 'user.role_changed', target_type: 'user', target_id: '5',
      project_id: null, request_id: 'req-2', ip: '10.0.0.1', user_agent: 'x', outcome: 'success',
      details: { from: 'maintainer', to: 'external' },
    },
    {
      id: 1, occurred_at: '2026-09-24T09:00:00', actor_user_id: null, actor_name: null,
      actor_type: 'anonymous', action: 'auth.login', target_type: 'user', target_id: '5',
      project_id: null, request_id: 'req-1', ip: '10.0.0.2', user_agent: 'x', outcome: 'failure',
      details: null,
    },
  ],
}

const requestPage = {
  total: 5,
  items: [
    {
      id: 15, occurred_at: '2026-10-28T10:05:00', actor_user_id: 1, actor_name: 'Ada Admin',
      actor_type: 'user', action: 'api.request', target_type: null, target_id: null,
      project_id: 3, request_id: 'req-15', ip: '10.0.0.1', user_agent: 'bloom-mcp/1.3.0', outcome: 'success',
      details: {
        method: 'POST', route: '/api/projects/{project_id}/requirements', path: '/api/projects/3/requirements',
        status: 201, duration_ms: 12.5, query: [], auth: 'bearer', client: 'cli', created_id: 42, created_doc_id: 'PRJ-REQ-001',
      },
    },
    {
      id: 14, occurred_at: '2026-10-28T10:04:00', actor_user_id: 1, actor_name: 'Ada Admin',
      actor_type: 'user', action: 'api.request', target_type: 'requirement', target_id: '42',
      project_id: null, request_id: 'req-14', ip: '10.0.0.1', user_agent: 'Mozilla/5.0', outcome: 'success',
      details: { method: 'GET', route: '/api/requirements/{requirement_id}', path: '/api/requirements/42', status: 200, client: 'web' },
    },
    {
      id: 13, occurred_at: '2026-10-28T10:03:00', actor_user_id: null, actor_name: null,
      actor_type: 'service', action: 'api.request', target_type: null, target_id: null,
      project_id: null, request_id: 'req-13', ip: '10.0.0.3', user_agent: 'bud', outcome: 'success',
      details: { method: 'POST', route: '/api/bud/results', path: '/api/bud/results', status: 200, service_credential_id: 7 },
    },
    {
      id: 12, occurred_at: '2026-10-28T10:02:00', actor_user_id: null, actor_name: null,
      actor_type: 'service', action: 'api.request', target_type: null, target_id: null,
      project_id: null, request_id: 'req-12', ip: '10.0.0.3', user_agent: 'bud', outcome: 'denied',
      details: { method: 'POST', route: '/api/bud/results', path: '/api/bud/results', status: 403, service_credential_id: 9 },
    },
    {
      id: 11, occurred_at: '2026-10-28T10:01:00', actor_user_id: null, actor_name: null,
      actor_type: 'anonymous', action: 'security.repeated_refusals', target_type: null, target_id: null,
      project_id: null, request_id: 'req-11', ip: '10.0.0.9', user_agent: 'curl/8', outcome: 'denied',
      details: { address: '10.0.0.9', count: 20, window_minutes: 10 },
    },
  ],
}

vi.mock('../api/client', () => ({
  auditApi: { list: vi.fn().mockResolvedValue(page) },
  usersApi: { list: vi.fn().mockResolvedValue([]) },
  serviceCredentialsApi: { list: vi.fn().mockResolvedValue([]) },
}))

const api = await import('../api/client')
const AuditPage = (await import('../pages/Audit')).default

function renderPage() {
  const client = createQueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <AuditPage />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.auditApi.list).mockResolvedValue(page)
  vi.mocked(api.usersApi.list).mockResolvedValue([{ id: 5, full_name: 'Grace Hopper', email: 'grace@example.com' }] as never)
  vi.mocked(api.serviceCredentialsApi.list).mockResolvedValue([{ id: 7, name: 'Bud result sync' }] as never)
})
afterEach(cleanup)

describe('Audit log admin screen', () => {
  it('lists events with actor, event, target, outcome and request', async () => {
    renderPage()
    expect(await screen.findByText('Ada Admin')).toBeTruthy()
    expect(screen.getByText('user.role_changed')).toBeTruthy()
    expect(screen.getByText('anonymous')).toBeTruthy()
    expect(screen.getByText('failure')).toBeTruthy()
    expect(screen.getByText('req-1')).toBeTruthy()
    expect(screen.getByText('2 events')).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Time' })).toBeTruthy()
    expect(screen.queryByText('Time (UTC)')).toBeNull()
  })

  it('filters by event group and outcome from the first page', async () => {
    renderPage()
    await screen.findByText('Ada Admin')
    changeControl(screen.getByLabelText('Events'), { target: { value: 'auth.' } })
    changeControl(screen.getByLabelText('Outcome'), { target: { value: 'failure' } })
    await waitFor(() =>
      expect(api.auditApi.list).toHaveBeenLastCalledWith(
        expect.objectContaining({ action: 'auth.', outcome: 'failure', offset: 0 }),
      ),
    )
  })

  it('sorts the full audit query and resets pagination while retaining filters', async () => {
    vi.mocked(api.auditApi.list).mockResolvedValue({ ...page, total: 60 })
    renderPage()
    await screen.findByText('Ada Admin')
    changeControl(screen.getByLabelText('Outcome'), { target: { value: 'failure' } })
    await waitFor(() => expect((screen.getByRole('button', { name: 'Next' }) as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 50 })))
    fireEvent.click(screen.getByRole('columnheader', { name: 'Actor' }))
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ sort: 'actor', dir: 'asc', offset: 0, outcome: 'failure' })))
    fireEvent.click(screen.getByRole('columnheader', { name: 'Actor' }))
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ sort: 'actor', dir: 'desc' })))
  })
  it('keeps literal date bounds and resets pagination when a date is selected or cleared', async () => {
    vi.mocked(api.auditApi.list).mockResolvedValue({ ...page, total: 60 })
    renderPage()
    await screen.findByText('Ada Admin')
    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2024-02-28' } })
    await waitFor(() => expect((screen.getByRole('button', { name: 'Next' }) as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ since: '2024-02-28', offset: 50 })))
    fireEvent.click(screen.getByRole('button', { name: 'Choose date for From' }))
    const dateLabel = new Intl.DateTimeFormat(navigator.language, { dateStyle: 'full', calendar: 'gregory' }).format(new Date(2024, 1, 29))
    fireEvent.click(screen.getByRole('button', { name: dateLabel }))
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ since: '2024-02-29', offset: 0 })))
    fireEvent.change(screen.getByLabelText('Until'), { target: { value: '2024-03-01' } })
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ since: '2024-02-29', until: '2024-03-01' })))
    fireEvent.click(screen.getByRole('button', { name: 'Choose date for From' }))
    fireEvent.click(screen.getByRole('button', { name: 'Clear' }))
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ since: undefined, until: '2024-03-01', offset: 0 })))
  })

  it('says every API request and every refused attempt is recorded', async () => {
    renderPage()
    await screen.findByText('Ada Admin')
    expect(screen.getByText(/Every API request and every refused attempt is recorded/)).toBeTruthy()
  })

  it('offers API calls, refused attempts and a group for every event prefix', async () => {
    renderPage()
    await screen.findByText('Ada Admin')
    const groups = optionValues(screen.getByRole('combobox', { name: 'Events' }))
    for (const value of ['api.', 'refused', 'access.', 'report.', 'project.', 'tag.', 'baseline.', 'workflow.', 'setup.', 'company_logo.', 'auth.', 'attachment.']) {
      expect(groups).toContain(value)
    }
    expect(optionValues(screen.getByRole('combobox', { name: 'Outcome' }))).toContain('denied')
  })

  it('filters API calls by prefix and refused attempts by the denied outcome', async () => {
    renderPage()
    await screen.findByText('Ada Admin')
    changeControl(screen.getByRole('combobox', { name: 'Events' }), { target: { value: 'api.' } })
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ action: 'api.', outcome: undefined, offset: 0 })))
    changeControl(screen.getByRole('combobox', { name: 'Outcome' }), { target: { value: 'success' } })
    changeControl(screen.getByRole('combobox', { name: 'Events' }), { target: { value: 'refused' } })
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ action: undefined, outcome: 'denied', offset: 0 })))
    const outcome = screen.getByRole('combobox', { name: 'Outcome' }) as HTMLButtonElement
    expect(outcome.disabled).toBe(true)
    expect(outcome.textContent).toContain('Denied')
    changeControl(screen.getByRole('combobox', { name: 'Events' }), { target: { value: '' } })
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ action: undefined, outcome: 'success' })))
  })

  it('filters by actor kind or one user from the first page', async () => {
    vi.mocked(api.auditApi.list).mockResolvedValue({ ...page, total: 60 })
    renderPage()
    await screen.findByText('Ada Admin')
    await waitFor(() => expect((screen.getByRole('button', { name: 'Next' }) as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 50 })))
    fireEvent.click(screen.getByRole('combobox', { name: 'Actor' }))
    fireEvent.click(screen.getByRole('option', { name: 'Service credential' }))
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ actor_type: 'service', offset: 0 })))
    fireEvent.click(screen.getByRole('combobox', { name: 'Actor' }))
    fireEvent.click(screen.getByRole('option', { name: 'Anonymous' }))
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ actor_type: 'anonymous' })))
    fireEvent.click(screen.getByRole('combobox', { name: 'Actor' }))
    fireEvent.click(await screen.findByRole('option', { name: 'Grace Hopper' }))
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ actor_user_id: 5, actor_type: undefined })))
    fireEvent.click(screen.getByRole('combobox', { name: 'Actor' }))
    fireEvent.click(screen.getByRole('option', { name: 'Any user' }))
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ actor_type: 'user', actor_user_id: undefined })))
    fireEvent.click(screen.getByRole('combobox', { name: 'Actor' }))
    fireEvent.click(screen.getByRole('option', { name: 'Anyone' }))
    expect(screen.getByRole('combobox', { name: 'Actor' }).textContent).toBe('Anyone')
  })

  it('filters by address and request id once typing pauses', async () => {
    renderPage()
    await screen.findByText('Ada Admin')
    fireEvent.change(screen.getByLabelText('Address'), { target: { value: ' 10.0.0.9 ' } })
    fireEvent.change(screen.getByLabelText('Request'), { target: { value: 'req-11' } })
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ ip: '10.0.0.9', request_id: 'req-11', offset: 0 })))
    fireEvent.change(screen.getByLabelText('Address'), { target: { value: '' } })
    await waitFor(() => expect(api.auditApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ ip: undefined, request_id: 'req-11' })))
  })

  it('shows API requests by method, route, status and target, and names their actors', async () => {
    vi.mocked(api.auditApi.list).mockResolvedValue(requestPage)
    renderPage()
    const created = await screen.findByText('POST /api/projects/{project_id}/requirements')
    expect(created.getAttribute('title')).toBe('/api/projects/3/requirements')
    expect(screen.getByText('201')).toBeTruthy()
    expect(screen.getByText('created PRJ-REQ-001')).toBeTruthy()
    expect(screen.getByText('GET /api/requirements/{requirement_id}')).toBeTruthy()
    expect(screen.getAllByText('200').some((status) => status.parentElement?.textContent === '200requirement 42')).toBe(true)
    const cli = screen.getAllByText('MCP or CLI')
    expect(cli).toHaveLength(1)
    expect(cli[0].getAttribute('title')).toBe('bloom-mcp/1.3.0')
    const named = screen.getByText('Bud result sync')
    expect(named.getAttribute('title')).toBe('Service credential #7')
    expect(screen.getByText('Service credential #9')).toBeTruthy()
    expect(screen.getByText('403')).toBeTruthy()
    expect(screen.getByText('security.repeated_refusals')).toBeTruthy()
    expect(screen.getByText('anonymous')).toBeTruthy()
    const denied = screen.getAllByText('denied')
    expect(denied).toHaveLength(2)
    expect(denied.every((cell) => cell.className.includes('text-red-600'))).toBe(true)
    expect(screen.getAllByText('success')[0].className).not.toContain('text-red-600')
  })

  it('names a service credential by id when the credential list is unavailable', async () => {
    vi.mocked(api.auditApi.list).mockResolvedValue(requestPage)
    vi.mocked(api.serviceCredentialsApi.list).mockRejectedValue(new Error('denied'))
    renderPage()
    expect(await screen.findByText('Service credential #7')).toBeTruthy()
    expect(screen.queryByText('Bud result sync')).toBeNull()
  })

})
