import { useState, useEffect } from 'react'
import { Sun, Moon, Monitor, Info, ExternalLink, Globe, ShieldCheck, Copy, Check, Loader2, RefreshCw, Mail } from 'lucide-react'
import {
  APP_VERSION,
  authApi,
  extractApiErrorMessage,
  serviceCredentialsApi,
  type ServiceCredential,
} from '../api/client'
import { useAuth } from '../contexts/AuthContext'

const COMMON_TIMEZONES = [
  { label: 'Auto (Browser)', value: 'auto' },
  { label: 'UTC+0', value: 'UTC' },
  { label: 'UTC+1', value: 'Etc/GMT-1' },
  { label: 'UTC+2', value: 'Etc/GMT-2' },
  { label: 'UTC+3', value: 'Etc/GMT-3' },
  { label: 'UTC+4', value: 'Etc/GMT-4' },
  { label: 'UTC+5', value: 'Etc/GMT-5' },
  { label: 'UTC+5.5', value: 'Asia/Kolkata' },
  { label: 'UTC+6', value: 'Etc/GMT-6' },
  { label: 'UTC+7', value: 'Etc/GMT-7' },
  { label: 'UTC+8', value: 'Etc/GMT-8' },
  { label: 'UTC+9', value: 'Etc/GMT-9' },
  { label: 'UTC+10', value: 'Etc/GMT-10' },
  { label: 'UTC+11', value: 'Etc/GMT-11' },
  { label: 'UTC+12', value: 'Etc/GMT-12' },
  { label: 'UTC-1', value: 'Etc/GMT+1' },
  { label: 'UTC-2', value: 'Etc/GMT+2' },
  { label: 'UTC-3', value: 'Etc/GMT+3' },
  { label: 'UTC-4', value: 'Etc/GMT+4' },
  { label: 'UTC-5', value: 'Etc/GMT+5' },
  { label: 'UTC-6', value: 'Etc/GMT+6' },
  { label: 'UTC-7', value: 'Etc/GMT+7' },
  { label: 'UTC-8', value: 'Etc/GMT+8' },
  { label: 'UTC-9', value: 'Etc/GMT+9' },
  { label: 'UTC-10', value: 'Etc/GMT+10' },
  { label: 'UTC-11', value: 'Etc/GMT+11' },
  { label: 'UTC-12', value: 'Etc/GMT+12' },
]

function useDarkMode() {
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem('bloom-theme')
    if (stored) return stored === 'dark'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    const root = document.documentElement
    if (dark) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    localStorage.setItem('bloom-theme', dark ? 'dark' : 'light')
  }, [dark])

  return [dark, setDark] as const
}

