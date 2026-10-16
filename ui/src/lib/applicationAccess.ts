import type { User } from '../api/client'

export function applicationAllows(user: Pick<User, 'role' | 'application_permissions'> | null | undefined, action: string, resource = 'access'): boolean {
  if (user?.role === 'admin') return true
  const permissions = user?.application_permissions ?? {}
  const actions = [...(permissions[resource] ?? []), ...(permissions['*'] ?? [])]
  return actions.includes(action) || actions.includes('*')
}
