import axios from 'axios'
import { Fragment, useEffect, useRef, useState, type ClipboardEvent, type KeyboardEvent } from 'react'
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
const TOO_MANY = 'Too many attempts. Wait a minute and try again.'
const CODE_MATCHES = 'The code matches.'
const CODE_MISMATCH = 'This code does not match. Check the code in your terminal, or deny this request.'
const CODE_LETTERS = 8
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

/** The HTTP status of a failed request, when it has one. */
function answerStatus(error: unknown): number | undefined {
  return axios.isAxiosError(error) ? error.response?.status : undefined
}

/** A typed or pasted text in upper case with every character that is not a letter or digit removed. */
function codeCharacters(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z0-9]/g, '')
}

/** A typed or pasted request code in upper case, letters and digits only, at most eight characters, with a hyphen after the fourth. */
function formatRequestCode(raw: string): string {
  const letters = codeCharacters(raw).slice(0, CODE_LETTERS)
  return letters.length > 4 ? `${letters.slice(0, 4)}-${letters.slice(4)}` : letters
}

type CodeCheck = 'empty' | 'match' | 'mismatch' | 'limited'

const CHECK_TEXT: Record<CodeCheck, string> = { empty: '', match: CODE_MATCHES, mismatch: CODE_MISMATCH, limited: TOO_MANY }

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
      <label htmlFor="cli-code" className="block text-sm font-medium text-foreground">One-time sign-in code</label>
      <input id="cli-code" value={code} readOnly autoComplete="off" className="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground font-mono text-sm" />
      <button type="button" onClick={() => { void copyCode() }} className="w-full rounded-lg bg-primary px-4 py-2 text-primary-foreground">Copy code</button>
      <output className="block text-sm text-muted-foreground">{copyStatus}</output>
    </div>
  )
}

const CODE_SLOTS = Array.from({ length: CODE_LETTERS }, (_, index) => index)

/** The request code as eight one-character boxes with a hyphen after the fourth, reporting the characters entered so far. */
function RequestCodeBoxes({ onChange }: Readonly<{ onChange: (value: string) => void }>) {
  const [slots, setSlots] = useState<string[]>(() => CODE_SLOTS.map(() => ''))
  const boxes = useRef<(HTMLInputElement | null)[]>([])

  const focusBox = (index: number) => {
    boxes.current[Math.min(Math.max(index, 0), CODE_LETTERS - 1)]?.focus()
  }

  const update = (next: string[]) => {
    setSlots(next)
    onChange(next.join(''))
  }

  const setSlot = (index: number, character: string) => {
    update(slots.map((slot, position) => (position === index ? character : slot)))
  }

  const fill = (characters: string) => {
    const code = characters.slice(0, CODE_LETTERS)
    update(CODE_SLOTS.map((index) => code[index] ?? ''))
    focusBox(code.length)
  }

  const enter = (index: number, raw: string) => {
    const typed = codeCharacters(raw)
    const previous = slots[index]
    if (raw === '') {
      setSlot(index, '')
    } else if (typed !== '' && typed === previous) {
      if (raw.length === 1) focusBox(index + 1)
    } else if (typed.length === 1) {
      setSlot(index, typed)
      focusBox(index + 1)
    } else if (typed.length === 2 && previous !== '' && typed.includes(previous)) {
      setSlot(index, typed.startsWith(previous) ? typed[1] : typed[0])
      focusBox(index + 1)
    } else if (typed !== '') {
      fill(typed)
    }
  }

  const paste = (event: ClipboardEvent<HTMLInputElement>) => {
    event.preventDefault()
    const typed = codeCharacters(event.clipboardData.getData('text'))
    if (typed !== '') fill(typed)
  }

  const move = (index: number, event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Backspace' && slots[index] === '' && index > 0) {
      event.preventDefault()
      setSlot(index - 1, '')
      focusBox(index - 1)
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      focusBox(index - 1)
    } else if (event.key === 'ArrowRight') {
      event.preventDefault()
      focusBox(index + 1)
    }
  }

  return (
    <div className="flex items-center gap-1">
      {CODE_SLOTS.map((index) => (
        <Fragment key={index}>
          {index === CODE_LETTERS / 2 && <span aria-hidden="true" className="shrink-0 font-mono text-xl font-semibold text-muted-foreground">-</span>}
          <input
            ref={(element) => { boxes.current[index] = element }}
            value={slots[index]}
            onChange={(event) => enter(index, event.target.value)}
            onKeyDown={(event) => move(index, event)}
            onPaste={paste}
            onFocus={(event) => event.target.select()}
            aria-label={`Request code character ${index + 1} of ${CODE_LETTERS}`}
            autoComplete="off"
            spellCheck={false}
            autoCapitalize="characters"
            className="h-12 w-full min-w-0 flex-1 rounded-lg border border-input bg-background px-0 text-center font-mono text-xl font-semibold text-foreground"
          />
        </Fragment>
      ))}
    </div>
  )
}

