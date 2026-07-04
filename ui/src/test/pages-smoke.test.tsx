import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderToString } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import type { User } from '../api/client'
import { docRegistryListUrl } from '../lib/docRegistryParams'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}))

vi.mock('../components/Layout', () => ({
  default: () => null,
}))

vi.mock('../components/ProtectedRoute', () => ({
  default: ({ children }: { children: unknown }) => children,
}))

describe('OSS readiness smoke', () => {
  it('User role contract includes external (not reviewer)', () => {
    const u: User = {
      id: 1,
      email: 'u@example.com',
      full_name: 'User',
      role: 'external',
      is_active: true,
      created_at: '',
      updated_at: '',
    }
    expect(u.role).toBe('external')
  })

  it('doc registry list URL encodes requirement type', () => {
    const url = docRegistryListUrl('VCU', 'REQ')
    expect(url).toContain('/projects/VCU/docs')
    expect(url).toContain('type=requirements')
  })

  it.each([
    ['/login', 'Welcome to Bloom'],
    ['/accept-invite', 'Accept Invitation'],
    ['/verify-email', 'Verify Email'],
    ['/forgot-password', 'Forgot Password'],
    ['/reset-password', 'Reset Password'],
  ])('renders %s without crashing', async (path, marker) => {
    vi.stubGlobal('window', { runtimeConfig: {} })
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { default: App } = await import('../App')
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })

    const html = renderToString(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[path]}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>
    )

    expect(html).toContain(marker)
    consoleErrorSpy.mockRestore()
    vi.unstubAllGlobals()
  })
})
