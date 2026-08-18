// @vitest-environment jsdom
/**
 * Test campaigns and the suites they are scoped from.
 *
 * A campaign copies its items from the suites picked at creation time, so the
 * order matters: a suite has to exist first, and a campaign with no suite
 * behind it would have nothing to run. The page carries both creation forms,
 * a search, a status filter and a sort with its own direction toggle - most of
 * which had no coverage, including the rule that stops an empty campaign.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { campaign, project, resetApiMocks, testCase, testSuite, user } from './apiFixtures'
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
const TestCampaigns = (await import('../pages/TestCampaigns')).default

/** Three campaigns that disagree on name, status and when they were touched. */
const running = {
  ...campaign,
  id: 31,
  campaign_id: 'VCU-CMP-001',
  name: 'Alpha regression',
  description: 'Full regression before release.',
  status: 'In Progress',
  updated_at: '2026-03-01T09:00:00Z',
}
const planned = {
  ...campaign,
  id: 32,
  campaign_id: 'VCU-CMP-002',
  name: 'Bravo smoke',
  description: 'Quick pass on every build.',
  status: 'Planned',
  updated_at: '2026-04-01T09:00:00Z',
}
const done = {
  ...campaign,
  id: 33,
  campaign_id: 'VCU-CMP-003',
  name: 'Charlie soak',
  description: null,
  status: 'Completed',
  updated_at: '2026-01-05T09:00:00Z',
}

const secondSuite = {
  ...testSuite,
  id: 42,
  suite_id: 'VCU-TS-002',
  name: 'Regression suite',
  total_items: 12,
}

function envelope(items: unknown[]) {
  return { items, total: items.length, skip: 0, limit: 50 }
}

