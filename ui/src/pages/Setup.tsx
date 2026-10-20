import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { APP_VERSION, extractApiErrorMessage, setupApi } from '../api/client'
import { BLOOM_LOGO_DARK, BLOOM_LOGO_LIGHT, PRODUCT_IDENTITY, PRODUCT_NAME } from '../brandAssets'
import { newPasswordProblem } from '../lib/passwordRules'

/**
 * First-run administrator creation.
 *
 * Reachable only while the instance has no users. A packaged install has no way
 * to ask for an email address at install time, so the first visitor supplies
 * their own here instead of hunting for a generated password on disk.
 */
export default function Setup() {
  const navigate = useNavigate()

  const [setupRequired, setSetupRequired] = useState<boolean | null>(null)
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false

    setupApi
      .getStatus()
      .then((status) => {
        if (!cancelled) setSetupRequired(status.setup_required)
      })
      .catch(() => {
        if (!cancelled) setSetupRequired(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitError('')

    const passwordProblem = newPasswordProblem(password, confirmPassword)
    if (passwordProblem) {
      setSubmitError(passwordProblem)
      return
    }

    setSubmitting(true)
    try {
      await setupApi.createFirstAdmin(email, password, fullName)
      void navigate('/login', { replace: true })
    } catch (err: unknown) {
      setSubmitError(extractApiErrorMessage(err, 'Unable to create the administrator account'))
    } finally {
      setSubmitting(false)
    }
  }

  if (setupRequired === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-linear-to-br/srgb from-[#1a1028] via-[#3b1d6e] to-[#6b7280]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  if (!setupRequired) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br/srgb from-[#1a1028] via-[#3b1d6e] to-[#6b7280] p-4">
      <div className="w-full max-w-md bg-card rounded-2xl shadow-2xl p-8 border border-border">
        <div className="flex flex-col items-center mb-6">
          <img
            src={BLOOM_LOGO_DARK}
            alt={PRODUCT_IDENTITY}
            className="h-16 w-auto max-w-full object-contain mb-3 hidden dark:block"
          />
          <img
            src={BLOOM_LOGO_LIGHT}
            alt={PRODUCT_IDENTITY}
            className="h-16 w-auto max-w-full object-contain mb-3 dark:hidden"
          />
        </div>

        <h1 className="text-2xl font-bold text-foreground mb-2">{`Welcome to ${PRODUCT_NAME}`}</h1>
        <p className="text-sm text-muted-foreground mb-6">
          This instance has no accounts yet. Create the administrator to get started.
        </p>

        {submitError && (
          <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
            {submitError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="setup-full-name" className="block text-sm font-medium text-foreground mb-1.5">Full Name</label>
            <input
              id="setup-full-name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              className="w-full px-3 py-2.5 bg-background border border-input rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
              placeholder="Your name"
            />
          </div>

          <div>
            <label htmlFor="setup-email" className="block text-sm font-medium text-foreground mb-1.5">Email</label>
            <input
              id="setup-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2.5 bg-background border border-input rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="setup-password" className="block text-sm font-medium text-foreground mb-1.5">Password</label>
            <input
              id="setup-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={12}
              className="w-full px-3 py-2.5 bg-background border border-input rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
              placeholder="At least 12 characters"
            />
          </div>

          <div>
            <label htmlFor="setup-confirm-password" className="block text-sm font-medium text-foreground mb-1.5">Confirm Password</label>
            <input
              id="setup-confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={12}
              className="w-full px-3 py-2.5 bg-background border border-input rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
              placeholder="Repeat your password"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 px-4 bg-linear-to-r/srgb from-primary to-[#6b7280] text-white text-sm font-medium rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Creating administrator...' : 'Create Administrator'}
          </button>
        </form>

        <div className="text-center mt-6">
          <p className="text-sm text-muted-foreground">{PRODUCT_NAME}</p>
          <p className="text-xs text-muted-foreground/70 mt-1">v{APP_VERSION}</p>
          <a
            href="https://www.embedlabs.net"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-muted-foreground/70 mt-1 inline-block hover:text-foreground transition-colors"
          >
            Powered by EmbedLabs
          </a>
        </div>
      </div>
    </div>
  )
}
