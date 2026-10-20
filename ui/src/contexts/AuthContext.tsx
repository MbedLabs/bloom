import React, { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { authApi, User } from '../api/client'
import {
  clearAuthToken,
  getAuthToken,
  getSessionUserId,
  setAuthToken,
  setSessionUserId,
} from '../lib/tokenStorage'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const pictureRevision = useRef<string | null | undefined>(undefined)

  const applyUser = useCallback(
    (next: User | null) => {
      const previous = getSessionUserId()
      if (previous !== null && previous !== (next?.id ?? null)) {
        clearAuthToken()
        queryClient.clear()
        setSessionUserId(null)
        setUser(null)
        window.location.replace('/login')
        return
      }
      if (previous === null && next !== null) {
        queryClient.clear()
      }
      if (previous === next?.id && pictureRevision.current !== next?.profile_picture_url) {
        void queryClient.invalidateQueries({ predicate: query =>
          ['users', 'mentionableUsers', 'access-assignment-options', 'project-members', 'project-access', 'access-requests', 'audit', 'artefactComments', 'artefactActivity', 'notifications-list'].includes(String(query.queryKey[0]))
        })
      }
      pictureRevision.current = next?.profile_picture_url
      setSessionUserId(next?.id ?? null)
      setUser(next)
    },
    [queryClient],
  )

  const loadUser = useCallback(async () => {
    try {
      if (getAuthToken()) {
        applyUser(await authApi.getMe())
      } else {
        const session = await authApi.refresh()
        setAuthToken(session.access_token)
        applyUser(session.user)
      }
    } catch {
      clearAuthToken()
      applyUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [applyUser])

  const loadStarted = useRef(false)

  useEffect(() => {
    if (loadStarted.current) return
    loadStarted.current = true
    void loadUser()
  }, [loadUser])

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login(email, password)
    setSessionUserId(null)
    setAuthToken(response.access_token)
    applyUser(response.user)
  }, [applyUser])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      clearAuthToken()
      applyUser(null)
    }
  }, [applyUser])

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      logout,
      refreshUser: loadUser,
    }),
    [user, isLoading, login, logout, loadUser],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
