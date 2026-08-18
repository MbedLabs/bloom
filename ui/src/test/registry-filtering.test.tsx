// @vitest-environment jsdom
/**
 * The document registry's filtering, sorting and paging.
 *
 * All of it is the server's work now - the screen used to fetch a whole project
 * and narrow it in the browser, which at a thousand documents meant paying for
 * a thousand rows to show thirty. So what these cases hold the page to is the
 * question it asks: `docsApi.list` here is a small stand-in server that knows
 * only the parameters it was sent. A filter the page forgets to send is a
 * filter the stand-in cannot apply, and the expected rows do not come back.
 * That is the failure the old local-filtering tests could not produce, because
 * a page that ignored a parameter still filtered correctly on its own.
 *
 * Whether the *real* server reads those parameters correctly is a different
 * question, asked against real SQL in tests/test_docs_facade_registry_http.py.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { clearRegistrySortSession } from '../lib/docRegistryParams'
import { docShell, resetApiMocks, user } from './apiFixtures'

vi.mock('../api/client', async (importOriginal) => {
  const { mockApiModule: build } = await import('./apiFixtures')
  return build(await importOriginal<Record<string, unknown>>(), vi)
})

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user,
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

const client = await import('../api/client')
// `client` above is a value binding, so it cannot be used in a type
// position; the shapes this file annotates with come from here.
import type { DocListParams, DocShell } from '../api/client'
const Documents = (await import('../pages/Documents')).default

const reviewer = { ...user, id: 7, full_name: 'Grace Hopper', role: 'maintainer' as const }

/**
 * Four documents that disagree on every axis the registry filters by, so a
 * filter that matches everything and one that matches nothing are told apart
 * by which identifiers come back.
 */
const alpha: DocShell = {
  ...docShell,
  id: 101,
  doc_id: 'VCU-REQ-001',
  doc_type: 'REQ',
  title: 'Alpha boot timing',
  status: 'Approved',
  priority: 'High',
  req_type: 'Functional',
  req_origin: 'Customer',
  reviewer_id: reviewer.id,
  incoming_links: 1,
  outgoing_links: 0,
  suspect_links: 1,
  created_at: '2026-01-10T09:00:00Z',
  updated_at: '2026-03-01T09:00:00Z',
}
const bravo: DocShell = {
  ...docShell,
  id: 102,
  doc_id: 'VCU-REQ-002',
  doc_type: 'REQ',
  title: 'Bravo shutdown sequence',
  status: 'Draft',
  priority: 'Low',
  req_type: 'Safety',
  req_origin: 'Regulatory',
  reviewer_id: null,
  incoming_links: 0,
  outgoing_links: 0,
  suspect_links: 0,
  created_at: '2026-02-10T09:00:00Z',
  updated_at: '2026-02-20T09:00:00Z',
}
const charlie: DocShell = {
  ...docShell,
  id: 103,
  doc_id: 'VCU-TC-001',
  doc_type: 'TC',
  title: 'Charlie cold start',
  status: 'Review',
  priority: 'Medium',
  req_type: null,
  req_origin: null,
  reviewer_id: null,
  // Linked both ways but with nothing suspect, which is what tells the
  // incoming filter apart from the suspect one.
  incoming_links: 1,
  outgoing_links: 3,
  suspect_links: 0,
  created_at: '2026-03-10T09:00:00Z',
  updated_at: '2026-04-01T09:00:00Z',
}
const delta: DocShell = {
  ...docShell,
  id: 104,
  doc_id: 'VCU-TC-002',
  doc_type: 'TC',
  title: 'Delta brownout',
  status: 'Draft',
  priority: 'High',
  req_type: null,
  req_origin: null,
  reviewer_id: reviewer.id,
  incoming_links: 2,
  outgoing_links: 2,
  suspect_links: 2,
  created_at: '2026-04-10T09:00:00Z',
  updated_at: '2026-01-05T09:00:00Z',
}

type Shell = DocShell
const ALL: Shell[] = [alpha, bravo, charlie, delta]

const TYPE_LABELS: Record<string, string> = { REQ: 'Requirement', TC: 'Test Case' }
const NAMES = new Map([
  [user.id, user.full_name],
  [reviewer.id, reviewer.full_name],
])

