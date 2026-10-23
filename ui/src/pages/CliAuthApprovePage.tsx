import axios from 'axios'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { api, extractApiErrorMessage, type User } from '../api/client'
import { PRODUCT_NAME } from '../brandAssets'
import AuthPageShell from '../components/AuthPageShell'
import { useAuth } from '../contexts/AuthContext'

interface CliSession {
  session_id: string
  client_name: string
  mode: 'callback' | 'code'
  redirect_uri: string | null
  expires_at: string
  consumed: boolean
  created_at: string
  request_code: string
}

interface CliApproval {
  redirect_to?: string
  exchange_code?: string
  expires_at?: string
}

interface CliDenial {
  redirect_to?: string
}

const NEW_LINK = 'This sign-in request is invalid, expired or already approved. Request a new sign-in link from your client.'
const INVALID_CALLBACK = 'The callback destination is invalid. Request a new sign-in link from your client.'
const DENIED = 'This sign-in request was denied. The link no longer works.'
const WARNING = 'rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200'
const SESSION_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const LOOPBACK_TARGET = /^http:\/\/(?:127\.0\.0\.1|localhost|\[::1\]):(\d+)(?:[/?]|$)/i

/** The session id of the approval link when it names exactly one well-formed id. */
function linkedSessionId(search: string): string | null {
  const ids = new URLSearchParams(search).getAll('session_id')
  return ids.length === 1 && SESSION_ID.test(ids[0]) ? ids[0] : null
}

/** Whether the URL carries exactly one non-empty value for the parameter. */
function hasSingleValue(url: URL, name: string): boolean {
  const values = url.searchParams.getAll(name)
  return values.length === 1 && values[0] !== ''
}

/** The loopback target parsed, when it has a valid port, no credentials or fragment and the registered origin and path. */
function registeredCallback(target: string, requested: string | null): URL {
  const port = Number(LOOPBACK_TARGET.exec(target)?.[1] ?? 0)
  if (!requested || port < 1 || port > 65535 || /[\s\\#]/.test(target)) throw new Error(INVALID_CALLBACK)
  const url = new URL(target)
  const original = new URL(requested)
  const sameCallback = url.origin === original.origin && url.pathname === original.pathname
  if (!sameCallback || url.username || url.password) throw new Error(INVALID_CALLBACK)
  return url
}

/** The approved loopback destination, checked against the callback the client registered. */
function callbackDestination(target: string, requested: string | null): string {
  const url = registeredCallback(target, requested)
  if (!hasSingleValue(url, 'code') || !hasSingleValue(url, 'state')) throw new Error(INVALID_CALLBACK)
  return target
}

/** The denied loopback destination: one error=access_denied, one state and no code on the registered callback. */
function denialDestination(target: string, requested: string | null): string {
  const url = registeredCallback(target, requested)
  const errors = url.searchParams.getAll('error')
  const denied = errors.length === 1 && errors[0] === 'access_denied'
  if (!denied || !hasSingleValue(url, 'state') || url.searchParams.has('code')) throw new Error(INVALID_CALLBACK)
  return target
}

/** Whether a failed request answered 403, the refusal of a code sign-in while it is turned off. */
function isCodeModeOff(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 403
}

/** A UTC timestamp from the API shown in the browser's local date and time. */
function localTime(value: string): string {
  return new Date(value).toLocaleString()
}

/** The one-time code to paste into the client, with a copy action. */
function ManualCode({ code }: Readonly<{ code: string }>) {
  const [copyStatus, setCopyStatus] = useState('')
  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopyStatus('Code copied.')
    } catch {
      setCopyStatus('Select and copy the code above, then paste it into your client.')
    }
  }
  return (
    <div className="space-y-4">
      <p className={WARNING}>Paste this code only into the client where you started this sign-in. Never send it to anyone.</p>
      <p className="text-sm text-muted-foreground">It expires with this sign-in request.</p>
      <label htmlFor="cli-code" className="block text-sm font-medium text-foreground">One-time sign-in code</label>
      <input id="cli-code" value={code} readOnly autoComplete="off" className="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground font-mono text-sm" />
      <button type="button" onClick={() => { void copyCode() }} className="w-full rounded-lg bg-primary px-4 py-2 text-primary-foreground">Copy code</button>
      <p role="status" className="text-sm text-muted-foreground">{copyStatus}</p>
    </div>
  )
}

/** The Deny action, which ends the sign-in request on the server. */
function DenyButton({ busy, onDeny }: Readonly<{ busy: boolean; onDeny: () => void }>) {
  return <button type="button" disabled={busy} onClick={onDeny} className="flex-1 rounded-lg border border-input px-4 py-2 text-foreground disabled:opacity-50">Deny</button>
}

