import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { workflowApi } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { docUrl } from '../types/doc'

export default function DocumentRequestsPanel({ projectId, projectPrefix }: Readonly<{ projectId: number; projectPrefix: string }>) {
  const { user } = useAuth()
  const { data: requests, isPending, isError } = useQuery({
    queryKey: ['document-requests', projectId, user?.id],
    queryFn: () => workflowApi.listProjectRequests(projectId),
    enabled: !!projectId,
    retry: false,
  })

  return (
    <section className="rounded-lg border border-border bg-card p-4 shadow-elegant">
      <h3 className="text-sm font-semibold text-foreground">Document requests</h3>
      <p className="mt-1 text-xs text-muted-foreground">Pending reviews and approvals for this project.</p>
      {isPending ? <p className="mt-3 text-sm text-muted-foreground">Loading document requests...</p>
        : isError ? <p className="mt-3 text-sm text-destructive" role="alert">Could not load document requests.</p>
          : !requests?.length ? <p className="mt-3 text-sm text-muted-foreground">No pending document requests.</p>
            : <ul className="mt-3 divide-y divide-border">
              {requests.map((request) => (
                <li key={request.id} className="flex flex-wrap items-center gap-3 py-2 text-sm">
                  <Link to={docUrl(projectPrefix, request.doc_type, request.public_id)} className="font-medium text-primary hover:underline">{request.public_id}</Link>
                  <span className="rounded bg-primary/10 px-2 py-0.5 text-xs text-primary">{request.kind === 'review' ? 'Review' : 'Approval'}</span>
                  <span className="text-xs text-muted-foreground">Revision {request.revision_number}</span>
                </li>
              ))}
            </ul>}
    </section>
  )
}