/**
 * A stand-in for the registry endpoint: it sees only what the page sent it.
 *
 * Kept deliberately literal - one branch per parameter, in the order the real
 * endpoint applies them - so that reading it tells you what the page is
 * expected to send, and nothing else.
 */
function fakeRegistry(rows: Shell[]) {
  return (_prefix: string, params: DocListParams = {}) => {
    let result = [...rows]

    if (params.type?.length) result = result.filter((d) => params.type!.includes(d.doc_type))
    if (params.status?.length) result = result.filter((d) => params.status!.includes(d.status))
    if (params.priority) result = result.filter((d) => (d.priority ?? '') === params.priority)

    if (params.reviewer === 'assigned') result = result.filter((d) => d.reviewer_id !== null)
    else if (params.reviewer === 'unassigned') result = result.filter((d) => d.reviewer_id === null)
    else if (params.reviewer) {
      result = result.filter((d) => String(d.reviewer_id ?? '') === params.reviewer)
    }

    const links = params.links
    if (links === 'linked') result = result.filter((d) => d.incoming_links + d.outgoing_links > 0)
    else if (links === 'unlinked') result = result.filter((d) => d.incoming_links + d.outgoing_links === 0)
    else if (links === 'incoming') result = result.filter((d) => d.incoming_links > 0)
    else if (links === 'outgoing') result = result.filter((d) => d.outgoing_links > 0)
    else if (links === 'suspect') result = result.filter((d) => d.suspect_links > 0)
    else if (links === 'clean') result = result.filter((d) => d.suspect_links === 0)

    const inRange = (value: string, from?: string, to?: string) => {
      const at = new Date(value).getTime()
      if (from && at < new Date(`${from}T00:00:00Z`).getTime()) return false
      if (to && at > new Date(`${to}T23:59:59Z`).getTime()) return false
      return true
    }
    result = result.filter(
      (d) =>
        inRange(d.created_at, params.createdFrom, params.createdTo) &&
        inRange(d.updated_at, params.updatedFrom, params.updatedTo),
    )

    if (params.q) {
      const needle = params.q.toLowerCase()
      result = result.filter((d) =>
        [
          d.doc_id,
          d.title,
          d.doc_type,
          TYPE_LABELS[d.doc_type] ?? d.doc_type,
          d.status,
          d.priority ?? '',
          d.req_type ?? '',
          d.req_origin ?? '',
          d.reviewer_id ? NAMES.get(d.reviewer_id) ?? '' : '',
          d.created_at.slice(0, 10),
          d.updated_at.slice(0, 10),
        ]
          .join(' ')
          .toLowerCase()
          .includes(needle),
      )
    }

    const key = params.sort ?? 'updated_at'
    const factor = (params.dir ?? 'desc') === 'desc' ? -1 : 1
    result.sort((a, b) => {
      const pick = (d: Shell): string => {
        if (key === 'reviewer') return d.reviewer_id ? NAMES.get(d.reviewer_id) ?? '' : ''
        return String((d as unknown as Record<string, unknown>)[key] ?? '')
      }
      const cmp = key === 'updated_at' || key === 'created_at'
        ? new Date(pick(a)).getTime() - new Date(pick(b)).getTime()
        : pick(a).toLowerCase().localeCompare(pick(b).toLowerCase())
      // The real endpoint breaks ties the same way, so a page boundary cannot
      // show the same row twice.
      return cmp !== 0 ? cmp * factor : a.doc_type.localeCompare(b.doc_type) || a.id - b.id
    })

    const total = result.length
    const skip = params.skip ?? 0
    const limit = params.limit
    const items = limit === undefined ? result : result.slice(skip, skip + limit)
    return Promise.resolve({ items, total, skip, limit: limit ?? total })
  }
}

