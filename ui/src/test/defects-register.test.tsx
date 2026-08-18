// @vitest-environment jsdom
/**
 * The defect register: raising defects, and finding them again.
 *
 * Status and severity are filtered by the server - they go into the query so
 * the list comes back already narrowed - while the search box and the sort are
 * done in the browser over what arrived. That split is easy to get wrong in
 * either direction, so these check both sides of it, along with the optional
 * external-issue fields that link a defect to GitHub or GitLab.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { defect, project, resetApiMocks, user } from './apiFixtures'
import { settle } from './settle'

vi.mock('../api/client', async (importOriginal) => {
  const { mockApiModule: build } = await import('./apiFixtures')
  return build(await importOriginal<Record<string, unknown>>(), vi)
})

/** The signed-in user, swapped per test to check what each role may do. */
let currentUser: Record<string, unknown> = user

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: currentUser,
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

const client = await import('../api/client')
const Defects = (await import('../pages/Defects')).default

const flicker = {
  ...defect,
  id: 51,
  defect_id: 'VCU-DEF-001',
  title: 'Alpha screen flickers on wake',
  status: 'Open',
  severity: 'High',
  priority: 'High',
  external_issue_url: null,
  external_issue_number: null,
  updated_at: '2026-03-01T09:00:00Z',
}
const brownout = {
  ...defect,
  id: 52,
  defect_id: 'VCU-DEF-002',
  title: 'Bravo brownout resets the clock',
  status: 'Triaged',
  severity: 'Critical',
  priority: 'Critical',
  external_tracker: 'github',
  external_repo_full_name: 'embedlabs/vcu',
  external_issue_number: 42,
  external_issue_url: 'https://github.com/embedlabs/vcu/issues/42',
  updated_at: '2026-04-01T09:00:00Z',
}
const cosmetic = {
  ...defect,
  id: 53,
  defect_id: 'VCU-DEF-003',
  title: 'Charlie label is misaligned',
  status: 'Resolved',
  severity: 'Low',
  priority: 'Low',
  external_issue_url: null,
  external_issue_number: null,
  updated_at: '2026-01-05T09:00:00Z',
}

const ALL = [flicker, brownout, cosmetic]

function envelope(items: unknown[]) {
  return { items, total: items.length, skip: 0, limit: 50 }
}

function renderDefects() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/projects/VCU/defects']}>
          <Routes>
            <Route path="/projects/:prefix/defects" element={<Defects />} />
            <Route path="/projects/:prefix/defects/:itemId" element={<div>defect detail</div>} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** The defect identifiers in the table, top to bottom. */
function rows(): string[] {
  const table = screen.queryByRole('table')
  if (!table) return []
  return within(table)
    .getAllByRole('row')
    .slice(1)
    .map((row) => /VCU-DEF-\d+/.exec(row.textContent ?? '')?.[0] ?? '')
}

/** The arguments of the most recent call to a mocked endpoint. */
function lastCall(fn: unknown): unknown[] {
  const mock = vi.mocked(fn as (...args: unknown[]) => unknown)
  expect(mock.mock.calls.length).toBeGreaterThan(0)
  return mock.mock.calls[mock.mock.calls.length - 1]
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  currentUser = user
  vi.mocked(client.defectsApi.list).mockResolvedValue(envelope(ALL) as never)
})

afterEach(cleanup)