export default function Settings() {
  const { user, refreshUser } = useAuth()
  const isAdmin = user?.role === 'admin'
  
  const [dark, setDark] = useDarkMode()
  const [newEmail, setNewEmail] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [emailMessage, setEmailMessage] = useState<string | null>(null)

  // Timezone state
  const [timezone, setTimezone] = useState(() => localStorage.getItem('bloom-timezone') || 'auto')

  // Scoped Bud result-sync credential state
  const [generatedToken, setGeneratedToken] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [copied, setCopied] = useState(false)
  const [credentials, setCredentials] = useState<ServiceCredential[]>([])

  useEffect(() => {
    if (!isAdmin) return
    serviceCredentialsApi.list().then(setCredentials).catch(() => setCredentials([]))
  }, [isAdmin])

  const handleTimezoneChange = (newTz: string) => {
    setTimezone(newTz)
    localStorage.setItem('bloom-timezone', newTz)
    window.location.reload()
  }

  const handleRequestEmailChange = async (event: React.FormEvent) => {
    event.preventDefault()
    setEmailMessage(null)
    try {
      const response = await authApi.requestEmailChange(currentPassword, newEmail)
      setEmailMessage(response.message)
      setNewEmail('')
      setCurrentPassword('')
      await refreshUser()
    } catch (error) {
      setEmailMessage(extractApiErrorMessage(error, 'Failed to request email change'))
    }
  }

  const handleCancelEmailChange = async () => {
    setEmailMessage(null)
    try {
      const response = await authApi.cancelEmailChange()
      setEmailMessage(response.message)
      await refreshUser()
    } catch (error) {
      setEmailMessage(extractApiErrorMessage(error, 'Failed to cancel email change'))
    }
  }

  const handleGenerateToken = async () => {
    setIsGenerating(true)
    try {
      const response = await serviceCredentialsApi.create()
      setGeneratedToken(response.token)
      setCredentials((current) => [response, ...current])
    } catch (error) {
      alert(`Error generating token: ${extractApiErrorMessage(error)}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleRotateToken = async (id: number) => {
    setIsGenerating(true)
    try {
      const response = await serviceCredentialsApi.rotate(id)
      setGeneratedToken(response.token)
      setCredentials(await serviceCredentialsApi.list())
    } catch (error) {
      alert(`Error rotating token: ${extractApiErrorMessage(error)}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleRevokeToken = async (id: number) => {
    if (!window.confirm('Revoke this Bud result-sync credential?')) return
    try {
      await serviceCredentialsApi.revoke(id)
      setCredentials(await serviceCredentialsApi.list())
    } catch (error) {
      alert(`Error revoking token: ${extractApiErrorMessage(error)}`)
    }
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedToken)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="max-w-2xl space-y-6 animate-fade-in pb-20">
      {/* Account */}
      <div className="bg-card rounded-lg border border-border shadow-elegant overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center gap-2 bg-muted/30">
          <Mail className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">Account</h3>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label htmlFor="current-email" className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
              Current email
            </label>
            <input
              id="current-email"
              type="email"
              value={user?.email ?? ''}
              readOnly
              className="w-full px-3 py-2 bg-muted/50 border border-input rounded-md text-sm text-foreground"
            />
          </div>

          {user?.pending_email ? (
            <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-4 space-y-3">
              <div>
                <p className="text-sm font-medium text-foreground">Requested email: {user.pending_email}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {user.email_change_status === 'requested'
                    ? 'Waiting for an administrator to approve or reject this request.'
                    : 'Approved. Use the confirmation link sent to the new address to finish the change.'}
                </p>
              </div>
              <button
                type="button"
                onClick={handleCancelEmailChange}
                className="text-sm font-medium text-destructive hover:underline"
              >
                Cancel email change
              </button>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={handleRequestEmailChange}>
              <p className="text-xs text-muted-foreground">
                Request a new login email. An administrator must approve it before Bloom sends a confirmation link to the new address.
              </p>
              <div>
                <label htmlFor="new-email" className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                  New email
                </label>
                <input
                  id="new-email"
                  type="email"
                  value={newEmail}
                  onChange={(event) => setNewEmail(event.target.value)}
                  required
                  className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground"
                />
              </div>
              <div>
                <label htmlFor="current-password" className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                  Current password
                </label>
                <input
                  id="current-password"
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  required
                  className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm text-foreground"
                />
              </div>
              <div className="flex justify-end">
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
                >
                  Request email change
                </button>
              </div>
            </form>
          )}

          {emailMessage && (
            <p className="text-sm text-muted-foreground" role="status">{emailMessage}</p>
          )}
        </div>
      </div>

      {/* Appearance */}
      <div className="bg-card rounded-lg border border-border shadow-elegant overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center gap-2 bg-muted/30">
          <Monitor className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">Appearance</h3>
        </div>
        <div className="p-5 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">Theme Mode</p>
              <p className="text-xs text-muted-foreground mt-0.5">Toggle between light and dark mode</p>
            </div>
            <button
              onClick={() => setDark(!dark)}
              className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors duration-200 ${
                dark ? 'bg-primary' : 'bg-muted'
              }`}
            >
              <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full bg-white shadow-sm transition-transform duration-200 ${
                dark ? 'translate-x-6' : 'translate-x-1'
              }`}>
                {dark ? <Moon className="h-3 w-3 text-primary" /> : <Sun className="h-3 w-3 text-amber-500" />}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Regional Settings */}
      <div className="bg-card rounded-lg border border-border shadow-elegant overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center gap-2 bg-muted/30">
          <Globe className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">Regional Settings</h3>
        </div>
        <div className="p-5 space-y-4">
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">Display Timezone</p>
            <div className="max-w-sm mt-3">
              <select
                value={timezone}
                onChange={(e) => handleTimezoneChange(e.target.value)}
                className="w-full bg-background border border-input rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                {COMMON_TIMEZONES.map((tz) => (
                  <option key={tz.value} value={tz.value}>
                    {tz.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <p className="text-[10px] text-muted-foreground italic">
            * Page will reload to apply changes.
          </p>
        </div>
      </div>

      {/* Scoped Bud integration credentials (Admin Only) */}
      {isAdmin && (
        <div className="bg-card rounded-lg border border-border shadow-elegant overflow-hidden border-primary/20">
          <div className="px-5 py-4 border-b border-border flex items-center gap-2 bg-primary/5">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Bud Result-Sync Credentials</h3>
          </div>
          <div className="p-5 space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground">Scoped service credential</p>
              <p className="text-xs text-muted-foreground">Creates a revocable 90-day credential that can only submit test-case results. It cannot access Bloom user, project, or admin APIs.</p>
            </div>

            {generatedToken ? (
              <div className="space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
                <div className="relative">
                  <textarea
                    readOnly
                    value={generatedToken}
                    className="w-full h-24 px-3 py-2 bg-muted/50 border border-border rounded-md text-[11px] font-mono text-foreground resize-none focus:outline-none"
                  />
                  <button
                    onClick={copyToClipboard}
                    className="absolute right-2 top-2 p-1.5 bg-background border border-border rounded-md hover:bg-accent transition-colors"
                    title="Copy to clipboard"
                  >
                    {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5 text-muted-foreground" />}
                  </button>
                </div>
                <div className="flex justify-between items-center">
                  <p className="text-[10px] text-amber-600 font-medium">⚠️ Copy this token now. It will not be shown again.</p>
                  <button
                    onClick={() => setGeneratedToken('')}
                    className="text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Clear
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex justify-start">
                <button
                  onClick={handleGenerateToken}
                  disabled={isGenerating}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                  Create Credential
                </button>
              </div>
            )}

            {credentials.length > 0 && (
              <div className="space-y-2 border-t border-border pt-4">
                {credentials.map((credential) => (
                  <div key={credential.id} className="flex items-center justify-between gap-3 rounded-md border border-border p-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground">{credential.name}</p>
                      <p className="text-[11px] font-mono text-muted-foreground">
                        {credential.token_prefix}… · {credential.scope} · expires {new Date(credential.expires_at).toLocaleDateString()}
                      </p>
                      {credential.revoked_at && <p className="text-[11px] text-destructive">Revoked</p>}
                    </div>
                    {!credential.revoked_at && (
                      <div className="flex gap-2">
                        <button
                          type="button"
                          disabled={isGenerating}
                          onClick={() => handleRotateToken(credential.id)}
                          className="text-xs font-medium text-primary hover:underline disabled:opacity-50"
                        >
                          Rotate
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRevokeToken(credential.id)}
                          className="text-xs font-medium text-destructive hover:underline"
                        >
                          Revoke
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* About */}
      <div className="bg-card rounded-lg border border-border shadow-elegant overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center gap-2 bg-muted/30">
          <Info className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">About</h3>
        </div>
        <div className="p-5">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-10 h-10 rounded-lg overflow-hidden flex items-center justify-center bg-muted">
              <img src="/favicon-96x96.png" alt="Bloom" className="w-full h-full object-contain" />
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">Bloom PLM</p>
              <p className="text-xs text-muted-foreground">v{APP_VERSION}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Powered by</span>
            <a
              href="https://www.embedlabs.net"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-primary hover:text-primary/80 transition-colors font-medium"
            >
              EmbedLabs
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <div className="mt-3 flex items-center gap-3 text-xs">
            <a
              href="https://github.com/MbedLabs/bloom"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:text-primary/80 transition-colors font-medium"
            >
              Source code
            </a>
            <a
              href="https://github.com/MbedLabs/bloom/blob/main/LICENSE"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:text-primary/80 transition-colors font-medium"
            >
              Source-available license
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