function renderCampaigns() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/projects/VCU/campaigns']}>
          <Routes>
            <Route path="/projects/:prefix/campaigns" element={<TestCampaigns />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** The campaign names on screen, in the order they are shown. */
function cardNames(): string[] {
  return screen
    .queryAllByRole('link')
    .map((node) => node.querySelector('h3')?.textContent ?? '')
    .filter(Boolean)
}

/** The arguments of the most recent call to a mocked endpoint. */
function lastCall(fn: unknown): unknown[] {
  const mock = vi.mocked(fn as (...args: unknown[]) => unknown)
  expect(mock.mock.calls.length).toBeGreaterThan(0)
  return mock.mock.calls[mock.mock.calls.length - 1]
}

/** An axios-shaped rejection carrying the server's message. */
function apiError(detail: string) {
  return Object.assign(new Error('Request failed'), {
    isAxiosError: true,
    response: { data: { detail } },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  currentUser = user
  vi.mocked(client.campaignsApi.list).mockResolvedValue(envelope([running, planned, done]) as never)
  vi.mocked(client.testSuitesApi.list).mockResolvedValue(
    envelope([testSuite, secondSuite]) as never,
  )
})

afterEach(cleanup)

describe('the campaign list', () => {
  it('searches the name, the description and the status', async () => {
    renderCampaigns()
    await screen.findByText('Alpha regression')
    const search = screen.getByPlaceholderText('Search campaigns...')

    fireEvent.change(search, { target: { value: 'soak' } })
    await waitFor(() => expect(cardNames()).toEqual(['Charlie soak']))

    // The description is searched too, and only Bravo mentions a build.
    fireEvent.change(search, { target: { value: 'every build' } })
    await waitFor(() => expect(cardNames()).toEqual(['Bravo smoke']))

    fireEvent.change(search, { target: { value: 'completed' } })
    await waitFor(() => expect(cardNames()).toEqual(['Charlie soak']))
  })

  it('narrows to a single status', async () => {
    renderCampaigns()
    await screen.findByText('Alpha regression')

    fireEvent.change(screen.getByLabelText('Filter by status'), { target: { value: 'Planned' } })

    await waitFor(() => expect(cardNames()).toEqual(['Bravo smoke']))
  })

  it('says a filter matched nothing rather than showing an empty grid', async () => {
    renderCampaigns()
    await screen.findByText('Alpha regression')

    fireEvent.change(screen.getByPlaceholderText('Search campaigns...'), {
      target: { value: 'nothing matches this' },
    })

    expect(await screen.findByText(/no campaigns match the current filters/i)).toBeTruthy()
    // That is a different message from having no campaigns at all.
    expect(screen.queryByText('No Campaign Scopes')).toBeNull()
  })

  it('orders by when each was last touched, newest first', async () => {
    renderCampaigns()
    await screen.findByText('Alpha regression')

    expect(cardNames()).toEqual(['Bravo smoke', 'Alpha regression', 'Charlie soak'])
  })

  it('sorts by name, and reverses on demand', async () => {
    renderCampaigns()
    await screen.findByText('Alpha regression')

    fireEvent.change(screen.getByLabelText('Sort by'), { target: { value: 'name' } })
    await waitFor(() =>
      expect(cardNames()).toEqual(['Charlie soak', 'Bravo smoke', 'Alpha regression']),
    )

    fireEvent.click(screen.getByTitle('Descending'))
    await waitFor(() =>
      expect(cardNames()).toEqual(['Alpha regression', 'Bravo smoke', 'Charlie soak']),
    )
  })

  it('sorts by status', async () => {
    renderCampaigns()
    await screen.findByText('Alpha regression')

    fireEvent.change(screen.getByLabelText('Sort by'), { target: { value: 'status' } })

    // Descending: Planned, In Progress, Completed.
    await waitFor(() =>
      expect(cardNames()).toEqual(['Bravo smoke', 'Alpha regression', 'Charlie soak']),
    )
  })

  it('offers to create the first campaign when there are none', async () => {
    vi.mocked(client.campaignsApi.list).mockResolvedValue(envelope([]) as never)
    renderCampaigns()

    expect(await screen.findByText('No Campaign Scopes')).toBeTruthy()
    expect(screen.getByRole('button', { name: /create first campaign/i })).toBeTruthy()
    // With nothing to filter, the toolbar is not shown at all.
    expect(screen.queryByPlaceholderText('Search campaigns...')).toBeNull()
  })

  it('shows nothing to create for a reader', async () => {
    currentUser = { ...user, role: 'external' }
    renderCampaigns()
    await screen.findByText('Alpha regression')

    expect(screen.queryByRole('button', { name: /new campaign/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /new suite/i })).toBeNull()
  })
})

describe('the suites of a project', () => {
  it('lists them with their identifiers and sizes', async () => {
    renderCampaigns()
    await screen.findByText('Smoke suite')

    expect(screen.getByText('VCU-TS-001')).toBeTruthy()
    expect(screen.getByText('Regression suite')).toBeTruthy()
    expect(screen.getByText('12 TCs')).toBeTruthy()
    // One test case is singular; the label must not read "1 TCs".
    expect(screen.getByText('1 TC')).toBeTruthy()
  })

  it('says plainly when there are none', async () => {
    vi.mocked(client.testSuitesApi.list).mockResolvedValue(envelope([]) as never)
    renderCampaigns()

    expect(await screen.findByText('No suites defined yet.')).toBeTruthy()
  })

  it('creates a suite from the test cases that were ticked', async () => {
    vi.mocked(client.testCasesApi.list).mockResolvedValue(envelope([testCase]) as never)
    renderCampaigns()
    await screen.findByText('Smoke suite')

    fireEvent.click(screen.getByRole('button', { name: /new suite/i }))
    const heading = await screen.findByText('New Test Suite')
    // The modal holds a name input and a description textarea, and the page
    // behind it has its own search box; scope to the dialog and take the name.
    const modal = heading.closest('div')?.parentElement as HTMLElement

    fireEvent.change(within(modal).getAllByRole('textbox')[0], {
      target: { value: 'Nightly suite' },
    })
    fireEvent.click(await screen.findByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: /^create suite$/i }))

    await waitFor(() =>
      expect(lastCall(client.testSuitesApi.create)[0]).toMatchObject({
        project_id: project.id,
        name: 'Nightly suite',
        test_case_ids: [testCase.id],
        visibility: 'internal',
      }),
    )
  })

  it('does not ask the server for test cases until the form is opened', async () => {
    renderCampaigns()
    await screen.findByText('Smoke suite')

    // The list is only needed inside the new-suite form, and a project can
    // hold a lot of test cases.
    expect(client.testCasesApi.list).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /new suite/i }))
    await waitFor(() => expect(client.testCasesApi.list).toHaveBeenCalled())
  })

  it('says so when the project has no test cases to put in a suite', async () => {
    vi.mocked(client.testCasesApi.list).mockResolvedValue(envelope([]) as never)
    renderCampaigns()
    await screen.findByText('Smoke suite')

    fireEvent.click(screen.getByRole('button', { name: /new suite/i }))

    expect(await screen.findByText('No test cases available.')).toBeTruthy()
  })

  it('closes the suite form without creating anything', async () => {
    renderCampaigns()
    await screen.findByText('Smoke suite')

    fireEvent.click(screen.getByRole('button', { name: /new suite/i }))
    await screen.findByText('New Test Suite')
    fireEvent.click(screen.getAllByRole('button', { name: /^cancel$/i })[0])

    await waitFor(() => expect(screen.queryByText('New Test Suite')).toBeNull())
    await settle()
    expect(client.testSuitesApi.create).not.toHaveBeenCalled()
  })
})