describe('finding a defect', () => {
  it('asks the server again when the status filter changes', async () => {
    renderDefects()
    await screen.findByText(flicker.title)

    fireEvent.change(screen.getByTitle('Filter by status'), { target: { value: 'Triaged' } })

    // Status is a server-side filter, so the query has to be re-issued.
    await waitFor(() =>
      expect(lastCall(client.defectsApi.list)).toEqual([project.id, { status: 'Triaged' }]),
    )
  })

  it('asks the server again when the severity filter changes', async () => {
    renderDefects()
    await screen.findByText(flicker.title)

    fireEvent.change(screen.getByTitle('Filter by severity'), { target: { value: 'Critical' } })

    await waitFor(() =>
      expect(lastCall(client.defectsApi.list)).toEqual([project.id, { severity: 'Critical' }]),
    )
  })

  it('sends both filters together', async () => {
    renderDefects()
    await screen.findByText(flicker.title)

    fireEvent.change(screen.getByTitle('Filter by status'), { target: { value: 'Open' } })
    fireEvent.change(screen.getByTitle('Filter by severity'), { target: { value: 'High' } })

    await waitFor(() =>
      expect(lastCall(client.defectsApi.list)).toEqual([
        project.id,
        { status: 'Open', severity: 'High' },
      ]),
    )
  })

  it('drops a filter from the query when it is cleared', async () => {
    renderDefects()
    await screen.findByText(flicker.title)

    fireEvent.change(screen.getByTitle('Filter by status'), { target: { value: 'Open' } })
    await waitFor(() =>
      expect(lastCall(client.defectsApi.list)).toEqual([project.id, { status: 'Open' }]),
    )

    // An empty choice must not be sent as status="" - that would match nothing.
    fireEvent.change(screen.getByTitle('Filter by status'), { target: { value: '' } })
    await waitFor(() => expect(lastCall(client.defectsApi.list)).toEqual([project.id, {}]))
  })

  it('searches without asking the server again', async () => {
    renderDefects()
    await screen.findByText(flicker.title)
    const before = vi.mocked(client.defectsApi.list).mock.calls.length

    fireEvent.change(screen.getByTitle(/filter defects in the current list/i), {
      target: { value: 'brownout' },
    })

    await waitFor(() => expect(rows()).toEqual(['VCU-DEF-002']))
    expect(vi.mocked(client.defectsApi.list).mock.calls.length).toBe(before)
  })

  it('searches the identifier and the status as well as the title', async () => {
    renderDefects()
    await screen.findByText(flicker.title)
    const search = screen.getByTitle(/filter defects in the current list/i)

    fireEvent.change(search, { target: { value: 'DEF-003' } })
    await waitFor(() => expect(rows()).toEqual(['VCU-DEF-003']))

    fireEvent.change(search, { target: { value: 'resolved' } })
    await waitFor(() => expect(rows()).toEqual(['VCU-DEF-003']))
  })
})

describe('ordering the defect register', () => {
  it('shows the most recently touched first', async () => {
    renderDefects()
    await screen.findByText(flicker.title)

    expect(rows()).toEqual(['VCU-DEF-002', 'VCU-DEF-001', 'VCU-DEF-003'])
  })

  it('sorts by title ascending, then reverses on a second click', async () => {
    renderDefects()
    await screen.findByText(flicker.title)

    fireEvent.click(screen.getByText('Title').closest('th') as HTMLElement)
    await waitFor(() => expect(rows()).toEqual(['VCU-DEF-001', 'VCU-DEF-002', 'VCU-DEF-003']))

    fireEvent.click(screen.getByText('Title').closest('th') as HTMLElement)
    await waitFor(() => expect(rows()).toEqual(['VCU-DEF-003', 'VCU-DEF-002', 'VCU-DEF-001']))
  })

  it('sorts by identifier, status and severity', async () => {
    renderDefects()
    await screen.findByText(flicker.title)

    fireEvent.click(screen.getByText('ID').closest('th') as HTMLElement)
    await waitFor(() => expect(rows()).toEqual(['VCU-DEF-001', 'VCU-DEF-002', 'VCU-DEF-003']))

    // Open, Resolved, Triaged - alphabetical, not workflow order.
    fireEvent.click(screen.getByText('Status').closest('th') as HTMLElement)
    await waitFor(() => expect(rows()).toEqual(['VCU-DEF-001', 'VCU-DEF-003', 'VCU-DEF-002']))

    // Critical, High, Low.
    fireEvent.click(screen.getByText('Severity').closest('th') as HTMLElement)
    await waitFor(() => expect(rows()).toEqual(['VCU-DEF-002', 'VCU-DEF-001', 'VCU-DEF-003']))
  })
})

