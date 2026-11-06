// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import Login from '../pages/Login'
import CliAuthApprovePage from '../pages/CliAuthApprovePage'

const mocks = vi.hoisted(() => ({
  login: vi.fn(), navigate: vi.fn(), get: vi.fn(), post: vi.fn(),
  auth: { isAuthenticated: true, isLoading: false, user: { id: 7, full_name: 'Dana Reader', email: 'dana@example.com' } },
}))

vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ ...mocks.auth, login: mocks.login }) }))
vi.mock('react-router', async (original) => ({
  ...await original<typeof import('react-router')>(), useNavigate: () => mocks.navigate,
}))
vi.mock('../api/client', async (original) => ({
  ...await original<typeof import('../api/client')>(),
  api: { get: mocks.get, post: mocks.post },
  setupApi: { getStatus: vi.fn().mockResolvedValue({ setup_required: false }) },
}))

const sessionId = '2cad0f2e-2d68-40ea-82cc-c4fcc57346da'
const approvalPath = `/auth/cli?session_id=${sessionId}`
const originalLocation = window.location
const callbackUri = 'http://127.0.0.1:8123/callback'
const codeModeOff = 'Code sign-in is turned off on this instance. Use callback mode.'

function inTenMinutes() {
  return new Date(Date.now() + 600_000).toISOString()
}

function session(overrides: Record<string, unknown> = {}) {
  return { data: {
    session_id: sessionId, client_name: 'Example client', mode: 'code', redirect_uri: null,
    expires_at: inTenMinutes(), consumed: false, created_at: new Date(Date.now() - 60_000).toISOString(),
    ...overrides,
  } }
}

function refused(status: number, detail: string) {
  return { isAxiosError: true, message: detail, response: { status, data: { detail }, headers: {} } }
}

function captureNavigation() {
  const assign = vi.fn()
  Object.defineProperty(window, 'location', { configurable: true, writable: true, value: { assign } })
  return assign
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.auth.isAuthenticated = true
  mocks.auth.isLoading = false
  mocks.login.mockResolvedValue(undefined)
  mocks.get.mockReset().mockResolvedValue(session())
  mocks.post.mockReset().mockResolvedValue({ data: { exchange_code: 'one-time-code', expires_at: inTenMinutes() } })
})

afterEach(() => {
  cleanup()
  Object.defineProperty(window, 'location', { configurable: true, writable: true, value: originalLocation })
})

function renderApproval(path = approvalPath) {
  return render(<MemoryRouter initialEntries={[path]}><CliAuthApprovePage /></MemoryRouter>)
}

