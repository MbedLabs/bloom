import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { useNavigate } from 'react-router'
import { useAuth } from '../contexts/AuthContext'
import { APP_VERSION, extractApiErrorMessage, setupApi } from '../api/client'
import { BLOOM_LOGO_DARK, BLOOM_LOGO_LIGHT } from '../brandAssets'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  // An instance with no accounts cannot be signed in to; send the first
  // visitor to create the administrator instead of showing them a form that
  // can only fail. Failures are ignored: a backend that cannot answer should
  // still render the login form.
  useEffect(() => {
    let cancelled = false
    setupApi
      .getStatus()
      .then((status) => {
        if (!cancelled && status.setup_required) navigate('/setup', { replace: true })
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (err: unknown) {
      const message = extractApiErrorMessage(err, 'Login failed')
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#1a1028] via-[#3b1d6e] to-[#6b7280]">
      <div className="w-full max-w-md px-4">
        <div className="bg-card rounded-2xl shadow-2xl p-8 border border-border">
          <div className="flex flex-col items-center mb-8">
            <img
              src={BLOOM_LOGO_DARK}
              alt="Bloom by EmbedLabs"
              className="h-24 w-auto max-w-full object-contain mb-4 hidden dark:block"
            />
            <img
              src={BLOOM_LOGO_LIGHT}
              alt="Bloom by EmbedLabs"
              className="h-24 w-auto max-w-full object-contain mb-4 dark:hidden"
            />
            <h1 className="text-2xl font-bold text-foreground">Welcome to Bloom</h1>
            <p className="text-sm text-muted-foreground mt-1">Sign in to your account</p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                className="w-full px-3 py-2.5 bg-background border border-input rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
                placeholder="you@company.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-3 py-2.5 bg-background border border-input rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors"
                placeholder="Enter your password"
              />
            </div>

            <div className="text-right">
              <Link to="/forgot-password" className="text-sm font-medium text-primary hover:text-primary/80 transition-colors">
                Forgot password?
              </Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-primary to-[#6b7280] text-white text-sm font-medium rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </div>

        <div className="text-center mt-6">
          <p className="text-sm text-violet-100/70">Bloom PLM</p>
          <p className="text-xs text-violet-200/50 mt-1">v{APP_VERSION}</p>
          <a
            href="https://www.embedlabs.net"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-300/60 mt-1 inline-block hover:text-gray-200 transition-colors"
          >
            Powered by EmbedLabs
          </a>
        </div>
      </div>
    </div>
  )
}
