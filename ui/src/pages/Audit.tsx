import DateField from '../components/DateField'
import SelectField from '../components/SelectField'
import UserIdentity from '../components/UserIdentity'
import UserSelect from '../components/UserSelect'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { auditApi, serviceCredentialsApi, usersApi, type AuditEvent, type AuditFilters } from '../api/client'
import { formatDateTime } from '../test/date-utils'
import { SortableHeader } from '../components/ListControls'
import { useDebounced } from '../hooks/useDebounced'

const PAGE_SIZE = 50
const REFUSED_GROUP = 'refused'
const REQUEST_ACTION = 'api.request'
const FILTER_CLASS = 'block mt-1 px-2 py-1.5 border border-border rounded-lg bg-background text-foreground'

const ACTION_GROUPS: { value: string; label: string }[] = [
  { value: '', label: 'All events' },
  { value: 'api.', label: 'API calls' },
  { value: REFUSED_GROUP, label: 'Refused attempts' },
  { value: 'auth.', label: 'Authentication' },
  { value: 'user.', label: 'Accounts' },
  { value: 'access.', label: 'Access requests' },
  { value: 'project.', label: 'Projects' },
  { value: 'project_member.', label: 'Project members' },
  { value: 'group.', label: 'Groups' },
  { value: 'policy.', label: 'Policies' },
  { value: 'artefact.', label: 'Artefacts' },
  { value: 'tag.', label: 'Tags' },
  { value: 'baseline.', label: 'Baselines' },
  { value: 'workflow.', label: 'Workflow' },
  { value: 'report.', label: 'Reports' },
  { value: 'integration.', label: 'Integrations' },
  { value: 'service_credential.', label: 'Service credentials' },
  { value: 'export.', label: 'Exports' },
  { value: 'import.', label: 'Imports' },
  { value: 'attachment.', label: 'Attachments' },
  { value: 'company_logo.', label: 'Company logo' },
  { value: 'setup.', label: 'Setup' },
]

const ACTOR_KINDS: { value: string; label: string }[] = [
  { value: 'type:user', label: 'Any user' },
  { value: 'type:service', label: 'Service credential' },
  { value: 'type:anonymous', label: 'Anonymous' },
]

/** The actor filters one choice of the Actor control stands for: an actor type, or one user. */
function actorFilters(actor: string): Pick<AuditFilters, 'actor_type' | 'actor_user_id'> {
  if (!actor) return { actor_type: undefined, actor_user_id: undefined }
  if (actor.startsWith('type:')) return { actor_type: actor.slice('type:'.length), actor_user_id: undefined }
  return { actor_type: undefined, actor_user_id: Number(actor) }
}

/** One detail of an event as text, or undefined when the event does not hold it. */
function detail(event: AuditEvent, key: string): string | undefined {
  const value = event.details?.[key]
  return value == null || value === '' ? undefined : String(value)
}

/** The Actor cell: a user (marked MCP or CLI for a CLI sign-in token, with the User-Agent on hover), a service credential by name or id, or the actor type. */
function AuditActor({ event, credentialNames }: Readonly<{ event: AuditEvent; credentialNames: Map<number, string> }>) {
  if (event.actor_user_id != null) {
    const identity = <UserIdentity user={{ id: event.actor_user_id, full_name: event.actor_name ?? `User ${event.actor_user_id}`, profile_picture_url: event.actor_profile_picture_url }} />
    if (detail(event, 'client') !== 'cli') return identity
    return (
      <span className="inline-flex flex-wrap items-center gap-2">
        {identity}
        <span title={event.user_agent ?? undefined} className="rounded border border-border px-1.5 py-0.5 text-xs text-muted-foreground whitespace-nowrap">MCP or CLI</span>
      </span>
    )
  }
  const credentialId = event.actor_type === 'service' ? detail(event, 'service_credential_id') : undefined
  if (credentialId) {
    const label = `Service credential #${credentialId}`
    const name = credentialNames.get(Number(credentialId))
    return <span title={name ? label : undefined}>{name ?? label}</span>
  }
  return <>{event.actor_type}</>
}

/** The Event cell: the method and route of an API request, with its path on hover, else the event name. */
function AuditEventName({ event }: Readonly<{ event: AuditEvent }>) {
  const request = event.action === REQUEST_ACTION
    ? [detail(event, 'method'), detail(event, 'route')].filter(Boolean).join(' ')
    : ''
  if (!request) return <>{event.action}</>
  return <span title={detail(event, 'path')}>{request}</span>
}

/** The Target cell: the target, and for an API request its status first and the document ID or id of what it created. */
function AuditTarget({ event }: Readonly<{ event: AuditEvent }>) {
  const target = event.target_type ? `${event.target_type} ${event.target_id ?? ''}`.trim() : ''
  if (event.action !== REQUEST_ACTION) return <>{target}</>
  const status = detail(event, 'status')
  const created = detail(event, 'created_doc_id') ?? detail(event, 'created_id')
  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-2">
      {status && <span className="font-mono text-xs text-foreground">{status}</span>}
      {target && <span>{target}</span>}
      {created && <span>created {created}</span>}
    </span>
  )
}

