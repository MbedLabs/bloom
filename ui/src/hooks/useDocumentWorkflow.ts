import { useQuery } from '@tanstack/react-query'
import { workflowApi } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export function useDocumentWorkflow(type: string, id: number | undefined) {
  const { user } = useAuth()
  const query = useQuery({
    queryKey: ['document-workflow', type, id, user?.id],
    queryFn: () => workflowApi.get(type, id!),
    enabled: !!id,
    retry: false,
    staleTime: 30_000,
  })
  return { ...query, data: query.isError ? undefined : query.data }
}
