import { getSessionUserId } from '../lib/tokenStorage'
import { useToast } from './useToast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router'
import { api, extractApiErrorMessage } from '../api/client'
import { docUrl } from '../types/doc'

export type ReportSource = {
  source_kind: 'test-case' | 'test-suite' | 'requirement' | 'campaign'
  source_id: number
  run_id: number
}

type RequestState = {
  id: number
  status: 'pending' | 'delivered' | 'refused'
  reason: string | null
  project_prefix: string
  doc_id: string | null
}

/** Label of the report request button. */
function requestLabel(pending: boolean, refused: boolean): string {
  if (pending) return 'Requesting…'
  return refused ? 'Request again' : 'Request report'
}

export default function ReportRequestAction({ source }: Readonly<{ source: ReportSource }>) {
  const client = useQueryClient()
  const toast = useToast()
  const requesterId = getSessionUserId()
  const key = ['report-request', requesterId, source]
  const state = useQuery({
    queryKey: key,
    queryFn: async () => (await api.get<RequestState | null>('/report-requests', { params: source })).data,
    refetchInterval: (query) => query.state.data?.status === 'pending' ? 15000 : false,
  })
  const request = useMutation({
    mutationFn: async () => (await api.post<RequestState>('/report-requests', source)).data,
    onSuccess: (value) => {
      if (getSessionUserId() !== requesterId) return
      client.setQueryData(key, value)
      toast.saved('Report request')
    },
    onError: (error) => toast.failed('Requesting the report', error),
  })
  const value = state.data
  return (
    <span className="inline-flex flex-wrap items-center gap-2 text-xs">
      {value?.status === 'pending' && <span className="text-muted-foreground">Report requested · Pending</span>}
      {value?.status === 'delivered' && (value.doc_id ? (
        <Link className="text-primary hover:text-primary/80" to={docUrl(value.project_prefix, 'RPT', value.doc_id)}>View report</Link>
      ) : <span className="text-muted-foreground">Report delivered</span>)}
      {value?.status === 'refused' && <span className="text-muted-foreground">Report refused: {value.reason}</span>}
      {!state.isPending && !state.isError && value?.status !== 'pending' && value?.status !== 'delivered' && (
        <button type="button" className="px-2 py-1 rounded border border-border text-foreground hover:bg-accent disabled:opacity-50"
          disabled={request.isPending} onClick={() => request.mutate()}>
          {requestLabel(request.isPending, value?.status === 'refused')}
        </button>
      )}
      {(state.isError || request.isError) && <span role="alert" className="text-destructive">
        {extractApiErrorMessage(request.error || state.error, 'Could not load the report request')}
      </span>}
    </span>
  )
}
