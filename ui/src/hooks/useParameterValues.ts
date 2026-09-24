import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { projectVariablesApi } from '../api/client'
import { useProjectByPrefix } from './useProjectByPrefix'

/**
 * The project's parameter and variable values by key, for showing a `{{KEY}}`
 * reference as its value. Undefined until loaded, or when the reader may not list
 * them, in which case references keep showing their names.
 */
export function useParameterValues(prefix?: string, projectId?: number): Record<string, string> | undefined {
  const { data: project } = useProjectByPrefix(projectId ? undefined : prefix)
  const id = projectId || project?.id
  const { data } = useQuery({
    queryKey: ['projectVariables', id],
    queryFn: () => projectVariablesApi.list(id as number),
    enabled: !!id,
    retry: false,
    staleTime: 60_000,
  })
  return useMemo(
    () => (Array.isArray(data) ? Object.fromEntries(data.map((variable) => [variable.key, variable.value])) : undefined),
    [data],
  )
}
