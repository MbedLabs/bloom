import { useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { projectMembersApi, type ProjectPermissions } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import type { DocType } from '../types/doc'
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
  | 'manage'

export type PermissionResource =
  | 'requirement'
  | 'design'
  | 'test_concept'
  | 'test_case'
  | 'risk'
  | 'change_request'
  | 'defect'
  | 'document'
  | 'suite'
  | 'campaign'
  | 'run'
  | 'baseline'
  | 'parameter'
  | 'link'
  | 'member'

/** The permission resource each document type is checked against. */
export const DOC_TYPE_RESOURCES: Record<DocType, PermissionResource> = {
  REQ: 'requirement',
  SPEC: 'document',
  TC: 'test_case',
  DES: 'design',
  RSK: 'risk',
  CHG: 'change_request',
  CPT: 'test_concept',
  DEF: 'defect',
  CMP: 'campaign',
  TS: 'suite',
  PRT: 'document',
  RPT: 'document',
  STD: 'document',
}

/** What the role alone allows, used until the server's effective set arrives. */
function roleBaseline(role: string | undefined): ProjectPermissions {
  if (role === 'admin' || role === 'maintainer') return { '*': ['*'] }
  if (role === 'external') return { '*': ['view', 'comment'] }
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
 * The current user's effective permissions on a project: the role baseline plus
 * the policies of the user's groups, as the server resolves them. Pass the project
 * id when it is known, otherwise the prefix.
 */
export function useProjectPermissions(prefix?: string, projectId?: number) {
  const { user } = useAuth()
  const { data: project } = useProjectByPrefix(projectId ? undefined : prefix)
  const id = projectId || project?.id
  const { data } = useQuery({
    queryKey: ['project-permissions', id, user?.id],
    queryFn: () => projectMembersApi.permissions(id as number),
    enabled: !!id && !!user,
    staleTime: 60_000,
    retry: false,
  })
  const granted = data ?? roleBaseline(user?.role)
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
