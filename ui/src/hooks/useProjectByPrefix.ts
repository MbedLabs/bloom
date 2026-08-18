import { useQuery } from '@tanstack/react-query'
import { projectsApi, type Project } from '../api/client'

export function useProjectByPrefix(prefix: string | undefined) {
  return useQuery<Project>({
    queryKey: ['project-by-prefix', prefix],
    queryFn: () => projectsApi.getByPrefix(prefix!),
    enabled: !!prefix,
  })
}