function renderRegistry(url = '/projects/VCU/docs') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={[url]}>
          <Routes>
            <Route path="/projects/:prefix/docs" element={<Documents />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** The identifiers currently in the table, top to bottom. */
function rows(): string[] {
  const table = screen.queryByRole('table')
  if (!table) return []
  return within(table)
    .getAllByRole('row')
    .slice(1)
    .map((row) => /VCU-[A-Z]+-\d+/.exec(row.textContent ?? '')?.[0] ?? '')
}

async function openFilters() {
  fireEvent.click(screen.getAllByRole('button', { name: /^Filters/ })[0])
  await screen.findByText('Priority / Severity')
}

/** The parameters of the most recent registry request. */
function lastQuery(): DocListParams {
  const calls = vi.mocked(client.docsApi.list).mock.calls
  return (calls[calls.length - 1]?.[1] ?? {}) as DocListParams
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  vi.mocked(client.docsApi.list).mockImplementation(fakeRegistry(ALL) as never)
  vi.mocked(client.usersApi.list).mockResolvedValue([user, reviewer] as never)
  window.localStorage.clear()
  // The registry remembers a sort per project for the length of the session,
  // in a module-level map that outlives a render. Without this the sort one
  // case chooses is still in force in the next one.
  clearRegistrySortSession('VCU')
})

afterEach(cleanup)

