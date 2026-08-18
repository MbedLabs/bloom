// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider, useAuth } from '../contexts/AuthContext'

const refreshMock = vi.hoisted(() => vi.fn())

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    authApi: {
      ...actual.authApi,
      refresh: refreshMock,
    },
  }
})

function AuthState() {
  const { user, isLoading } = useAuth()
  if (isLoading) return <span>Loading</span>
  return <span>{user?.email ?? 'Signed out'}</span>
}

describe('Bloom cross-tab session restoration', () => {
  beforeEach(() => {
    sessionStorage.clear()
    refreshMock.mockReset()
  })

  afterEach(() => {
    cleanup()
  })

  it('restores an existing login from the HttpOnly refresh cookie when a new tab has no access token', async () => {
    refreshMock.mockResolvedValueOnce({
      access_token: 'new-tab-access-token',
      token_type: 'bearer',
      user: {
        id: 1,
        email: 'already-logged-in@example.com',
        full_name: 'Existing User',
        role: 'admin',
        is_active: true,
        created_at: '',
        updated_at: '',
      },
    })

    render(
      <AuthProvider>
        <AuthState />
      </AuthProvider>,
    )

    expect(await screen.findByText('already-logged-in@example.com')).toBeInTheDocument()
    expect(refreshMock).toHaveBeenCalledOnce()
    expect(sessionStorage.getItem('bloom_token')).toBe('new-tab-access-token')
  })

  it('stays signed out when no refresh session exists', async () => {
    refreshMock.mockRejectedValueOnce(new Error('Invalid or expired session'))

    render(
      <AuthProvider>
        <AuthState />
      </AuthProvider>,
    )

    expect(await screen.findByText('Signed out')).toBeInTheDocument()
  })
})
