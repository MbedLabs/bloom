import { useQuery } from '@tanstack/react-query'
import { projectsApi, type ProjectCapabilities } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

/** The current user's server-reported project metadata and administration rights. */
export function useProjectCapabilities(projectId?: number) {
  const { user } = useAuth()
  const { data, isError, isPending } = useQuery({
    queryKey: ['project-capabilities', projectId, user?.id],
    queryFn: () => projectsApi.capabilities(projectId as number),
    enabled: !!projectId && !!user,
    staleTime: 60_000,
    retry: false,
  })
  const isAdmin = user?.role === 'admin'
  const fallback: ProjectCapabilities = {
    can_edit: isAdmin,
    can_delete: isAdmin,
    can_manage_access: isAdmin,
  }
  return {
    ...(isError ? fallback : data ?? fallback),
    isLoading: !!projectId && !!user && isPending && !isAdmin,
  }
}
