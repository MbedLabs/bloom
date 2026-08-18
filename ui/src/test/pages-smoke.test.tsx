import { renderPage } from './render'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

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

describe('source-available readiness smoke', () => {
  // These tests run in the node environment, so `window` only exists because it
  // is stubbed here. Without cleanup the stub leaked into later cases and raced
  // the cached App import, which made the suite fail intermittently.
  beforeEach(() => {
    vi.stubGlobal('window', { runtimeConfig: {} })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetModules()
  })

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
    ['/login', 'Welcome to Bloom', 'text-gray-300/60'],
    ['/accept-invite', 'Accept Invitation', 'text-gray-300/50'],
    ['/verify-email', 'Verify Email', 'text-gray-300/50'],
    ['/forgot-password', 'Forgot Password', 'text-gray-300/50'],
    ['/reset-password', 'Reset Password', 'text-gray-300/50'],
  ])('renders %s without crashing', async (path, marker, attributionColor) => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { default: App } = await import('../App')
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })

    const html = renderPage(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[path]}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>
    )

    expect(html).toContain(marker)
    expect(html).toContain('Powered by EmbedLabs')
    expect(html).not.toContain('>by EmbedLabs</a>')
    expect(html).not.toContain('fixed bottom-3 left-3')
    expect(html).toContain(attributionColor)
    expect(html).not.toContain(
      'text-gray-500 transition-colors hover:text-gray-700 dark:text-white',
    )
    consoleErrorSpy.mockRestore()
  })
})
