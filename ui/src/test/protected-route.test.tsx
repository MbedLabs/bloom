// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ProtectedRoute from '../components/ProtectedRoute'

let authState: { isAuthenticated: boolean; isLoading: boolean } = {
  isAuthenticated: false,
  isLoading: false,
}

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => authState,
}))

const renderGuard = () =>
  render(
    <MemoryRouter>
      <ProtectedRoute>
        <div>secret content</div>
      </ProtectedRoute>
    </MemoryRouter>,
  )

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ProtectedRoute', () => {
  it('shows a loading state while auth resolves', () => {
    authState = { isAuthenticated: false, isLoading: true }
    renderGuard()
    expect(screen.getByText('Loading...')).toBeInTheDocument()
    expect(screen.queryByText('secret content')).not.toBeInTheDocument()
  })

  it('redirects away when the visitor is not authenticated', () => {
    authState = { isAuthenticated: false, isLoading: false }
    renderGuard()
    expect(screen.queryByText('secret content')).not.toBeInTheDocument()
  })

  it('renders the protected children when authenticated', () => {
    authState = { isAuthenticated: true, isLoading: false }
    renderGuard()
    expect(screen.getByText('secret content')).toBeInTheDocument()
  })
})
