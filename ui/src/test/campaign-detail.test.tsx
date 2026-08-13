// @vitest-environment jsdom
/**
 * One campaign in detail: its scope, its Bud run, and editing it.
 *
 * A campaign's body is its scope - the suites it was built from, each holding
 * the test cases resolved at creation time, plus anything added ad hoc. None
 * of that was covered, because the fixture the tests ran against carried no
 * scopes at all. These drive the real thing: expanding a suite, reading a
 * result off an item, and the edit and delete paths that change or destroy it.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { settle } from './settle'

import { ToastProvider } from '../components/Toast'
import {
  campaignDetail,
  campaignItem,
  resetApiMocks,
  testCase,
  testSuite,
  user,
} from './apiFixtures'

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
const CampaignDetail = (await import('../pages/CampaignDetail')).default

const passed = {
  ...campaignItem,
  id: 61,
  status: 'Executed',
  result: 'Passed',
  test_case: { ...testCase, tc_id: 'VCU-TC-001', title: 'Cold boot timing' },
}
const failed = {
  ...campaignItem,
  id: 62,
  test_case_id: 22,
  status: 'Executed',
  result: 'Failed',
  test_case: { ...testCase, id: 22, tc_id: 'VCU-TC-002', title: 'Brownout recovery' },
}
/** Scoped but never resolved to a test case, which the row has to survive. */
const unresolved = {
  ...campaignItem,
  id: 63,
  test_case_id: 99,
  status: 'Pending',
  result: null,
  executed_at: null,
  test_case: null,
}

const secondSuite = { ...testSuite, id: 42, suite_id: 'VCU-TS-002', name: 'Regression suite' }

const withScopes = {
  ...campaignDetail,
  suite_scopes: [
    { suite: testSuite, items: [passed, failed] },
    { suite: secondSuite, items: [] },
  ],
  ad_hoc_items: [unresolved],
}

function renderCampaign() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/projects/VCU/campaigns/31']}>
          <Routes>
            <Route path="/projects/:prefix/campaigns/:campaignId" element={<CampaignDetail />} />
            <Route path="/projects/:prefix/suites/:suiteId" element={<div>suite detail</div>} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** The arguments of the most recent call to a mocked endpoint. */
function lastCall(fn: unknown): unknown[] {
  const mock = vi.mocked(fn as (...args: unknown[]) => unknown)
  expect(mock.mock.calls.length).toBeGreaterThan(0)
  return mock.mock.calls[mock.mock.calls.length - 1]
}

/** The expandable header of a suite in the scope list. */
function suiteHeader(name: string): HTMLElement {
  return screen.getByText(name).closest('button') as HTMLElement
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  currentUser = user
  vi.mocked(client.campaignsApi.get).mockResolvedValue(withScopes as never)
})

afterEach(cleanup)

describe('the scope of a campaign', () => {
  it('counts the suites it was built from', async () => {
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    // "Suites" is both a stat tile and the section heading.
    expect(screen.getByRole('heading', { name: 'Suites' })).toBeTruthy()
    expect(screen.getByText(testSuite.name)).toBeTruthy()
    expect(screen.getByText(secondSuite.name)).toBeTruthy()
  })

  it('shows how many test cases each suite contributed', async () => {
    renderCampaign()
    await screen.findByText(testSuite.name)

    expect(within(suiteHeader(testSuite.name)).getByText('2 TCs')).toBeTruthy()
    // One test case would be "1 TC", and none is "0 TCs".
    expect(within(suiteHeader(secondSuite.name)).getByText('0 TCs')).toBeTruthy()
  })

  it('keeps the test cases hidden until a suite is expanded', async () => {
    renderCampaign()
    await screen.findByText(testSuite.name)

    expect(screen.queryByText('Cold boot timing')).toBeNull()

    fireEvent.click(suiteHeader(testSuite.name))
    expect(await screen.findByText('Cold boot timing')).toBeTruthy()
    expect(screen.getByText('Brownout recovery')).toBeTruthy()
  })

  it('collapses again on a second click', async () => {
    renderCampaign()
    await screen.findByText(testSuite.name)

    fireEvent.click(suiteHeader(testSuite.name))
    await screen.findByText('Cold boot timing')
    fireEvent.click(suiteHeader(testSuite.name))

    await waitFor(() => expect(screen.queryByText('Cold boot timing')).toBeNull())
  })

  it('expands each suite independently', async () => {
    renderCampaign()
    await screen.findByText(testSuite.name)

    fireEvent.click(suiteHeader(secondSuite.name))

    // The empty suite says so rather than showing the other suite's cases.
    expect(await screen.findByText(/no test cases resolved for this suite yet/i)).toBeTruthy()
    expect(screen.queryByText('Cold boot timing')).toBeNull()
  })

  it('shows each result against its test case', async () => {
    renderCampaign()
    await screen.findByText(testSuite.name)
    fireEvent.click(suiteHeader(testSuite.name))
    await screen.findByText('Cold boot timing')

    expect(screen.getByText('Passed')).toBeTruthy()
    expect(screen.getByText('Failed')).toBeTruthy()
  })

  it('links each scoped test case to the document it came from', async () => {
    renderCampaign()
    await screen.findByText(testSuite.name)
    fireEvent.click(suiteHeader(testSuite.name))

    const link = (await screen.findByText('VCU-TC-001')).closest('a') as HTMLAnchorElement
    expect(link.getAttribute('href')).toContain('VCU-TC-001')
  })

  it('opens the suite itself without expanding the row', async () => {
    renderCampaign()
    await screen.findByText(testSuite.name)

    fireEvent.click(screen.getAllByTitle('Open suite detail')[0])

    expect(await screen.findByText('suite detail')).toBeTruthy()
  })

  it('keeps ad-hoc test cases apart from the suites', async () => {
    renderCampaign()
    await screen.findByText(testSuite.name)

    const adHoc = screen.getByText('Ad-hoc test cases').closest('button') as HTMLElement
    expect(within(adHoc).getByText('1 TC')).toBeTruthy()

    fireEvent.click(adHoc)
    // The item never resolved to a test case, so it falls back to its id.
    expect(await screen.findByText('TC#99')).toBeTruthy()
  })

  it('shows nothing at all when the campaign has no scope', async () => {
    vi.mocked(client.campaignsApi.get).mockResolvedValue({
      ...campaignDetail,
      suite_scopes: [],
      ad_hoc_items: [],
    } as never)
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    // The stat tile counting suites stays; the scope section itself goes.
    expect(screen.queryByRole('heading', { name: 'Suites' })).toBeNull()
  })

  it('says the suites are missing when only ad-hoc cases remain', async () => {
    vi.mocked(client.campaignsApi.get).mockResolvedValue({
      ...campaignDetail,
      suite_scopes: [],
      ad_hoc_items: [passed],
    } as never)
    renderCampaign()

    expect(await screen.findByText(/no suites linked to this campaign/i)).toBeTruthy()
  })
})

