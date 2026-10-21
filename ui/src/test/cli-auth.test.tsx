// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import Login from '../pages/Login'
import CliAuthApprovePage from '../pages/CliAuthApprovePage'

const mocks = vi.hoisted(() => ({
  login: vi.fn(), navigate: vi.fn(), get: vi.fn(), post: vi.fn(),
  auth: { isAuthenticated: true, isLoading: false },
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

function inTenMinutes() {
  return new Date(Date.now() + 600_000).toISOString()
}

function session(overrides: Record<string, unknown> = {}) {
  return { data: {
    session_id: sessionId, client_name: 'Example client', mode: 'code', redirect_uri: null,
    expires_at: inTenMinutes(), consumed: false, ...overrides,
  } }
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

  it('shows client consent and displays a copyable manual exchange code', async () => {
    const copy = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: copy } })
    renderApproval()
    expect(await screen.findByText('Example client')).toBeInTheDocument()
    expect(screen.getByText(/current account permissions/i)).toBeInTheDocument()
    expect(screen.getByText(/one-time code to paste/i)).toBeInTheDocument()
    expect(mocks.get).toHaveBeenCalledWith(`/auth/cli/sessions/${sessionId}`)
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByLabelText('One-time sign-in code')).toHaveValue('one-time-code')
    expect(mocks.post).toHaveBeenCalledWith('/auth/cli/approve', { session_id: sessionId })
    fireEvent.click(screen.getByRole('button', { name: 'Copy code' }))
    await waitFor(() => expect(copy).toHaveBeenCalledWith('one-time-code'))
    expect(await screen.findByText('Code copied.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
  })

  it('names the local callback destination before approval', async () => {
    mocks.get.mockResolvedValue(session({ mode: 'callback', redirect_uri: 'http://127.0.0.1:8123/callback' }))
    renderApproval()
    expect(await screen.findByText(/returns to your local client at http:\/\/127\.0\.0\.1:8123\/callback/i)).toBeInTheDocument()
  })

  it('allows cancelling consent without approving the request', async () => {
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Cancel' }))
    expect(mocks.navigate).toHaveBeenCalledWith('/', { replace: true })
    expect(mocks.post).not.toHaveBeenCalled()
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

  it('handles approval failure without displaying credentials', async () => {
    mocks.post.mockRejectedValue(new Error('Already approved. Request a new sign-in link.'))
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/new sign-in link/i)
    expect(screen.queryByLabelText('One-time sign-in code')).not.toBeInTheDocument()
  })

  it('reports a manual approval that returns no code', async () => {
    mocks.post.mockResolvedValue({ data: { expires_at: inTenMinutes() } })
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/new sign-in link/i)
  })

  it('shows a manual copy instruction when clipboard access fails', async () => {
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: vi.fn().mockRejectedValue(new Error('denied')) } })
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Copy code' }))
    expect(await screen.findByText(/select and copy the code/i)).toBeInTheDocument()
  })

  it('rejects an external callback returned by the server', async () => {
    mocks.get.mockResolvedValue(session({ mode: 'callback', redirect_uri: 'http://127.0.0.1:8123/callback' }))
    mocks.post.mockResolvedValue({ data: { redirect_to: 'https://evil.test/callback?code=c&state=s' } })
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/callback/i)
  })

  it.each([
    'http://127.0.0.1:8123/callback', 'http://localhost:80/callback', 'http://[::1]:8123/callback',
  ])('returns an approved callback to %s', async (redirectUri) => {
    const assign = vi.fn()
    Object.defineProperty(window, 'location', { configurable: true, writable: true, value: { assign } })
    mocks.get.mockResolvedValue(session({ mode: 'callback', redirect_uri: redirectUri }))
    const target = `${redirectUri}?code=approved&state=expected`
    mocks.post.mockResolvedValue({ data: { redirect_to: target } })
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    await waitFor(() => expect(assign).toHaveBeenCalledWith(target))
  })

  it.each([
    'http://127.0.0.1/callback?code=c&state=s', 'http://127.0.0.1:0/callback?code=c&state=s',
    'http://127.0.0.1:65536/callback?code=c&state=s', 'http://127.0.0.1:8123/other?code=c&state=s',
    'http://user@127.0.0.1:8123/callback?code=c&state=s', 'http://127.0.0.1:8123/callback?code=c&state=s#',
    'http://127.0.0.1:8123/callback?code=c&code=d&state=s', 'http://127.0.0.1:8123/callback?state=s',
    'http://127.0.0.1:8123/callback?code=c&state=', '',
  ])('rejects an invalid callback response %s', async (target) => {
    mocks.get.mockResolvedValue(session({ mode: 'callback', redirect_uri: 'http://127.0.0.1:8123/callback' }))
    mocks.post.mockResolvedValue({ data: { redirect_to: target } })
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/callback/i)
  })

  it('clears an approved manual code when the request expires', async () => {
    mocks.get.mockResolvedValue(session({ expires_at: new Date(Date.now() + 1000).toISOString() }))
    renderApproval()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    expect(await screen.findByLabelText('One-time sign-in code')).toHaveValue('one-time-code')
    expect(await screen.findByRole('alert')).toHaveTextContent(/new sign-in link/i)
    expect(screen.queryByLabelText('One-time sign-in code')).not.toBeInTheDocument()
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
