// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import Settings from '../pages/Settings'

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
    refreshUser: vi.fn(),
  }),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    serviceCredentialsApi: {
      ...actual.serviceCredentialsApi,
      list: vi.fn().mockResolvedValue([]),
    },
  }
})

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

describe('Settings', () => {
  it('keeps the historical PLM integration section name', () => {
    render(<Settings />)

    expect(
      screen.getByRole('heading', { name: 'PLM Integration Token Management' }),
    ).toBeInTheDocument()
    expect(screen.queryByText('Bud Result-Sync Credentials')).not.toBeInTheDocument()
  })
})
