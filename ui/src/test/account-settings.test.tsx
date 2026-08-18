// @vitest-environment jsdom
/**
 * The settings screen: the account, the theme, the timezone and the
 * credentials Bud submits results with.
 *
 * Most of this page is preferences, but two parts are not: an email change
 * that an administrator has to approve, and a service credential whose token
 * is shown exactly once and never again. The failure paths were the gap - what
 * happens when the current password is wrong, when a token cannot be
 * generated, when a revoke is declined - and those are the paths where an
 * unreported error leaves a user staring at an unchanged screen.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { resetApiMocks, serviceCredential, user } from './apiFixtures'
import { settle } from './settle'

vi.mock('../api/client', async (importOriginal) => {
  const { mockApiModule: build } = await import('./apiFixtures')
  return build(await importOriginal<Record<string, unknown>>(), vi)
})

/** The signed-in user, swapped per test. */
let currentUser: Record<string, unknown> = user
const refreshUser = vi.fn(async () => undefined)

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: currentUser,
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser,
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

const client = await import('../api/client')
const Settings = (await import('../pages/Settings')).default

function renderSettings() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter>
          <Settings />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** An axios-shaped rejection carrying the server's message. */
function apiError(detail: string) {
  return Object.assign(new Error('Request failed'), {
    isAxiosError: true,
    response: { data: { detail } },
  })
}

let alerts: string[] = []
let reloads = 0

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  currentUser = user
  alerts = []
  reloads = 0
  window.localStorage.clear()
  document.documentElement.classList.remove('dark')
  window.alert = (message?: unknown) => void alerts.push(String(message))
  window.confirm = () => true
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
  // jsdom refuses to navigate; the page only needs the call to be made.
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { ...window.location, reload: () => void (reloads += 1) },
  })
  Object.defineProperty(window.navigator, 'clipboard', {
    configurable: true,
    value: { writeText: vi.fn(async () => undefined) },
  })
})

afterEach(cleanup)

describe('changing your own email', () => {
  it('sends an administrator authorization to the current mailbox', async () => {
    vi.mocked(client.authApi.requestEmailChange).mockResolvedValue({
      message: 'Authorization link sent to your current email address.',
    } as never)
    renderSettings()

    expect(screen.queryByText(/administrator must approve/i)).toBeNull()
    expect(screen.getByText(/authorization link to your current email first/i)).toBeTruthy()

    fireEvent.change(screen.getByLabelText('New email'), {
      target: { value: 'ada.new@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Current password'), {
      target: { value: 'my-current-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send authorization email/i }))

    await waitFor(() =>
      expect(client.authApi.requestEmailChange).toHaveBeenCalledWith(
        'my-current-password',
        'ada.new@example.com',
      ),
    )
    expect(await screen.findByText(/authorization link sent to your current email/i)).toBeTruthy()
    expect(refreshUser).toHaveBeenCalled()
  })

  it('empties the form once the request is accepted', async () => {
    vi.mocked(client.authApi.requestEmailChange).mockResolvedValue({
      message: 'Requested.',
    } as never)
    renderSettings()

    fireEvent.change(screen.getByLabelText('New email'), { target: { value: 'a@b.example' } })
    fireEvent.change(screen.getByLabelText('Current password'), { target: { value: 'pw' } })
    fireEvent.click(screen.getByRole('button', { name: /send authorization email/i }))

    // Leaving the password on screen after a successful request is the kind of
    // thing that ends up in a screenshot.
    await waitFor(() =>
      expect((screen.getByLabelText('Current password') as HTMLInputElement).value).toBe(''),
    )
    expect((screen.getByLabelText('New email') as HTMLInputElement).value).toBe('')
  })

  it('says why the request was refused', async () => {
    vi.mocked(client.authApi.requestEmailChange).mockRejectedValueOnce(
      apiError('Current password is incorrect'),
    )
    renderSettings()

    fireEvent.change(screen.getByLabelText('New email'), { target: { value: 'a@b.example' } })
    fireEvent.change(screen.getByLabelText('Current password'), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /send authorization email/i }))

    expect(await screen.findByText(/password is incorrect/i)).toBeTruthy()
  })

  it('shows a pending request instead of the form, and cancels it', async () => {
    currentUser = {
      ...user,
      pending_email: 'ada.new@example.com',
      email_change_status: 'requested',
    }
    vi.mocked(client.authApi.cancelEmailChange).mockResolvedValue({
      message: 'The request was cancelled.',
    } as never)
    renderSettings()

    expect(screen.getByText(/Requested email: ada\.new@example\.com/)).toBeTruthy()
    expect(screen.getByText(/waiting for an administrator/i)).toBeTruthy()
    expect(screen.queryByLabelText('New email')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /cancel email change/i }))

    await waitFor(() => expect(client.authApi.cancelEmailChange).toHaveBeenCalled())
    expect(await screen.findByText(/was cancelled/i)).toBeTruthy()
    expect(refreshUser).toHaveBeenCalled()
  })

  it('says the original mailbox must authorize before Bloom contacts the new one', async () => {
    currentUser = {
      ...user,
      pending_email: 'ada.new@example.com',
      email_change_status: 'awaiting_current_confirmation',
    }
    renderSettings()

    expect(screen.getByText(/authorization link sent to your current address/i)).toBeTruthy()
  })

  it('says an authorized change is waiting on the new mailbox', async () => {
    currentUser = {
      ...user,
      pending_email: 'ada.new@example.com',
      email_change_status: 'awaiting_confirmation',
    }
    renderSettings()

    expect(screen.getByText(/verification link sent to the new address/i)).toBeTruthy()
  })

  it('reports a cancellation that failed', async () => {
    currentUser = { ...user, pending_email: 'ada.new@example.com', email_change_status: 'requested' }
    vi.mocked(client.authApi.cancelEmailChange).mockRejectedValueOnce(
      apiError('That request was already approved'),
    )
    renderSettings()

    fireEvent.click(screen.getByRole('button', { name: /cancel email change/i }))

    expect(await screen.findByText(/already approved/i)).toBeTruthy()
  })
})