describe('narrowing the registry', () => {
  it('shows every document to begin with', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')

    expect(rows()).toHaveLength(4)
  })

  it('asks for one page rather than the whole project', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')

    // An unbounded request is the bug this screen was fixed for: it reads one
    // page and takes the count from the envelope.
    expect(lastQuery().limit).toBe(30)
    expect(lastQuery().skip).toBe(0)
  })

  it('searches the title, the identifier and the kind at once', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    const search = screen.getByPlaceholderText(/^Search name, ID, kind/)

    fireEvent.change(search, { target: { value: 'brownout' } })
    await waitFor(() => expect(rows()).toEqual(['VCU-TC-002']))

    fireEvent.change(search, { target: { value: 'REQ-002' } })
    await waitFor(() => expect(rows()).toEqual(['VCU-REQ-002']))

    // "Test Case" is the label of the TC kind, not a word in any title.
    fireEvent.change(search, { target: { value: 'test case' } })
    await waitFor(() => expect(rows()).toEqual(['VCU-TC-001', 'VCU-TC-002']))
  })

  it('waits for typing to pause before asking again', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    const before = vi.mocked(client.docsApi.list).mock.calls.length
    const search = screen.getByPlaceholderText(/^Search name, ID, kind/)

    for (const value of ['b', 'br', 'bro', 'brow', 'brown', 'brownout']) {
      fireEvent.change(search, { target: { value } })
    }

    await waitFor(() => expect(rows()).toEqual(['VCU-TC-002']))
    // Six keystrokes, one request - five of the six would have been stale
    // before they landed.
    expect(vi.mocked(client.docsApi.list).mock.calls.length - before).toBe(1)
  })

  it('searches by the reviewer’s name, which is not in the row text', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')

    fireEvent.change(screen.getByPlaceholderText(/^Search name, ID, kind/), {
      target: { value: 'grace hopper' },
    })

    await waitFor(() => expect(rows()).toEqual(['VCU-REQ-001', 'VCU-TC-002']))
  })

  it('keeps every document whose status is ticked', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    await openFilters()

    fireEvent.click(screen.getByRole('button', { name: 'Draft' }))
    await waitFor(() => expect(rows()).toEqual(['VCU-REQ-002', 'VCU-TC-002']))

    // Statuses accumulate rather than replace each other.
    fireEvent.click(screen.getByRole('button', { name: 'Review' }))
    await waitFor(() => expect(rows()).toHaveLength(3))
    expect(lastQuery().status).toEqual(['Draft', 'Review'])

    fireEvent.click(screen.getByRole('button', { name: 'Draft' }))
    await waitFor(() => expect(rows()).toEqual(['VCU-TC-001']))
  })

  it('narrows to one priority', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    await openFilters()

    fireEvent.change(screen.getByLabelText(/Priority/i), { target: { value: 'High' } })

    await waitFor(() => expect(rows()).toEqual(['VCU-REQ-001', 'VCU-TC-002']))
  })

  it('separates assigned from unassigned, and picks out one reviewer', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    await openFilters()
    const picker = screen.getByLabelText(/Reviewer/i)

    fireEvent.change(picker, { target: { value: 'unassigned' } })
    await waitFor(() => expect(rows()).toEqual(['VCU-TC-001', 'VCU-REQ-002']))

    fireEvent.change(picker, { target: { value: 'assigned' } })
    await waitFor(() => expect(rows()).toEqual(['VCU-REQ-001', 'VCU-TC-002']))

    fireEvent.change(picker, { target: { value: String(reviewer.id) } })
    await waitFor(() => expect(rows()).toEqual(['VCU-REQ-001', 'VCU-TC-002']))

    // A reviewer with nothing assigned empties the table rather than being
    // ignored.
    fireEvent.change(picker, { target: { value: String(user.id) } })
    await waitFor(() => expect(rows()).toHaveLength(0))
  })

  it('tells the six link states apart', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    await openFilters()
    const picker = screen.getByLabelText(/Links/i)

    const cases: [string, string[]][] = [
      ['linked', ['VCU-TC-001', 'VCU-REQ-001', 'VCU-TC-002']],
      ['unlinked', ['VCU-REQ-002']],
      ['incoming', ['VCU-TC-001', 'VCU-REQ-001', 'VCU-TC-002']],
      ['outgoing', ['VCU-TC-001', 'VCU-TC-002']],
      ['suspect', ['VCU-REQ-001', 'VCU-TC-002']],
      ['clean', ['VCU-TC-001', 'VCU-REQ-002']],
    ]
    for (const [value, expected] of cases) {
      fireEvent.change(picker, { target: { value } })
      await waitFor(() => expect(rows()).toEqual(expected))
    }
  })

  it('bounds the created range at both ends', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    await openFilters()

    fireEvent.change(screen.getByLabelText('Created From'), { target: { value: '2026-03-01' } })
    await waitFor(() => expect(rows()).toEqual(['VCU-TC-001', 'VCU-TC-002']))

    fireEvent.change(screen.getByLabelText('Created To'), { target: { value: '2026-03-31' } })
    await waitFor(() => expect(rows()).toEqual(['VCU-TC-001']))
  })

  it('bounds the updated range independently of the created one', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    await openFilters()

    // Delta was created last but updated first, so the two ranges must not be
    // reading the same field.
    fireEvent.change(screen.getByLabelText('Updated To'), { target: { value: '2026-01-31' } })
    await waitFor(() => expect(rows()).toEqual(['VCU-TC-002']))

    fireEvent.change(screen.getByLabelText('Updated To'), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText('Updated From'), { target: { value: '2026-03-15' } })
    await waitFor(() => expect(rows()).toEqual(['VCU-TC-001']))
  })

  it('applies every filter at once rather than the last one set', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    await openFilters()

    fireEvent.click(screen.getByRole('button', { name: 'Draft' }))
    fireEvent.change(screen.getByLabelText(/Priority/i), { target: { value: 'High' } })

    // Draft alone keeps two; High alone keeps two; together only Delta.
    await waitFor(() => expect(rows()).toEqual(['VCU-TC-002']))
  })

  it('says a filter matched nothing instead of showing an empty table', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    await openFilters()

    fireEvent.change(screen.getByLabelText(/Priority/i), { target: { value: 'Critical' } })

    expect(await screen.findByText(/no documents found/i)).toBeTruthy()
    expect(screen.getByText(/try a different filter combination/i)).toBeTruthy()
  })

  it('distinguishes an empty project from an over-filtered one', async () => {
    vi.mocked(client.docsApi.list).mockImplementation(fakeRegistry([]) as never)
    renderRegistry()

    expect(await screen.findByText(/no documents yet/i)).toBeTruthy()
    expect(screen.queryByText(/try a different filter combination/i)).toBeNull()
  })

  it('summarises what is filtering the view, and clears it all at once', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    await openFilters()

    fireEvent.change(screen.getByLabelText(/Priority/i), { target: { value: 'High' } })
    fireEvent.click(screen.getByRole('button', { name: 'Draft' }))

    expect(await screen.findByText('Priority: High')).toBeTruthy()
    expect(screen.getByText('Status: Draft')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /clear all/i }))
    await waitFor(() => expect(rows()).toHaveLength(4))
    expect(screen.queryByText('Priority: High')).toBeNull()
  })

  it('names the reviewer in the summary rather than their id', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')
    await openFilters()

    fireEvent.change(screen.getByLabelText(/Reviewer/i), { target: { value: String(reviewer.id) } })

    expect(await screen.findByText(`Reviewer: ${reviewer.full_name}`)).toBeTruthy()
  })
})