describe('creating a campaign', () => {
  async function openForm() {
    renderCampaigns()
    await screen.findByText('Alpha regression')
    fireEvent.click(screen.getByRole('button', { name: /new campaign/i }))
    return {
      name: await screen.findByPlaceholderText('Campaign name'),
      description: screen.getByPlaceholderText('Optional description...'),
      submit: screen.getByRole('button', {
        name: /^create campaign$/i,
      }) as HTMLButtonElement,
    }
  }

  it('cannot be submitted until a suite is chosen', async () => {
    const form = await openForm()
    fireEvent.change(form.name, { target: { value: 'Unscoped' } })

    // A campaign's items are copied from its suites, so it cannot have none.
    expect(form.submit.disabled).toBe(true)
    fireEvent.submit(form.name.closest('form') as HTMLFormElement)
    expect(await screen.findByText(/select at least one suite/i)).toBeTruthy()
    await settle()
    expect(client.campaignsApi.create).not.toHaveBeenCalled()
  })

  it('scopes from several suites at once', async () => {
    const form = await openForm()
    fireEvent.change(form.name, { target: { value: 'Release sweep' } })

    const boxes = screen.getAllByRole('checkbox')
    fireEvent.click(boxes[0])
    fireEvent.click(boxes[1])
    fireEvent.click(screen.getByRole('button', { name: /^create campaign$/i }))

    await waitFor(() =>
      expect(lastCall(client.campaignsApi.create)[0]).toMatchObject({
        project_id: project.id,
        name: 'Release sweep',
        suite_ids: [testSuite.id, secondSuite.id],
      }),
    )
  })

  it('un-ticks a suite that is clicked twice', async () => {
    const form = await openForm()
    fireEvent.change(form.name, { target: { value: 'Release sweep' } })

    const boxes = screen.getAllByRole('checkbox')
    fireEvent.click(boxes[0])
    fireEvent.click(boxes[1])
    fireEvent.click(boxes[0])
    fireEvent.click(screen.getByRole('button', { name: /^create campaign$/i }))

    await waitFor(() =>
      expect(
        (lastCall(client.campaignsApi.create)[0] as { suite_ids: number[] }).suite_ids,
      ).toEqual([secondSuite.id]),
    )
  })

  it('carries the description and the visibility that were chosen', async () => {
    const form = await openForm()
    fireEvent.change(form.name, { target: { value: 'Customer sweep' } })
    fireEvent.change(form.description, { target: { value: 'Shared with the customer' } })
    fireEvent.change(screen.getAllByRole('combobox').slice(-1)[0], {
      target: { value: 'customer' },
    })
    fireEvent.click(screen.getAllByRole('checkbox')[0])
    fireEvent.click(screen.getByRole('button', { name: /^create campaign$/i }))

    await waitFor(() =>
      expect(lastCall(client.campaignsApi.create)[0]).toMatchObject({
        description: 'Shared with the customer',
        visibility: 'customer',
      }),
    )
  })

  it('warns that a suite is needed before a campaign can exist', async () => {
    vi.mocked(client.testSuitesApi.list).mockResolvedValue(envelope([]) as never)
    renderCampaigns()
    await screen.findByText('Alpha regression')

    fireEvent.click(screen.getByRole('button', { name: /new campaign/i }))

    expect(await screen.findByText(/create a test suite first/i)).toBeTruthy()
    expect(screen.getByText('No suites available.')).toBeTruthy()
  })

  it('shows the server’s refusal without closing the form', async () => {
    vi.mocked(client.campaignsApi.create).mockRejectedValueOnce(
      apiError('A campaign with that name already exists'),
    )
    const form = await openForm()
    fireEvent.change(form.name, { target: { value: 'Alpha regression' } })
    fireEvent.click(screen.getAllByRole('checkbox')[0])
    fireEvent.click(screen.getByRole('button', { name: /^create campaign$/i }))

    expect((await screen.findAllByText(/already exists/i)).length).toBeGreaterThan(0)
    expect(screen.getByPlaceholderText('Campaign name')).toBeTruthy()
  })

  it('forgets a cancelled form, including the suites that were ticked', async () => {
    const form = await openForm()
    fireEvent.change(form.name, { target: { value: 'Abandoned' } })
    fireEvent.click(screen.getAllByRole('checkbox')[0])
    fireEvent.click(screen.getAllByRole('button', { name: /^cancel$/i })[0])

    await waitFor(() => expect(screen.queryByPlaceholderText('Campaign name')).toBeNull())
    fireEvent.click(screen.getByRole('button', { name: /new campaign/i }))

    const reopened = (await screen.findByPlaceholderText('Campaign name')) as HTMLInputElement
    expect(reopened.value).toBe('')
    expect(screen.getByText(/campaign suites \(0 selected\)/i)).toBeTruthy()
    await settle()
    expect(client.campaignsApi.create).not.toHaveBeenCalled()
  })
})