/** The sort direction after a column is chosen: the sorted column flips, another column starts descending for the event time and ascending otherwise. */
function nextSortDir(field: string, sortField: string, sortDir: 'asc' | 'desc'): 'asc' | 'desc' {
  if (field === sortField) return sortDir === 'asc' ? 'desc' : 'asc'
  return field === 'occurred_at' ? 'desc' : 'asc'
}

/** The admin audit log: every API request, every refused attempt and every security-relevant event, newest first, filterable. */
export default function AuditPage() {
  const [action, setAction] = useState('')
  const [outcome, setOutcome] = useState('')
  const [actor, setActor] = useState('')
  const [ip, setIp] = useState('')
  const [requestId, setRequestId] = useState('')
  const [since, setSince] = useState('')
  const [until, setUntil] = useState('')
  const [page, setPage] = useState(0)
  const [sortField, setSortField] = useState<NonNullable<AuditFilters['sort']>>('occurred_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const settledIp = useDebounced(ip.trim(), 250)
  const settledRequestId = useDebounced(requestId.trim(), 250)

  const refusedGroup = action === REFUSED_GROUP
  const shownOutcome = refusedGroup ? 'denied' : outcome
  const filters: AuditFilters = {
    action: refusedGroup ? undefined : action || undefined,
    outcome: shownOutcome || undefined,
    ...actorFilters(actor),
    ip: settledIp || undefined,
    request_id: settledRequestId || undefined,
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
  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })
  const { data: credentials } = useQuery({
    queryKey: ['service-credentials'],
    queryFn: serviceCredentialsApi.list,
  })
  const credentialNames = new Map((credentials ?? []).map((credential) => [credential.id, credential.name]))
  const total = data?.total ?? 0
  const lastPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1)
  const resetPage = () => setPage(0)
  const toggleSort = (field: NonNullable<AuditFilters['sort']>) => {
    setSortDir(nextSortDir(field, sortField, sortDir))
    setSortField(field)
    resetPage()
  }

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Audit log</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Every API request and every refused attempt is recorded, with who did what to accounts, access, configuration and data. Events cannot be changed or deleted here.
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-muted-foreground">
          Events
          <SelectField
            aria-label="Events"
            value={action}
            onChange={(e) => { setAction(e.target.value); resetPage() }}
            className={FILTER_CLASS}
          >
            {ACTION_GROUPS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
          </SelectField>
        </label>
        <label className="text-sm text-muted-foreground">
          Outcome
          <SelectField
            aria-label="Outcome"
            value={shownOutcome}
            disabled={refusedGroup}
            onChange={(e) => { setOutcome(e.target.value); resetPage() }}
            className={FILTER_CLASS}
          >
            <option value="">Any</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
            <option value="denied">Denied</option>
            <option value="ignored">Ignored</option>
          </SelectField>
        </label>
        <div className="text-sm text-muted-foreground">
          Actor
          <div className="mt-1 w-44 text-foreground">
            <UserSelect
              value={actor}
              onChange={(next) => { setActor(next); resetPage() }}
              users={users ?? []}
              label="Actor"
              emptyLabel="Anyone"
              options={ACTOR_KINDS}
            />
          </div>
        </div>
        <label className="text-sm text-muted-foreground">
          Address
          <input
            type="text"
            value={ip}
            onChange={(e) => { setIp(e.target.value); resetPage() }}
            placeholder="Client address"
            spellCheck={false}
            className={`${FILTER_CLASS} w-36 placeholder:text-muted-foreground`}
          />
        </label>
        <label className="text-sm text-muted-foreground">
          Request
          <input
            type="text"
            value={requestId}
            onChange={(e) => { setRequestId(e.target.value); resetPage() }}
            placeholder="Request id"
            spellCheck={false}
            className={`${FILTER_CLASS} w-44 font-mono placeholder:font-sans placeholder:text-muted-foreground`}
          />
        </label>
        <label className="text-sm text-muted-foreground">
          From
          <DateField
            label="From"
            value={since}
            onChange={(next) => { setSince(next); resetPage() }}
            className={FILTER_CLASS}
          />
        </label>
        <label className="text-sm text-muted-foreground">
          Until
          <DateField
            label="Until"
            value={until}
            onChange={(next) => { setUntil(next); resetPage() }}
            className={FILTER_CLASS}
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
                  <AuditActor event={event} credentialNames={credentialNames} />
                </td>
                <td className="px-4 py-2 text-foreground font-mono text-xs"><AuditEventName event={event} /></td>
                <td className="px-4 py-2 text-muted-foreground">
                  <AuditTarget event={event} />
                </td>
                <td className={`px-4 py-2 ${event.outcome === 'failure' || event.outcome === 'denied' ? 'text-red-600' : 'text-muted-foreground'}`}>
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