/** The Deny action, which ends the sign-in request on the server. */
function DenyButton({ busy, onDeny }: Readonly<{ busy: boolean; onDeny: () => void }>) {
  return <button type="button" disabled={busy} onClick={onDeny} className="flex-1 rounded-lg border border-input px-4 py-2 text-foreground disabled:opacity-50">Deny</button>
}

/** The request code boxes, the requesting client, the account, the request time and expiry, with Approve and Deny. */
function Consent({ session, account, busy, approving, codeCheck, onCodeChange, onApprove, onDeny }: Readonly<{
  session: CliSession
  account: User | null
  busy: boolean
  approving: boolean
  codeCheck: CodeCheck
  onCodeChange: (value: string) => void
  onApprove: () => void
  onDeny: () => void
}>) {
  const signedIn = account ? `${account.full_name} (${account.email})` : 'your account'
  return (
    <div className="space-y-4">
      <fieldset className="min-w-0 space-y-1">
        <legend className="mb-1 block text-sm font-medium text-foreground">Request code</legend>
        <RequestCodeBoxes onChange={onCodeChange} />
        <output className={`block text-sm ${codeCheck === 'match' ? 'text-foreground' : 'text-destructive'}`}>{CHECK_TEXT[codeCheck]}</output>
      </fieldset>
      <div>
        <p className="font-semibold text-foreground wrap-anywhere">{session.client_name}</p>
      </div>
      <p className="text-sm text-muted-foreground">Approving signs this client in to {PRODUCT_NAME} as {signedIn}.</p>
      <p className="text-sm text-muted-foreground">Requested {localTime(session.created_at)}. Expires {localTime(session.expires_at)}.</p>
      <div className="flex gap-3">
        <button type="button" disabled={busy || codeCheck !== 'match'} onClick={onApprove} className="flex-1 rounded-lg bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50">{approving ? 'Approving...' : 'Approve'}</button>
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
  const [typedCode, setTypedCode] = useState('')
  const [codeCheck, setCodeCheck] = useState<CodeCheck>('empty')
  const currentCode = useRef('')

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

  /** A refused check or approval: 429 asks to wait, 400 reloads the request to tell a wrong code from an ended request. */
  const codeRefused = async (value: string, err: unknown) => {
    const status = answerStatus(err)
    if (status === 429) {
      if (currentCode.current === value) setCodeCheck('limited')
      return
    }
    if (status !== 400) {
      setError(extractApiErrorMessage(err, NEW_LINK))
      return
    }
    try {
      await api.get<CliSession>(`/auth/cli/sessions/${sessionId}`)
      if (currentCode.current === value) setCodeCheck('mismatch')
    } catch {
      setError(NEW_LINK)
    }
  }

  const changeCode = (raw: string) => {
    const value = formatRequestCode(raw)
    if (value === currentCode.current) return
    currentCode.current = value
    setTypedCode(value)
    setCodeCheck('empty')
    if (!session || value.replace('-', '').length < CODE_LETTERS) return
    api.post('/auth/cli/check', { session_id: session.session_id, request_code: value })
      .then(() => {
        if (currentCode.current === value) setCodeCheck('match')
      })
      .catch((err: unknown) => {
        if (currentCode.current === value) void codeRefused(value, err)
      })
  }

  const approve = async () => {
    if (!session || busy || codeCheck !== 'match') return
    const value = typedCode
    setBusy(true)
    setApproving(true)
    try {
      const { data } = await api.post<CliApproval>('/auth/cli/approve', { session_id: session.session_id, request_code: value })
      if (session.mode === 'callback') {
        window.location.assign(callbackDestination(data.redirect_to ?? '', session.redirect_uri))
      } else if (data.exchange_code) {
        setCode(data.exchange_code)
      } else {
        throw new Error(NEW_LINK)
      }
    } catch (err: unknown) {
      const status = answerStatus(err)
      if (status === 400 || status === 429) await codeRefused(value, err)
      else setError(extractApiErrorMessage(err, NEW_LINK))
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

  let content = <output className="block text-sm text-muted-foreground">Loading sign-in request...</output>
  if (problem) {
    content = <div role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{problem}</div>
  } else if (denied) {
    content = <output className="block text-sm text-foreground">{DENIED}</output>
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
        codeCheck={codeCheck}
        onCodeChange={changeCode}
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