describe('the defect rows', () => {
  it('opens the defect that was clicked', async () => {
    renderDefects()
    await screen.findByText(brownout.title)

    fireEvent.click(screen.getByText(brownout.title))

    expect(await screen.findByText('defect detail')).toBeTruthy()
  })

  it('links out to the external issue, and shows a dash without one', async () => {
    renderDefects()
    await screen.findByText(brownout.title)

    const link = screen.getByText('#42').closest('a') as HTMLAnchorElement
    expect(link.href).toBe(brownout.external_issue_url)
    expect(link.rel).toContain('noopener')
    expect(link.target).toBe('_blank')

    // Two of the three defects have no external issue.
    expect(screen.getAllByText('—')).toHaveLength(2)
  })

  it('does not open the defect when the external link is clicked', async () => {
    renderDefects()
    await screen.findByText(brownout.title)

    fireEvent.click(screen.getByText('#42'))

    // The click is stopped at the link, so the row underneath does not navigate.
    expect(screen.queryByText('defect detail')).toBeNull()
  })

  it('says plainly when there are no defects', async () => {
    vi.mocked(client.defectsApi.list).mockResolvedValue(envelope([]) as never)
    renderDefects()

    await waitFor(() => expect(screen.queryByRole('table')).toBeNull())
    expect(screen.queryByText('VCU-DEF-001')).toBeNull()
  })
})

describe('raising a defect', () => {
  async function openForm() {
    renderDefects()
    await screen.findByText(flicker.title)
    fireEvent.click(screen.getByRole('button', { name: /new defect/i }))
    return { title: await screen.findByTitle('Title') }
  }

  it('is not offered to a reader', async () => {
    currentUser = { ...user, role: 'external' }
    renderDefects()
    await screen.findByText(flicker.title)

    expect(screen.queryByRole('button', { name: /new defect/i })).toBeNull()
  })

  it('sends the title, severity and priority', async () => {
    const form = await openForm()
    fireEvent.change(form.title, { target: { value: 'Fan stalls above 60C' } })
    fireEvent.change(screen.getByTitle('Severity'), { target: { value: 'Critical' } })
    fireEvent.change(screen.getByTitle('Priority'), { target: { value: 'High' } })
    fireEvent.click(screen.getByRole('button', { name: /^create defect$/i }))

    await waitFor(() =>
      expect(lastCall(client.defectsApi.create)[0]).toMatchObject({
        project_id: project.id,
        title: 'Fan stalls above 60C',
        severity: 'Critical',
        priority: 'High',
      }),
    )
  })

  it('sends nulls rather than empty strings for what was left blank', async () => {
    const form = await openForm()
    fireEvent.change(form.title, { target: { value: 'Fan stalls above 60C' } })
    fireEvent.click(screen.getByRole('button', { name: /^create defect$/i }))

    await waitFor(() =>
      expect(lastCall(client.defectsApi.create)[0]).toMatchObject({
        description: null,
        external_tracker: null,
        external_repo_full_name: null,
        external_issue_number: null,
        external_issue_url: null,
      }),
    )
  })

  it('links the defect to an external issue when one is given', async () => {
    const form = await openForm()
    fireEvent.change(form.title, { target: { value: 'Fan stalls above 60C' } })
    fireEvent.change(screen.getByTitle('External tracker'), { target: { value: 'github' } })
    fireEvent.change(screen.getByTitle('Repository'), { target: { value: 'embedlabs/vcu' } })
    fireEvent.change(screen.getByTitle('Issue number'), { target: { value: '99' } })
    fireEvent.change(screen.getByTitle('Issue URL'), {
      target: { value: 'https://github.com/embedlabs/vcu/issues/99' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^create defect$/i }))

    await waitFor(() =>
      expect(lastCall(client.defectsApi.create)[0]).toMatchObject({
        external_tracker: 'github',
        external_repo_full_name: 'embedlabs/vcu',
        // The field is typed text; the API wants a number.
        external_issue_number: 99,
        external_issue_url: 'https://github.com/embedlabs/vcu/issues/99',
      }),
    )
  })

  it('shows why the server refused, and keeps the form open', async () => {
    vi.mocked(client.defectsApi.create).mockRejectedValueOnce(
      Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { data: { detail: 'That issue is already linked to another defect' } },
      }),
    )
    const form = await openForm()
    fireEvent.change(form.title, { target: { value: 'Duplicate link' } })
    fireEvent.click(screen.getByRole('button', { name: /^create defect$/i }))

    expect((await screen.findAllByText(/already linked/i)).length).toBeGreaterThan(0)
    expect(screen.getByTitle('Title')).toBeTruthy()
  })

  it('closes the form without raising anything', async () => {
    await openForm()
    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))

    await waitFor(() => expect(screen.queryByTitle('Title')).toBeNull())
    await settle()
    expect(client.defectsApi.create).not.toHaveBeenCalled()
  })
})