describe('appearance and region', () => {
  it('remembers the theme across visits', async () => {
    renderSettings()
    expect(document.documentElement.classList.contains('dark')).toBe(false)

    fireEvent.click(screen.getByText('Theme Mode').closest('div')?.parentElement
      ?.querySelector('button') as HTMLElement)

    await waitFor(() => expect(document.documentElement.classList.contains('dark')).toBe(true))
    expect(window.localStorage.getItem('bloom-theme')).toBe('dark')
  })

  it('follows the stored choice over the system preference', async () => {
    window.localStorage.setItem('bloom-theme', 'dark')
    renderSettings()

    await waitFor(() => expect(document.documentElement.classList.contains('dark')).toBe(true))
  })

  it('stores the timezone and reloads so every date re-renders', async () => {
    renderSettings()

    const picker = screen.getAllByRole('combobox')[0]
    fireEvent.change(picker, { target: { value: 'Etc/GMT+5' } })

    expect(window.localStorage.getItem('bloom-timezone')).toBe('Etc/GMT+5')
    // Dates are formatted all over the app, so the page reloads rather than
    // trying to re-render each of them.
    expect(reloads).toBe(1)
  })
})

describe('the credentials Bud submits results with', () => {
  it('are not fetched at all for a non-admin', async () => {
    currentUser = { ...user, role: 'maintainer' }
    renderSettings()

    await waitFor(() => expect(screen.getByText('Account')).toBeTruthy())
    expect(client.serviceCredentialsApi.list).not.toHaveBeenCalled()
  })

  it('copies the newly generated token', async () => {
    renderSettings()
    await screen.findByText(new RegExp(serviceCredential.token_prefix))

    fireEvent.click(screen.getByRole('button', { name: /create credential/i }))
    await screen.findByText(/blm_sync_secret/)
    fireEvent.click(screen.getByRole('button', { name: /copy/i }))

    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalled())
    const [copied] = vi.mocked(navigator.clipboard.writeText).mock.calls[0]
    expect(String(copied)).toContain('blm_sync_secret')
  })

  it('reports a token it could not generate', async () => {
    vi.mocked(client.serviceCredentialsApi.create).mockRejectedValueOnce(
      apiError('You already have the maximum number of credentials'),
    )
    renderSettings()
    await screen.findByText(new RegExp(serviceCredential.token_prefix))

    fireEvent.click(screen.getByRole('button', { name: /create credential/i }))

    await waitFor(() => expect(alerts.join(' ')).toMatch(/maximum number of credentials/i))
  })

  it('reports a rotation that failed', async () => {
    vi.mocked(client.serviceCredentialsApi.rotate).mockRejectedValueOnce(
      apiError('That credential was revoked'),
    )
    renderSettings()
    await screen.findByText(new RegExp(serviceCredential.token_prefix))

    fireEvent.click(screen.getByRole('button', { name: /^rotate$/i }))

    await waitFor(() => expect(alerts.join(' ')).toMatch(/was revoked/i))
  })

  it('keeps the credential when the revoke is declined', async () => {
    window.confirm = () => false
    renderSettings()
    await screen.findByText(new RegExp(serviceCredential.token_prefix))

    fireEvent.click(screen.getByRole('button', { name: /^revoke$/i }))

    await settle()
    expect(client.serviceCredentialsApi.revoke).not.toHaveBeenCalled()
  })

  it('reports a revoke that failed', async () => {
    vi.mocked(client.serviceCredentialsApi.revoke).mockRejectedValueOnce(
      apiError('That credential is in use by a running sync'),
    )
    renderSettings()
    await screen.findByText(new RegExp(serviceCredential.token_prefix))

    fireEvent.click(screen.getByRole('button', { name: /^revoke$/i }))

    await waitFor(() => expect(alerts.join(' ')).toMatch(/in use by a running sync/i))
  })

  it('shows nothing rather than failing when the list cannot be read', async () => {
    vi.mocked(client.serviceCredentialsApi.list).mockRejectedValueOnce(apiError('Server error'))
    renderSettings()

    await waitFor(() => expect(client.serviceCredentialsApi.list).toHaveBeenCalled())
    // The rest of the settings screen still has to work.
    expect(screen.getByText('Account')).toBeTruthy()
    expect(screen.queryByText(new RegExp(serviceCredential.token_prefix))).toBeNull()
  })
})
