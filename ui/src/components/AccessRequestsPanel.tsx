import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { accessRequestsApi } from '../api/client'
import { useToast } from './useToast'
import UserIdentity from './UserIdentity'

/** Pending access requests, optionally filtered to one project. */
export default function AccessRequestsPanel({ projectPrefix, showEmpty = false }: Readonly<{ projectPrefix?: string; showEmpty?: boolean }>) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const queryKey = ['access-requests', projectPrefix]
  const { data: requests, isLoading, isError } = useQuery({
    queryKey,
    queryFn: () => accessRequestsApi.list({ status: 'pending', ...(projectPrefix ? { project_prefix: projectPrefix } : {}) }),
  })
  const decide = useMutation({
    mutationFn: ({ id, decision }: { id: number; decision: 'granted' | 'refused' }) =>
      accessRequestsApi.decide(id, decision),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['access-requests'] })
      toast.saved('Access request')
    },
    onError: (error) => toast.failed('Answering the access request', error),
  })

  if (!showEmpty && (!requests || requests.length === 0)) return null

  return (
    <section className="bg-card border border-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-foreground mb-3">Access requests</h3>
      {isLoading && <output className="block text-sm text-muted-foreground">Loading requests…</output>}
      {isError && <p role="alert" className="text-sm text-destructive">Could not load access requests.</p>}
      {!isLoading && !isError && requests?.length === 0 && <p className="text-sm text-muted-foreground">No pending requests.</p>}
      <ul className="divide-y divide-border">
        {requests?.map((request) => (
          <li key={request.id} className="py-2 flex items-center justify-between gap-3 text-sm">
            <span className="text-foreground">
              <UserIdentity user={{ full_name: request.requester_name ?? request.requester_email ?? 'Unknown user', profile_picture_url: request.requester_profile_picture_url }} /> ({request.requester_email}) asks for {request.resource_label ?? request.resource_ref}{request.project_prefix && request.resource_type !== 'project' ? ` in project ${request.project_prefix}` : ''}
            </span>
            <span className="flex gap-2">
              <button
                type="button"
                disabled={decide.isPending}
                onClick={() => decide.mutate({ id: request.id, decision: 'granted' })}
                className="px-2 py-1 rounded text-xs bg-primary text-white hover:bg-primary/90"
              >
                Mark granted
              </button>
              <button
                type="button"
                disabled={decide.isPending}
                onClick={() => decide.mutate({ id: request.id, decision: 'refused' })}
                className="px-2 py-1 rounded text-xs border border-border text-foreground hover:bg-muted"
              >
                Refuse
              </button>
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
