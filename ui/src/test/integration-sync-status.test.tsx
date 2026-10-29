// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import type { User } from '../api/client'
import { createQueryClient } from '../lib/queryClient'
import { integrationSetting, resetApiMocks, user } from './apiFixtures'
import { formatDateTime } from './date-utils'

let currentUser: User = user

vi.mock('../api/client', async (importOriginal) => {
  const { mockApiModule: build } = await import('./apiFixtures')
  return build(await importOriginal<Record<string, unknown>>(), vi)
})

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
const IntegrationSettingsPanel = (await import('../components/IntegrationSettingsPanel')).default

const jiraRow = {
  ...integrationSetting,
  id: 142,
  tracker: 'jira',
  base_url: 'https://acme.atlassian.net',
  account_email: 'bot@acme.test',
  jira_project_key: 'PROJ',
  auto_sync_minutes: 15,
  sync_checked_at: null,
  synced_at: null,
  sync_error: null,
  sync_warning: null,
  sync_created: 0,
  sync_updated: 0,
}

const githubRow = { ...jiraRow, id: 141, tracker: 'github', account_email: null, jira_project_key: null }

function renderPanel() {
  const queryClient = createQueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter>
          <IntegrationSettingsPanel projectId={1} />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

async function statusFor(row: Record<string, unknown>) {
  vi.mocked(client.integrationsApi.listSettings).mockResolvedValue([row] as never)
  renderPanel()
  return screen.findByTestId('sync-status')
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  currentUser = user
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('the automatic sync status of a tracker', () => {
  it('says the sync is off when the server runs none', async () => {
    const status = await statusFor({ ...jiraRow, auto_sync_minutes: 0 })
    expect(status.textContent).toBe('Automatic sync is off on this server.')
  })

  it('asks to enable a disabled integration before naming its last failure', async () => {
    const status = await statusFor({ ...jiraRow, enabled: false, sync_error: 'Jira answered 401' })
    expect(status.textContent).toBe('Enable the integration to sync it automatically.')
  })

  it('names what a Jira integration lacks', async () => {
    const status = await statusFor({ ...jiraRow, account_email: null })
    expect(status.textContent).toBe(
      'Automatic sync needs the site URL, account email, API token and Jira project key.',
    )
  })

  it('asks a GitHub integration for a token', async () => {
    const status = await statusFor({ ...githubRow, has_token: false })
    expect(status.textContent).toBe('Automatic sync needs a token.')
  })

  it('shows the last failure with the time of the attempt', async () => {
    const checked = '2026-10-26T11:45:00Z'
    const status = await statusFor({
      ...jiraRow,
      sync_checked_at: checked,
      synced_at: '2026-10-26T11:00:00Z',
      sync_error: 'Jira answered 401 to the search.',
      sync_warning: 'ignored',
    })
    expect(status.textContent).toBe(
      `Last automatic sync failed ${formatDateTime(checked)}: Jira answered 401 to the search.`,
    )
    expect(status.querySelector('.text-destructive')).toBeTruthy()
  })

  it('says a new integration has not synced yet', async () => {
    const status = await statusFor({ ...jiraRow, sync_warning: 'ignored' })
    expect(status.textContent).toBe('Syncs automatically every 15 minutes. Not synced yet.')
  })

  it('shows the last sync with its counts and the repositories it skipped', async () => {
    const synced = '2026-10-26T11:30:00Z'
    const status = await statusFor({
      ...githubRow,
      synced_at: '2026-10-26T09:00:00Z',
      sync_checked_at: synced,
      sync_created: 2,
      sync_updated: 3,
      sync_warning: 'GitHub refused the issue list of acme/gone',
    })
    expect(status.children[0].textContent).toBe(
      `Syncs automatically every 15 minutes. Last sync ${formatDateTime(synced)}: 2 created, 3 updated.`,
    )
    expect(status.children[1].textContent).toBe('Skipped: GitHub refused the issue list of acme/gone')
    expect(status.children[1].className).toContain('text-amber-700')
  })

  it('shows no sync line to someone who is not an administrator', async () => {
    currentUser = { ...user, role: 'maintainer' }
    vi.mocked(client.integrationsApi.listSettings).mockResolvedValue([jiraRow] as never)
    renderPanel()
    expect(await screen.findByText(/jira is configured for this project/i)).toBeTruthy()
    expect(screen.queryByTestId('sync-status')).toBeNull()
  })

  it('keeps unsaved input when a refresh brings a new sync result', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.mocked(client.integrationsApi.listSettings).mockResolvedValue([jiraRow] as never)
    renderPanel()
    await screen.findByTestId('sync-status')
    const secret = screen.getByPlaceholderText('Shared secret for inbound webhooks') as HTMLInputElement
    fireEvent.change(secret, { target: { value: 'typed-secret' } })
    vi.mocked(client.integrationsApi.listSettings).mockResolvedValue([
      { ...jiraRow, sync_checked_at: '2026-10-26T12:00:00Z', synced_at: '2026-10-26T12:00:00Z' },
    ] as never)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000)
    })
    expect(await screen.findByText(/Last sync/)).toBeTruthy()
    expect(secret.value).toBe('typed-secret')
  })

  it('refreshes the settings every minute', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.mocked(client.integrationsApi.listSettings).mockResolvedValue([jiraRow] as never)
    renderPanel()
    await screen.findByTestId('sync-status')
    const before = vi.mocked(client.integrationsApi.listSettings).mock.calls.length
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000)
    })
    expect(vi.mocked(client.integrationsApi.listSettings).mock.calls).toHaveLength(before + 1)
  })
})