describe('ordering the registry', () => {
  it('shows the most recently touched document first', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')

    // The registry opens on updated_at descending, so the order is Charlie,
    // Alpha, Bravo, Delta rather than the order the API returned.
    expect(rows()).toEqual(['VCU-TC-001', 'VCU-REQ-001', 'VCU-REQ-002', 'VCU-TC-002'])
    expect(lastQuery()).toMatchObject({ sort: 'updated_at', dir: 'desc' })
  })

  it('reverses the order when the same header is clicked twice', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')

    // Text columns start ascending.
    fireEvent.click(screen.getByText('ID').closest('th') as HTMLElement)
    await waitFor(() =>
      expect(rows()).toEqual(['VCU-REQ-001', 'VCU-REQ-002', 'VCU-TC-001', 'VCU-TC-002']),
    )

    fireEvent.click(screen.getByText('ID').closest('th') as HTMLElement)
    await waitFor(() =>
      expect(rows()).toEqual(['VCU-TC-002', 'VCU-TC-001', 'VCU-REQ-002', 'VCU-REQ-001']),
    )
  })

  it('sorts dates newest first and text A to Z', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')

    fireEvent.click(screen.getByText('Created').closest('th') as HTMLElement)
    await waitFor(() =>
      expect(rows()).toEqual(['VCU-TC-002', 'VCU-TC-001', 'VCU-REQ-002', 'VCU-REQ-001']),
    )

    fireEvent.click(screen.getByText('Name / Title').closest('th') as HTMLElement)
    await waitFor(() =>
      expect(rows()).toEqual(['VCU-REQ-001', 'VCU-REQ-002', 'VCU-TC-001', 'VCU-TC-002']),
    )
  })

  it('sorts by status, priority and kind', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')

    fireEvent.click(screen.getByText('Status').closest('th') as HTMLElement)
    await waitFor(() => expect(rows()[0]).toBe('VCU-REQ-001'))

    fireEvent.click(screen.getByText('Priority').closest('th') as HTMLElement)
    // High, High, Low, Medium - ascending, alphabetically.
    await waitFor(() => expect(rows().slice(0, 2).sort()).toEqual(['VCU-REQ-001', 'VCU-TC-002']))

    fireEvent.click(screen.getByText('Kind').closest('th') as HTMLElement)
    await waitFor(() => expect(rows().slice(0, 2).sort()).toEqual(['VCU-REQ-001', 'VCU-REQ-002']))
  })

  it('sorts by reviewer name, putting the unassigned together', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')

    fireEvent.click(screen.getByText('Reviewer').closest('th') as HTMLElement)

    // Ascending by name: the two with no reviewer sort as the empty string.
    await waitFor(() => expect(rows().slice(0, 2).sort()).toEqual(['VCU-REQ-002', 'VCU-TC-001']))
  })

  it('takes the sort from the drop-down as well as the headers', async () => {
    renderRegistry()
    await screen.findByText('Alpha boot timing')

    const picker = screen
      .getAllByRole('combobox')
      .find((box) => /Sort by/.test(box.textContent ?? '')) as HTMLSelectElement
    fireEvent.change(picker, { target: { value: 'updated_at' } })

    // Updated descending: Charlie, Alpha, Bravo, Delta.
    await waitFor(() =>
      expect(rows()).toEqual(['VCU-TC-001', 'VCU-REQ-001', 'VCU-REQ-002', 'VCU-TC-002']),
    )
  })

  it('reads a sort out of the URL so a sorted view can be shared', async () => {
    renderRegistry('/projects/VCU/docs?sort=title&dir=desc')
    await screen.findByText('Alpha boot timing')

    await waitFor(() =>
      expect(rows()).toEqual(['VCU-TC-002', 'VCU-TC-001', 'VCU-REQ-002', 'VCU-REQ-001']),
    )
  })

  it('ignores a sort field the registry does not have', async () => {
    renderRegistry('/projects/VCU/docs?sort=whatever&dir=asc')
    await screen.findByText('Alpha boot timing')

    // Falling back to the default beats asking the server to sort by a column
    // it will reject with a 422.
    expect(lastQuery().sort).toBe('updated_at')
    await waitFor(() =>
      expect(rows()).toEqual(['VCU-TC-001', 'VCU-REQ-001', 'VCU-REQ-002', 'VCU-TC-002']),
    )
  })
})

