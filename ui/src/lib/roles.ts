export const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  maintainer: 'Maintainer',
  external: 'Viewer',
}

export function roleLabel(role: string | null | undefined): string {
  if (!role) return ''
  return ROLE_LABELS[role] ?? role
}
