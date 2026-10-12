import UserIdentity from '../components/UserIdentity'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { auditApi, type AuditFilters } from '../api/client'
import { formatDateTime } from '../test/date-utils'
import { SortableHeader } from '../components/ListControls'

const PAGE_SIZE = 50

const ACTION_GROUPS: { value: string; label: string }[] = [
  { value: '', label: 'All events' },
  { value: 'auth.', label: 'Authentication' },
  { value: 'user.', label: 'Accounts' },
  { value: 'project_member.', label: 'Project members' },
  { value: 'group.', label: 'Groups' },
  { value: 'policy.', label: 'Policies' },
  { value: 'artefact.', label: 'Artefacts' },
  { value: 'integration.', label: 'Integrations' },
  { value: 'service_credential.', label: 'Service credentials' },
  { value: 'export.', label: 'Exports' },
  { value: 'import.', label: 'Imports' },
  { value: 'attachment.', label: 'Attachments' },
]

/** The admin audit log: security-relevant events, newest first, filterable. */
export default function AuditPage() {
  const [action, setAction] = useState('')
  const [outcome, setOutcome] = useState('')
  const [since, setSince] = useState('')
  const [until, setUntil] = useState('')
  const [page, setPage] = useState(0)
  const [sortField, setSortField] = useState<NonNullable<AuditFilters['sort']>>('occurred_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const filters: AuditFilters = {
    action: action || undefined,
    outcome: outcome || undefined,
    since: since || undefined,
    until: until || undefined,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    sort: sortField,
    dir: sortDir,
  }
  const { data, isLoading } = useQuery({
    queryKey: ['audit', filters],
    queryFn: () => auditApi.list(filters),
  })
  const total = data?.total ?? 0
  const lastPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1)
  const resetPage = () => setPage(0)
  const toggleSort = (field: NonNullable<AuditFilters['sort']>) => {
    setSortDir(field === sortField ? (sortDir === 'asc' ? 'desc' : 'asc') : field === 'occurred_at' ? 'desc' : 'asc')
    setSortField(field)
    resetPage()
  }

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Audit log</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Who did what to accounts, access, configuration and data. Events cannot be changed or deleted here.
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-muted-foreground">
          Events
          <select
            aria-label="Events"
            value={action}
            onChange={(e) => { setAction(e.target.value); resetPage() }}
            className="block mt-1 px-2 py-1.5 border border-border rounded-lg bg-background text-foreground"
          >
            {ACTION_GROUPS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
          </select>
        </label>
        <label className="text-sm text-muted-foreground">
          Outcome
          <select
            aria-label="Outcome"
            value={outcome}
            onChange={(e) => { setOutcome(e.target.value); resetPage() }}
            className="block mt-1 px-2 py-1.5 border border-border rounded-lg bg-background text-foreground"
          >
            <option value="">Any</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
            <option value="ignored">Ignored</option>
          </select>
        </label>
        <label className="text-sm text-muted-foreground">
          From
          <input
            aria-label="From"
            type="date"
            value={since}
            onChange={(e) => { setSince(e.target.value); resetPage() }}
            className="block mt-1 px-2 py-1.5 border border-border rounded-lg bg-background text-foreground"
          />
        </label>
        <label className="text-sm text-muted-foreground">
          Until
          <input
            aria-label="Until"
            type="date"
            value={until}
            onChange={(e) => { setUntil(e.target.value); resetPage() }}
            className="block mt-1 px-2 py-1.5 border border-border rounded-lg bg-background text-foreground"
          />
        </label>
      </div>
      <div className="border border-border rounded-xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-muted-foreground">
            <tr>
              {([
                ['occurred_at', 'Time'], ['actor', 'Actor'], ['action', 'Event'], ['target', 'Target'],
                ['outcome', 'Outcome'], ['ip', 'Address'], ['request_id', 'Request'],
              ] as const).map(([field, label]) => (
                <SortableHeader key={field} field={field} sortField={sortField} sortDir={sortDir} onSort={toggleSort}
                  className="text-left font-medium px-4 py-2 cursor-pointer select-none hover:text-foreground transition-colors">
                  {label}
                </SortableHeader>
              ))}
            </tr>
          </thead>
          <tbody>
            {(data?.items ?? []).map((event) => (
              <tr key={event.id} className="border-t border-border align-top">
                <td className="px-4 py-2 text-muted-foreground whitespace-nowrap">
                  {formatDateTime(event.occurred_at)}
                </td>
                <td className="px-4 py-2 text-foreground">
                  {event.actor_user_id != null ? <UserIdentity user={{ id: event.actor_user_id, full_name: event.actor_name ?? `User ${event.actor_user_id}`, profile_picture_url: event.actor_profile_picture_url }} /> : event.actor_type}
                </td>
                <td className="px-4 py-2 text-foreground font-mono text-xs">{event.action}</td>
                <td className="px-4 py-2 text-muted-foreground">
                  {event.target_type ? `${event.target_type} ${event.target_id ?? ''}`.trim() : ''}
                </td>
                <td className={`px-4 py-2 ${event.outcome === 'failure' ? 'text-red-600' : 'text-muted-foreground'}`}>
                  {event.outcome}
                </td>
                <td className="px-4 py-2 text-muted-foreground">{event.ip ?? ''}</td>
                <td className="px-4 py-2 text-muted-foreground font-mono text-xs">{event.request_id ?? ''}</td>
              </tr>
            ))}
            {!isLoading && (data?.items.length ?? 0) === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-muted-foreground">No events match these filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>{total} events</span>
        <div className="flex gap-2">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1.5 border border-border rounded-lg disabled:opacity-50"
          >
            Prev
          </button>
          <button
            onClick={() => setPage((p) => Math.min(lastPage, p + 1))}
            disabled={page >= lastPage}
            className="px-3 py-1.5 border border-border rounded-lg disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