describe('CLI browser approval', () => {
  it('waits for browser authentication to initialize', () => {
    mocks.auth.isLoading = true
    renderApproval()
    expect(screen.getByRole('status')).toHaveTextContent(/loading/i)
    expect(mocks.get).not.toHaveBeenCalled()
    expect(mocks.navigate).not.toHaveBeenCalled()
  })

  it('sends signed-out users to login with the encoded approval destination', async () => {
    mocks.auth.isAuthenticated = false
    renderApproval()
    await waitFor(() => expect(mocks.navigate).toHaveBeenCalledWith(`/login?next=${encodeURIComponent(approvalPath)}`, { replace: true }))
    expect(mocks.get).not.toHaveBeenCalled()
  })

  it('names the local callback destination before approval', async () => {
    mocks.get.mockResolvedValue(session({ mode: 'callback', redirect_uri: 'http://127.0.0.1:8123/callback' }))
    renderApproval()
    expect(await screen.findByText(/returns to your local client at http:\/\/127\.0\.0\.1:8123\/callback/i)).toBeInTheDocument()
  })

  it.each([
    [callbackUri, `${callbackUri}?error=access_denied&state=expected`],
    [`${callbackUri}?existing=a`, `${callbackUri}?existing=a&error=access_denied&state=expected`],
  ])('denies a callback request for %s on the server and returns the denial to %s', async (redirectUri, target) => {
    const assign = captureNavigation()
    mocks.get.mockResolvedValue(session({ mode: 'callback', redirect_uri: redirectUri }))
    mocks.post.mockResolvedValue({ data: { redirect_to: target } })
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Deny' }))
    await waitFor(() => expect(assign).toHaveBeenCalledWith(target))
    expect(mocks.post).toHaveBeenCalledTimes(1)
    expect(mocks.post).toHaveBeenCalledWith('/auth/cli/deny', { session_id: sessionId })
  })

  it('denies a code request on the server and says the link no longer works', async () => {
    mocks.post.mockResolvedValue({ data: {} })
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Deny' }))
    expect(await screen.findByText('This sign-in request was denied. The link no longer works.')).toBeInTheDocument()
    expect(mocks.post).toHaveBeenCalledWith('/auth/cli/deny', { session_id: sessionId })
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Deny' })).not.toBeInTheDocument()
  })

  it.each([
    'https://evil.test/callback?error=access_denied&state=s', 'http://127.0.0.1/callback?error=access_denied&state=s',
    'http://127.0.0.1:9999/callback?error=access_denied&state=s', 'http://127.0.0.1:8123/other?error=access_denied&state=s',
    'http://user@127.0.0.1:8123/callback?error=access_denied&state=s', 'http://127.0.0.1:8123/callback?error=access_denied&state=s#',
    'http://127.0.0.1:8123/callback?error=access_denied&error=access_denied&state=s', 'http://127.0.0.1:8123/callback?error=server_error&state=s',
    'http://127.0.0.1:8123/callback?state=s', 'http://127.0.0.1:8123/callback?error=access_denied',
    'http://127.0.0.1:8123/callback?error=access_denied&state=s&state=t', 'http://127.0.0.1:8123/callback?error=access_denied&state=',
    'http://127.0.0.1:8123/callback?error=access_denied&state=s&code=c', 'http://127.0.0.1:8123/callback?code=c&state=s',
    'http://127.0.0.1:8123/call back?error=access_denied&state=s', '',
  ])('rejects an invalid denial response %s', async (target) => {
    const assign = captureNavigation()
    mocks.get.mockResolvedValue(session({ mode: 'callback', redirect_uri: callbackUri }))
    mocks.post.mockResolvedValue({ data: { redirect_to: target } })
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Deny' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/callback/i)
    expect(assign).not.toHaveBeenCalled()
  })

  it('keeps the Approve label while a denial is in flight', async () => {
    mocks.post.mockReturnValue(new Promise(() => {}))
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Deny' }))
    expect(await screen.findByRole('button', { name: 'Approve' })).toBeDisabled()
    expect(screen.queryByText('Approving...')).not.toBeInTheDocument()
  })

  it('shows a refused denial without approving', async () => {
    mocks.post.mockRejectedValue(refused(400, 'Invalid or expired authorization. Request a new sign-in link from your client.'))
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Deny' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/new sign-in link/i)
    expect(mocks.post).toHaveBeenCalledTimes(1)
    expect(mocks.post).toHaveBeenCalledWith('/auth/cli/deny', { session_id: sessionId })
  })

  it('shows the code sign-in refusal with Deny and without Approve', async () => {
    mocks.get.mockRejectedValue(refused(403, codeModeOff))
    mocks.post.mockResolvedValue({ data: {} })
    renderApproval()
    expect(await screen.findByRole('alert')).toHaveTextContent(codeModeOff)
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Deny' }))
    expect(await screen.findByText('This sign-in request was denied. The link no longer works.')).toBeInTheDocument()
    expect(mocks.post).toHaveBeenCalledWith('/auth/cli/deny', { session_id: sessionId })
  })

  it('does not follow a denial callback when the request details are unknown', async () => {
    const assign = captureNavigation()
    mocks.get.mockRejectedValue(refused(403, codeModeOff))
    mocks.post.mockResolvedValue({ data: { redirect_to: `${callbackUri}?error=access_denied&state=s` } })
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Deny' }))
    expect(await screen.findByText(/callback destination is invalid/i)).toBeInTheDocument()
    expect(assign).not.toHaveBeenCalled()
  })

  it('shows any other refusal of the request details without actions', async () => {
    mocks.get.mockRejectedValue(refused(400, 'Invalid or expired authorization. Request a new sign-in link from your client.'))
    renderApproval()
    expect(await screen.findByRole('alert')).toHaveTextContent(/new sign-in link/i)
    expect(screen.queryByRole('button', { name: 'Deny' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
  })

  it.each(['/auth/cli', '/auth/cli?session_id=bad', `/auth/cli?session_id=${sessionId}&session_id=${sessionId}`])('handles an invalid approval link %s', async (path) => {
    renderApproval(path)
    expect(await screen.findByRole('alert')).toHaveTextContent(/new sign-in link/i)
    expect(mocks.get).not.toHaveBeenCalled()
  })

  it('shows an actionable error for an expired or already approved session', async () => {
    mocks.get.mockRejectedValue(new Error('Invalid or expired authorization. Request a new sign-in link from your client.'))
    renderApproval()
    expect(await screen.findByRole('alert')).toHaveTextContent(/new sign-in link/i)
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
  })
})

function submitLogin(next: string) {
  render(<MemoryRouter initialEntries={[`/login?next=${encodeURIComponent(next)}`]}><Login /></MemoryRouter>)
  fireEvent.change(screen.getByPlaceholderText('you@company.com'), { target: { value: 'reader@example.com' } })
  fireEvent.change(screen.getByPlaceholderText('Enter your password'), { target: { value: 'password' } })
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
}

describe('CLI login return destination', () => {
  it('returns to the same internal approval session after login', async () => {
    submitLogin(approvalPath)
    await waitFor(() => expect(mocks.navigate).toHaveBeenCalledWith(approvalPath, { replace: true }))
  })

  it('opens the dashboard after a login without a return destination', async () => {
    render(<MemoryRouter initialEntries={['/login']}><Login /></MemoryRouter>)
    fireEvent.change(screen.getByPlaceholderText('you@company.com'), { target: { value: 'reader@example.com' } })
    fireEvent.change(screen.getByPlaceholderText('Enter your password'), { target: { value: 'password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(mocks.navigate).toHaveBeenCalledWith('/', { replace: true }))
  })

  it.each([
    'https://evil.test/auth/cli', '//evil.test/auth/cli', '/\\evil.test/auth/cli',
    '/auth/cli?session_id=invalid', `${approvalPath}&next=https://evil.test`,
    `${approvalPath}#fragment`, '/settings', '/auth/cli/../settings',
  ])('rejects an unapproved return destination %s', async (next) => {
    submitLogin(next)
    await waitFor(() => expect(mocks.navigate).toHaveBeenCalledWith('/', { replace: true }))
  })
})