/** The request code, the requesting client, the account, the request time and expiry, with Approve and Deny. */
function Consent({ session, account, busy, approving, onApprove, onDeny }: Readonly<{
  session: CliSession
  account: User | null
  busy: boolean
  approving: boolean
  onApprove: () => void
  onDeny: () => void
}>) {
  const destination = session.mode === 'callback'
    ? `Approval returns to your local client at ${session.redirect_uri}.`
    : 'Approval shows a one-time code to paste into your client.'
  const signedIn = account ? `${account.full_name} (${account.email})` : 'your account'
  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-muted-foreground">Request code</p>
        <p className="font-mono text-2xl font-semibold tracking-widest text-foreground">{session.request_code}</p>
        <p className="text-sm text-muted-foreground">It must match the code your client shows. If it does not, deny this request.</p>
      </div>
      <div>
        <p className="font-semibold text-foreground">{session.client_name}</p>
        <p className="text-xs text-muted-foreground">Name given by the requesting client, not verified.</p>
      </div>
      <p className="text-sm text-muted-foreground">Approving signs this client in to {PRODUCT_NAME} as {signedIn}, with your full permissions.</p>
      <p className="text-sm text-muted-foreground">Requested {localTime(session.created_at)}. Expires {localTime(session.expires_at)}.</p>
      <p className={WARNING}>Approve only a sign-in you started yourself, on your own computer, in the last few minutes.</p>
      <p className="text-sm text-muted-foreground">{destination}</p>
      {session.mode === 'code' && (
        <p className={WARNING}>This request asks for a one-time code instead of returning to a client on this computer. If someone else sent you this link or asks you for the code, deny it: the code signs their client in to your account.</p>
      )}
      <div className="flex gap-3">
        <button type="button" disabled={busy} onClick={onApprove} className="flex-1 rounded-lg bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50">{approving ? 'Approving...' : 'Approve'}</button>
        <DenyButton busy={busy} onDeny={onDeny} />
      </div>
    </div>
  )
}

/** Browser approval of a CLI sign-in request for the signed-in account. */
export default function CliAuthApprovePage() {
  const { user, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const sessionId = linkedSessionId(location.search)
  const [session, setSession] = useState<CliSession | null>(null)
  const [error, setError] = useState('')
  const [codeModeOff, setCodeModeOff] = useState('')
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [approving, setApproving] = useState(false)
  const [denied, setDenied] = useState(false)

  useEffect(() => {
    if (isLoading || !sessionId) return
    if (!isAuthenticated) {
      const approvalPath = `/auth/cli?session_id=${sessionId}`
      void navigate(`/login?next=${encodeURIComponent(approvalPath)}`, { replace: true })
      return
    }
    let active = true
    api.get<CliSession>(`/auth/cli/sessions/${sessionId}`)
      .then(({ data }) => {
        if (active) setSession(data)
      })
      .catch((err: unknown) => {
        if (!active) return
        if (isCodeModeOff(err)) setCodeModeOff(extractApiErrorMessage(err, NEW_LINK))
        else setError(extractApiErrorMessage(err, NEW_LINK))
      })
    return () => { active = false }
  }, [isLoading, isAuthenticated, navigate, sessionId])

  useEffect(() => {
    if (!session) return
    const timer = window.setTimeout(() => {
      setCode('')
      setError(NEW_LINK)
    }, Math.max(0, new Date(session.expires_at).getTime() - Date.now()))
    return () => window.clearTimeout(timer)
  }, [session])

  const approve = async () => {
    if (!session || busy) return
    setBusy(true)
    setApproving(true)
    try {
      const { data } = await api.post<CliApproval>('/auth/cli/approve', { session_id: session.session_id })
      if (session.mode === 'callback') {
        window.location.assign(callbackDestination(data.redirect_to ?? '', session.redirect_uri))
      } else if (data.exchange_code) {
        setCode(data.exchange_code)
      } else {
        throw new Error(NEW_LINK)
      }
    } catch (err: unknown) {
      setError(extractApiErrorMessage(err, NEW_LINK))
    } finally {
      setBusy(false)
      setApproving(false)
    }
  }

  const deny = async () => {
    if (!sessionId || busy) return
    setBusy(true)
    try {
      const { data } = await api.post<CliDenial>('/auth/cli/deny', { session_id: sessionId })
      if (session?.mode === 'callback' || data.redirect_to !== undefined) {
        window.location.assign(denialDestination(data.redirect_to ?? '', session?.redirect_uri ?? null))
      } else {
        setDenied(true)
      }
    } catch (err: unknown) {
      setError(extractApiErrorMessage(err, NEW_LINK))
    } finally {
      setBusy(false)
    }
  }

  const problem = error || (sessionId ? '' : NEW_LINK)

  let content = <p role="status" className="text-sm text-muted-foreground">Loading sign-in request...</p>
  if (problem) {
    content = <div role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{problem}</div>
  } else if (denied) {
    content = <p role="status" className="text-sm text-foreground">{DENIED}</p>
  } else if (codeModeOff) {
    content = (
      <div className="space-y-4">
        <div role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{codeModeOff}</div>
        <div className="flex gap-3">
          <DenyButton busy={busy} onDeny={() => { void deny() }} />
        </div>
      </div>
    )
  } else if (code) {
    content = <ManualCode code={code} />
  } else if (session) {
    content = (
      <Consent
        session={session}
        account={user}
        busy={busy}
        approving={approving}
        onApprove={() => { void approve() }}
        onDeny={() => { void deny() }}
      />
    )
  }

  return (
    <AuthPageShell>
      <h1 className="text-xl font-bold text-foreground mb-4">Connect a client to {PRODUCT_NAME}</h1>
      {content}
    </AuthPageShell>
  )
}
