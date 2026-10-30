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

/** Types the code the client shows and waits for the server to confirm it. */
async function enterMatchingCode() {
  fireEvent.change(await screen.findByLabelText('Request code'), { target: { value: 'BUUZ-WHVV' } })
  expect(await screen.findByText('The code matches.')).toBeInTheDocument()
}

/** Answers /auth/cli/check with the given result and every other post with the approval answer. */
function answerCheck(check: () => Promise<unknown>, other: () => Promise<unknown> = () => Promise.resolve({ data: {} })) {
  mocks.post.mockImplementation((url: string) => url === '/auth/cli/check' ? check() : other())
}

function checkCalls() {
  return mocks.post.mock.calls.filter(([url]) => url === '/auth/cli/check')
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
    expect(screen.getByText(/with your full permissions/i)).toBeInTheDocument()
    expect(screen.getByText(/one-time code to paste/i)).toBeInTheDocument()
    expect(mocks.get).toHaveBeenCalledWith(`/auth/cli/sessions/${sessionId}`)
    await enterMatchingCode()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByLabelText('One-time sign-in code')).toHaveValue('one-time-code')
    expect(mocks.post).toHaveBeenCalledWith('/auth/cli/approve', { session_id: sessionId, request_code: 'BUUZ-WHVV' })
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

  it('asks for the request code and shows the unverified client name, the account, the request time and the expiry', async () => {
    const created = '2026-10-22T08:00:00Z'
    const expires = '2026-10-22T08:10:00Z'
    mocks.get.mockResolvedValue(session({ created_at: created, expires_at: expires }))
    renderApproval()
    expect(await screen.findByLabelText('Request code')).toHaveValue('')
    expect(screen.getByText('Type the code your terminal or AI client shows next to the link.')).toBeInTheDocument()
    expect(screen.getByText('Name given by the requesting client, not verified.')).toBeInTheDocument()
    expect(screen.getByText(/as Dana Reader \(dana@example\.com\), with your full permissions\./)).toBeInTheDocument()
    expect(screen.getByText(`Requested ${new Date(created).toLocaleString()}. Expires ${new Date(expires).toLocaleString()}.`)).toBeInTheDocument()
    expect(screen.getByText('Approve only a sign-in you started yourself, on your own computer, in the last few minutes.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument()
  })

  it('warns before approving a code request and repeats the warning with the one-time code', async () => {
    renderApproval()
    expect(await screen.findByText(/If someone else sent you this link or asks you for the code, deny it/)).toBeInTheDocument()
    await enterMatchingCode()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByText('Paste this code only into the client where you started this sign-in. Never send it to anyone.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Deny' })).not.toBeInTheDocument()
  })

  it('shows no code warning for a callback request', async () => {
    mocks.get.mockResolvedValue(session({ mode: 'callback', redirect_uri: callbackUri }))
    renderApproval()
    expect(await screen.findByLabelText('Request code')).toBeInTheDocument()
    expect(screen.queryByText(/asks you for the code/)).not.toBeInTheDocument()
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

  it('rejects a denial response as an approval target', async () => {
    const assign = captureNavigation()
    mocks.get.mockResolvedValue(session({ mode: 'callback', redirect_uri: callbackUri }))
    mocks.post.mockResolvedValue({ data: { redirect_to: `${callbackUri}?error=access_denied&state=s` } })
    renderApproval()
    await enterMatchingCode()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
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

  it('handles approval failure without displaying credentials', async () => {
    answerCheck(() => Promise.resolve({}), () => Promise.reject(new Error('Already approved. Request a new sign-in link.')))
    renderApproval()
    await enterMatchingCode()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/new sign-in link/i)
    expect(screen.queryByLabelText('One-time sign-in code')).not.toBeInTheDocument()
  })

  it('reports a manual approval that returns no code', async () => {
    mocks.post.mockResolvedValue({ data: { expires_at: inTenMinutes() } })
    renderApproval()
    await enterMatchingCode()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/new sign-in link/i)
  })

  it('shows a manual copy instruction when clipboard access fails', async () => {
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: vi.fn().mockRejectedValue(new Error('denied')) } })
    renderApproval()
    await enterMatchingCode()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Copy code' }))
    expect(await screen.findByText(/select and copy the code/i)).toBeInTheDocument()
  })

  it('rejects an external callback returned by the server', async () => {
    mocks.get.mockResolvedValue(session({ mode: 'callback', redirect_uri: 'http://127.0.0.1:8123/callback' }))
    mocks.post.mockResolvedValue({ data: { redirect_to: 'https://evil.test/callback?code=c&state=s' } })
    renderApproval()
    await enterMatchingCode()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/callback/i)
  })

  it.each([
    'http://127.0.0.1:8123/callback', 'http://localhost:80/callback', 'http://[::1]:8123/callback',
  ])('returns an approved callback to %s', async (redirectUri) => {
    const assign = captureNavigation()
    mocks.get.mockResolvedValue(session({ mode: 'callback', redirect_uri: redirectUri }))
    const target = `${redirectUri}?code=approved&state=expected`
    mocks.post.mockResolvedValue({ data: { redirect_to: target } })
    renderApproval()
    await enterMatchingCode()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
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
    await enterMatchingCode()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/callback/i)
  })

  it('renders no request code from the session answer', async () => {
    mocks.get.mockResolvedValue(session({ request_code: 'BUUZ-WHVV' }))
    renderApproval()
    expect(await screen.findByLabelText('Request code')).toHaveValue('')
    expect(screen.queryByText('BUUZ-WHVV')).not.toBeInTheDocument()
  })

  it('formats a typed code and checks it once at eight characters', async () => {
    renderApproval()
    const field = await screen.findByLabelText('Request code')
    for (const letter of 'buuzwhvv') fireEvent.change(field, { target: { value: `${(field as HTMLInputElement).value}${letter}` } })
    expect(field).toHaveValue('BUUZ-WHVV')
    fireEvent.change(field, { target: { value: 'BUUZ-WHVVX' } })
    expect(field).toHaveValue('BUUZ-WHVV')
    await screen.findByText('The code matches.')
    expect(checkCalls()).toEqual([['/auth/cli/check', { session_id: sessionId, request_code: 'BUUZ-WHVV' }]])
  })

  it('formats a pasted code with a space and checks it', async () => {
    renderApproval()
    const field = await screen.findByLabelText('Request code')
    fireEvent.change(field, { target: { value: 'buuz whvv' } })
    expect(field).toHaveValue('BUUZ-WHVV')
    await screen.findByText('The code matches.')
    expect(checkCalls()).toHaveLength(1)
  })

  it('enables Approve only while the checked code matches', async () => {
    renderApproval()
    const field = await screen.findByLabelText('Request code')
    const approveButton = screen.getByRole('button', { name: 'Approve' })
    expect(approveButton).toBeDisabled()
    fireEvent.change(field, { target: { value: 'BUUZ-WHV' } })
    expect(approveButton).toBeDisabled()
    await enterMatchingCode()
    expect(approveButton).toBeEnabled()
    fireEvent.change(field, { target: { value: 'BUUZ-WHV' } })
    expect(approveButton).toBeDisabled()
    expect(screen.queryByText('The code matches.')).not.toBeInTheDocument()
  })

  it('shows a mismatch without the server text and keeps Approve disabled while the request is pending', async () => {
    answerCheck(() => Promise.reject(refused(400, 'Invalid or expired authorization. Request a new sign-in link from your client.')))
    renderApproval()
    fireEvent.change(await screen.findByLabelText('Request code'), { target: { value: 'AAAA-AAAA' } })
    expect(await screen.findByText('This code does not match. Check the code in your terminal, or deny this request.')).toBeInTheDocument()
    expect(screen.queryByText(/new sign-in link/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled()
    expect(mocks.get).toHaveBeenCalledTimes(2)
  })

  it('shows the ended request when a refused check finds the request gone', async () => {
    answerCheck(() => Promise.reject(refused(400, 'Invalid or expired authorization. Request a new sign-in link from your client.')))
    renderApproval()
    const field = await screen.findByLabelText('Request code')
    mocks.get.mockRejectedValue(refused(400, 'Invalid or expired authorization. Request a new sign-in link from your client.'))
    fireEvent.change(field, { target: { value: 'AAAA-AAAA' } })
    expect(await screen.findByRole('alert')).toHaveTextContent(/new sign-in link/i)
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
  })

  it.each(['/auth/cli/check', '/auth/cli/approve'])('asks to wait after a 429 on %s', async (limited) => {
    mocks.post.mockImplementation((url: string) => url === limited ? Promise.reject(refused(429, 'Rate limit exceeded')) : Promise.resolve({}))
    renderApproval()
    fireEvent.change(await screen.findByLabelText('Request code'), { target: { value: 'BUUZ-WHVV' } })
    if (limited === '/auth/cli/approve') {
      await screen.findByText('The code matches.')
      fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    }
    expect(await screen.findByText('Too many attempts. Wait a minute and try again.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled()
  })

  it('shows a mismatch when approval answers 400 for a request that is still pending', async () => {
    answerCheck(() => Promise.resolve({}), () => Promise.reject(refused(400, 'Invalid or expired authorization. Request a new sign-in link from your client.')))
    renderApproval()
    await enterMatchingCode()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByText('This code does not match. Check the code in your terminal, or deny this request.')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('ignores a check answer for a code that was edited since', async () => {
    let answer: (value: unknown) => void = () => {}
    answerCheck(() => new Promise((resolve) => { answer = resolve }))
    renderApproval()
    const field = await screen.findByLabelText('Request code')
    fireEvent.change(field, { target: { value: 'BUUZ-WHVV' } })
    fireEvent.change(field, { target: { value: 'BUUZ-WHV' } })
    answer({})
    await waitFor(() => expect(checkCalls()).toHaveLength(1))
    expect(screen.queryByText('The code matches.')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled()
  })

  it('denies with an empty code field', async () => {
    mocks.post.mockResolvedValue({ data: {} })
    renderApproval()
    expect(await screen.findByLabelText('Request code')).toHaveValue('')
    fireEvent.click(screen.getByRole('button', { name: 'Deny' }))
    expect(await screen.findByText('This sign-in request was denied. The link no longer works.')).toBeInTheDocument()
    expect(mocks.post).toHaveBeenCalledWith('/auth/cli/deny', { session_id: sessionId })
  })

  it('clears an approved manual code when the request expires', async () => {
    mocks.get.mockResolvedValue(session({ expires_at: new Date(Date.now() + 1000).toISOString() }))
    renderApproval()
    await enterMatchingCode()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
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