describe('editing a campaign', () => {
  it('opens the form filled from the campaign', async () => {
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))

    expect(((await screen.findByLabelText('Name')) as HTMLInputElement).value).toBe(
      campaignDetail.name,
    )
    expect((screen.getByLabelText('Description') as HTMLTextAreaElement).value).toBe(
      campaignDetail.description,
    )
    expect((screen.getByLabelText('Status') as HTMLSelectElement).value).toBe(
      campaignDetail.status,
    )
  })

  it('saves the name, description and visibility together', async () => {
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    fireEvent.change(await screen.findByLabelText('Name'), { target: { value: 'Final sweep' } })
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Sign-off run' } })
    fireEvent.change(screen.getByLabelText('Visibility'), { target: { value: 'customer' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() =>
      expect(lastCall(client.campaignsApi.update)).toEqual([
        campaignDetail.id,
        {
          name: 'Final sweep',
          description: 'Sign-off run',
          status: campaignDetail.status,
          visibility: 'customer',
        },
      ]),
    )
  })

  it('sends no description rather than an empty one', async () => {
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    fireEvent.change(await screen.findByLabelText('Description'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() =>
      expect(
        (lastCall(client.campaignsApi.update)[1] as { description?: string }).description,
      ).toBeUndefined(),
    )
  })

  it('closes on Escape without saving', async () => {
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    const name = await screen.findByLabelText('Name')
    fireEvent.change(name, { target: { value: 'Abandoned' } })
    fireEvent.keyDown(name, { key: 'Escape' })

    await waitFor(() => expect(screen.queryByLabelText('Name')).toBeNull())
    await settle()
    expect(client.campaignsApi.update).not.toHaveBeenCalled()
  })

  it('closes on the X without saving', async () => {
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    await screen.findByLabelText('Name')
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))

    await waitFor(() => expect(screen.queryByLabelText('Name')).toBeNull())
    await settle()
    expect(client.campaignsApi.update).not.toHaveBeenCalled()
  })

  it('re-fills the form from the campaign when it is reopened', async () => {
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    fireEvent.change(await screen.findByLabelText('Name'), { target: { value: 'Abandoned' } })
    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))
    await waitFor(() => expect(screen.queryByLabelText('Name')).toBeNull())

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    expect(((await screen.findByLabelText('Name')) as HTMLInputElement).value).toBe(
      campaignDetail.name,
    )
  })
})

describe('deleting a campaign', () => {
  it('backs out of the confirmation', async () => {
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
    expect(await screen.findByText('Delete Campaign?')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }))

    await waitFor(() => expect(screen.queryByText('Delete Campaign?')).toBeNull())
    await settle()
    expect(client.campaignsApi.delete).not.toHaveBeenCalled()
  })

  it('warns that the scope goes with it', async () => {
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))

    expect(await screen.findByText(/all campaign test cases and scopes will be removed/i))
      .toBeTruthy()
  })

  it('reopens the campaign when the deletion fails', async () => {
    vi.mocked(client.campaignsApi.delete).mockRejectedValueOnce(
      Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { data: { detail: 'A Bud run still references this campaign' } },
      }),
    )
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
    const confirms = await screen.findAllByRole('button', { name: /^delete$/i })
    fireEvent.click(confirms[confirms.length - 1])

    // The dialog closes so the campaign is readable again, and the reason is
    // reported rather than swallowed.
    await waitFor(() => expect(screen.queryByText('Delete Campaign?')).toBeNull())
    expect(await screen.findByText(/still references this campaign/i)).toBeTruthy()
  })
})

describe('what a reader may do', () => {
  it('is offered neither edit nor delete', async () => {
    currentUser = { ...user, role: 'external' }
    renderCampaign()
    await screen.findByText(campaignDetail.name)

    expect(screen.queryByRole('button', { name: /edit/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /^delete$/i })).toBeNull()
    // The scope is still readable.
    expect(screen.getByText(testSuite.name)).toBeTruthy()
  })
})

describe('a campaign that is not there', () => {
  it('says so rather than rendering an empty page', async () => {
    vi.mocked(client.campaignsApi.get).mockRejectedValueOnce(new Error('404'))
    renderCampaign()

    expect(await screen.findByText('Campaign Not Found')).toBeTruthy()
  })
})
