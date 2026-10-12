import { useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { docsApi, projectMembersApi, type ProjectPermissions } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { DOC_TYPE_SLUGS, type DocType } from '../types/doc'
import { useProjectByPrefix } from './useProjectByPrefix'

export type PermissionAction =
  | 'view'
  | 'comment'
  | 'create'
  | 'edit'
  | 'delete'
  | 'review'
  | 'approve'
  | 'execute'
  | 'plan'
  | 'import'
  | 'export'

export type PermissionResource = DocType | 'baseline' | 'parameter' | 'link'

/** The instance administrator's existing unrestricted permissions. */
function roleBaseline(role: string | undefined): ProjectPermissions {
  if (role === 'admin') return { '*': ['*'] }
  return {}
}

/** True when the set allows the action on the resource, directly or by wildcard. */
export function allows(
  permissions: ProjectPermissions,
  action: PermissionAction,
  resource: PermissionResource,
): boolean {
  const granted = [...(permissions[resource] ?? []), ...(permissions['*'] ?? [])]
  return granted.includes(action) || granted.includes('*')
}

/**
 * The current user's effective permissions on a project, as the server resolves
 * its direct and group grants. Pass the project
 * id when it is known, otherwise the prefix.
 */
export function useProjectPermissions(prefix?: string, projectId?: number) {
  const { user } = useAuth()
  const { data: project } = useProjectByPrefix(projectId ? undefined : prefix)
  const id = projectId || project?.id
  const { data, isError } = useQuery({
    queryKey: ['project-permissions', id, user?.id],
    queryFn: () => projectMembersApi.permissions(id as number),
    enabled: !!id && !!user,
    staleTime: 60_000,
    retry: false,
  })
  const granted = (isError ? undefined : data) ?? roleBaseline(user?.role)
  const can = useCallback(
    (action: PermissionAction, resource: PermissionResource) => allows(granted, action, resource),
    [granted],
  )
  const canAny = useCallback(
    (action: PermissionAction) =>
      Object.values(granted).some((actions) => actions.includes(action) || actions.includes('*')),
    [granted],
  )
  return { can, canAny }
}

/** A change the server answers for one artefact. */
export type RowAction = 'edit' | 'delete' | 'plan' | 'review' | 'approve'

/**
 * Whether the signed-in user may take a change on one artefact, from the server's answer for
 * that row: the answer the page was given, else the artefact's detail read. While the answer
 * is pending, missing or failed, no mutation action is available.
 */
export function useRowActions(
  prefix: string | undefined,
  docType: DocType,
  docId: string | null | undefined,
  given?: string[],
) {
  const slug = DOC_TYPE_SLUGS[docType]
  const { data, isError } = useQuery({
    queryKey: ['doc-facade', prefix, slug, docId],
    queryFn: () => docsApi.get(prefix as string, slug, docId as string),
    enabled: given === undefined && !!prefix && !!docId,
    retry: false,
  })
  const actions = given ?? (isError ? undefined : data?.allowed_actions)
  return useCallback(
    (action: RowAction) => actions?.includes(action) ?? false,
    [actions],
  )
}
