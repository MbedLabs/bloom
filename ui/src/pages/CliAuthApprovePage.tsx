import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { api, extractApiErrorMessage } from '../api/client'
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
}

interface CliApproval {
  redirect_to?: string
  exchange_code?: string
  expires_at?: string
}

const NEW_LINK = 'This sign-in request is invalid, expired or already approved. Request a new sign-in link from your client.'
const INVALID_CALLBACK = 'The callback destination is invalid. Request a new sign-in link from your client.'
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

/** The approved loopback destination, checked against the callback the client registered. */
function callbackDestination(target: string, requested: string | null): string {
  const port = Number(LOOPBACK_TARGET.exec(target)?.[1] ?? 0)
  if (!requested || port < 1 || port > 65535 || /[\s\\#]/.test(target)) throw new Error(INVALID_CALLBACK)
  const url = new URL(target)
  const original = new URL(requested)
  const sameCallback = url.origin === original.origin && url.pathname === original.pathname
  if (!sameCallback || url.username || url.password || !hasSingleValue(url, 'code') || !hasSingleValue(url, 'state')) {
    throw new Error(INVALID_CALLBACK)
  }
  return target
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
      <p className="text-sm text-muted-foreground">Paste this one-time code into your client or terminal. It expires with this sign-in request.</p>
      <label htmlFor="cli-code" className="block text-sm font-medium text-foreground">One-time sign-in code</label>
      <input id="cli-code" value={code} readOnly autoComplete="off" className="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground font-mono text-sm" />
      <button type="button" onClick={() => { void copyCode() }} className="w-full rounded-lg bg-primary px-4 py-2 text-primary-foreground">Copy code</button>
      <p role="status" className="text-sm text-muted-foreground">{copyStatus}</p>
    </div>
  )
}

/** The requesting client and its destination, with Approve and Cancel. */
function Consent({ session, busy, onApprove, onCancel }: Readonly<{
  session: CliSession
  busy: boolean
  onApprove: () => void
  onCancel: () => void
}>) {
  const destination = session.mode === 'callback'
    ? `Approval returns to your local client at ${session.redirect_uri}.`
    : 'Approval shows a one-time code to paste into your client.'
  return (
    <div className="space-y-4">
      <p className="font-semibold text-foreground">{session.client_name}</p>
      <p className="text-sm text-muted-foreground">This client is requesting access to {PRODUCT_NAME} with your current account permissions. Approve only if you started this request.</p>
      <p className="text-sm text-muted-foreground">{destination}</p>
      <div className="flex gap-3">
        <button type="button" disabled={busy} onClick={onApprove} className="flex-1 rounded-lg bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50">{busy ? 'Approving...' : 'Approve'}</button>
        <button type="button" disabled={busy} onClick={onCancel} className="flex-1 rounded-lg border border-input px-4 py-2 text-foreground disabled:opacity-50">Cancel</button>
      </div>
    </div>
  )
}

/** Browser approval of a CLI sign-in request for the signed-in account. */
export default function CliAuthApprovePage() {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const sessionId = linkedSessionId(location.search)
  const [session, setSession] = useState<CliSession | null>(null)
  const [error, setError] = useState('')
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)

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
        if (active) setError(extractApiErrorMessage(err, NEW_LINK))
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
    }
  }

  const problem = error || (sessionId ? '' : NEW_LINK)

  let content = <p role="status" className="text-sm text-muted-foreground">Loading sign-in request...</p>
  if (problem) {
    content = <div role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{problem}</div>
  } else if (code) {
    content = <ManualCode code={code} />
  } else if (session) {
    content = (
      <Consent
        session={session}
        busy={busy}
        onApprove={() => { void approve() }}
        onCancel={() => { void navigate('/', { replace: true }) }}
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