describe('paging the registry', () => {
  const many: Shell[] = Array.from({ length: 25 }, (_, index) => ({
    ...alpha,
    id: 200 + index,
    doc_id: `VCU-REQ-${String(index + 1).padStart(3, '0')}`,
    title: `Requirement ${index + 1}`,
    // One shared timestamp, so the default sort has nothing but the tiebreaker
    // to go on - which is what a page boundary actually leans on.
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }))

  beforeEach(() => {
    vi.mocked(client.docsApi.list).mockImplementation(fakeRegistry(many) as never)
  })

  it('counts what is on screen out of the whole set', async () => {
    renderRegistry()
    await screen.findByText('Requirement 1')

    // 25 documents, 30 to a page: the count comes from the envelope's `total`,
    // not from the length of what arrived.
    expect(screen.getByText(/1.*25 of 25/)).toBeTruthy()
  })

  it('splits the set when the page size is reduced', async () => {
    renderRegistry()
    await screen.findByText('Requirement 1')

    fireEvent.change(screen.getByDisplayValue('30'), { target: { value: '10' } })

    await waitFor(() => expect(rows()).toHaveLength(10))
    expect(screen.getByText('1 / 3')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Prev' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('asks the server for the next page instead of slicing what it has', async () => {
    renderRegistry()
    await screen.findByText('Requirement 1')
    fireEvent.change(screen.getByDisplayValue('30'), { target: { value: '10' } })
    await waitFor(() => expect(rows()).toHaveLength(10))

    // The page counter moves at once - the rows follow when the request lands,
    // because the previous page is held on screen rather than flashing empty.
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(rows()[0]).toBe('VCU-REQ-011'))
    expect(screen.getByText('2 / 3')).toBeTruthy()
    expect(lastQuery()).toMatchObject({ skip: 10, limit: 10 })

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    // The last page holds the remainder, and there is nowhere further to go.
    await waitFor(() => expect(rows()).toHaveLength(5))
    expect(screen.getByText('3 / 3')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Next' }) as HTMLButtonElement).disabled).toBe(true)

    fireEvent.click(screen.getByRole('button', { name: 'Prev' }))
    await waitFor(() => expect(rows()[0]).toBe('VCU-REQ-011'))
  })

  it('shows no row twice while walking the pages', async () => {
    renderRegistry()
    await screen.findByText('Requirement 1')
    fireEvent.change(screen.getByDisplayValue('30'), { target: { value: '10' } })
    await waitFor(() => expect(rows()).toHaveLength(10))

    const seen: string[] = [...rows()]
    for (const first of ['VCU-REQ-011', 'VCU-REQ-021']) {
      fireEvent.click(screen.getByRole('button', { name: 'Next' }))
      await waitFor(() => expect(rows()[0]).toBe(first))
      seen.push(...rows())
    }

    // Every document sorts on the same timestamp here, so without a stable
    // tiebreaker the server is free to return one of them on two pages.
    expect(new Set(seen).size).toBe(25)
  })

  it('returns to the first page when a filter changes the set', async () => {
    renderRegistry()
    await screen.findByText('Requirement 1')
    fireEvent.change(screen.getByDisplayValue('30'), { target: { value: '10' } })
    await waitFor(() => expect(rows()).toHaveLength(10))
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(screen.getByText('2 / 3')).toBeTruthy())

    fireEvent.change(screen.getByPlaceholderText(/^Search name, ID, kind/), {
      target: { value: 'Requirement 1' },
    })

    // "Requirement 1" also matches 10 to 19, so eleven rows survive - but the
    // view has to be back on the first page, not on a page two that no longer
    // has ten rows above it.
    await waitFor(() => expect(screen.getByText('1 / 2')).toBeTruthy())
    expect(rows()[0]).toBe('VCU-REQ-001')
  })
})
