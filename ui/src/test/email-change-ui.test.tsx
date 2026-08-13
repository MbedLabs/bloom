// @vitest-environment jsdom

import { ToastProvider } from '../components/Toast'
import '@testing-library/jest-dom/vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import Settings from '../pages/Settings'
import UsersPage from '../pages/Users'

const requestEmailChange = vi.hoisted(() => vi.fn())
const approveEmailChange = vi.hoisted(() => vi.fn())
const refreshUser = vi.hoisted(() => vi.fn())

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: 'admin@bloom.example',
      full_name: 'Bloom Admin',
      role: 'admin',
      is_active: true,
      created_at: '',
      updated_at: '',
    },
    refreshUser,
  }),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  const pendingUser = {
    id: 2,
    email: 'old@bloom.example',
    full_name: 'Bloom User',
    role: 'external' as const,
    is_active: true,
    pending_email: 'new@bloom.example',
    email_change_status: 'requested' as const,
    email_change_requested_at: '2026-07-29T12:00:00Z',
    created_at: '2026-07-01T12:00:00Z',
    updated_at: '2026-07-29T12:00:00Z',
  }
  return {
    ...actual,
    authApi: {
      ...actual.authApi,
      requestEmailChange,
      cancelEmailChange: vi.fn(),
    },
    serviceCredentialsApi: {
      ...actual.serviceCredentialsApi,
      list: vi.fn().mockResolvedValue([]),
    },
    usersApi: {
      ...actual.usersApi,
      list: vi.fn().mockResolvedValue([pendingUser]),
      approveEmailChange,
      rejectEmailChange: vi.fn(),
    },
  }
})

function renderWithQueryClient(element: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{element}</ToastProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  const storage = {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
    key: vi.fn(() => null),
    length: 0,
  }
  vi.stubGlobal('localStorage', storage)
  Object.defineProperty(window, 'localStorage', {
    value: storage,
    writable: true,
    configurable: true,
  })
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: vi.fn((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: (): void => undefined,
      removeListener: (): void => undefined,
      addEventListener: (): void => undefined,
      removeEventListener: (): void => undefined,
      dispatchEvent: (): boolean => false,
    })),
  })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('administrator-controlled email changes', () => {
  it('lets an account holder submit a request from Settings', async () => {
    requestEmailChange.mockResolvedValue({
      message: 'Email change requested. An administrator must approve it.',
    })
    refreshUser.mockResolvedValue(undefined)
    renderWithQueryClient(<Settings />)

    fireEvent.change(screen.getByLabelText('New email'), {
      target: { value: 'new@bloom.example' },
    })
    fireEvent.change(screen.getByLabelText('Current password'), {
      target: { value: 'current-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Request email change' }))

    await waitFor(() => {
      expect(requestEmailChange).toHaveBeenCalledWith(
        'current-password',
        'new@bloom.example',
      )
    })
    expect(refreshUser).toHaveBeenCalled()
  })

  it('shows a pending user request to administrators and approves it', async () => {
    approveEmailChange.mockResolvedValue({})
    renderWithQueryClient(<UsersPage />)

    expect(await screen.findByText('Requested: new@bloom.example')).toBeInTheDocument()
    fireEvent.click(screen.getByTitle('Approve email change'))

    await waitFor(() => {
      expect(approveEmailChange).toHaveBeenCalledWith(2, expect.anything())
    })
  })
})
