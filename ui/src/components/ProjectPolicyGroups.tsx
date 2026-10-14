import SelectField from './SelectField'
import UserIdentity from './UserIdentity'
import ProfilePicture from './ProfilePicture'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import {
  extractApiErrorMessage, groupsApi, policiesApi, projectMembersApi,
  type Group, type Policy, type ProjectMember,
} from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { applicationAllows } from '../lib/applicationAccess'
import { useToast } from './useToast'

const DEFAULT_GROUPS = ['Administrators', 'Developers', 'Product Owners', 'Testers']
type Person = { id: number; email: string; full_name: string; role?: string; profile_picture_url?: string | null }

function ProjectMemberIdentity({ member, canRemove, disabled, onRemove }: { member: ProjectMember; canRemove: boolean; disabled: boolean; onRemove: () => void }) {
  const label = `Remove ${member.full_name} from project`
  return <span className="inline-flex min-w-0 items-center gap-2 align-middle">
    <span className="group/image relative inline-flex shrink-0">
      <ProfilePicture user={{ ...member, id: member.user_id }} className="w-6 h-6" />
      {canRemove && <button type="button" aria-label={label} title={label} disabled={disabled} onClick={onRemove}
        className="absolute -right-1 -top-1 z-10 flex h-4 w-4 items-center justify-center rounded-full border border-border bg-card text-red-500 opacity-0 transition-opacity group-hover/image:opacity-100 group-focus-within/image:opacity-100 [@media(hover:none)]:opacity-100 hover:bg-red-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 disabled:cursor-wait disabled:opacity-50">
        <X className="h-3 w-3" aria-hidden="true" />
      </button>}
    </span>
    <span className="truncate">{member.full_name}</span>
  </span>
}

function groupRequiresRole(group: Group, policies: Policy[]): 'admin' | 'maintainer' | 'external' {
  if (group.name === 'Administrators') return 'maintainer'
  if (['Developers', 'Product Owners', 'Testers'].includes(group.name)) return 'maintainer'
  const groupPolicies = policies.filter((p) => group.policy_ids.includes(p.id))
  if (groupPolicies.some((p) => p.scope === 'app')) return 'admin'
  const hasWrite = groupPolicies.some((p) =>
    Object.values(p.rules ?? {}).some((rule) => rule.write || rule.approve || rule.delete)
  )
  if (hasWrite) return 'maintainer'
  return 'external'
}

function isEligibleForGroup(person: Person, group: Group, policies: Policy[]): boolean {
  const requirement = groupRequiresRole(group, policies)
  const role = person.role ?? 'external'
  if (requirement === 'admin') {
    return role === 'admin'
  }
  if (requirement === 'maintainer') {
    return role === 'admin' || role === 'maintainer'
  }
  return true
}

export default function ProjectPolicyGroups({ projectId }: { projectId: number }) {
  const { user } = useAuth()
  const groups = useQuery({ queryKey: ['groups'], queryFn: groupsApi.list })
  const policies = useQuery({ queryKey: ['policies'], queryFn: policiesApi.list })
  const options = useQuery({ queryKey: ['access-assignment-options'], queryFn: groupsApi.assignmentOptions })
  const members = useQuery({ queryKey: ['project-members', projectId], queryFn: () => projectMembersApi.list(projectId) })
  const [additionalIds, setAdditionalIds] = useState<number[]>([])
  const [additionalId, setAdditionalId] = useState('')
  const queries = [groups, policies, options, members]
  const canAssign = applicationAllows(user, 'edit')
  const canRemove = applicationAllows(user, 'delete')

  if (queries.some((query) => query.isPending)) return <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">Loading project access...</div>
  if (queries.some((query) => query.isError)) return <div role="alert" className="rounded-lg border border-border bg-card p-6 text-sm text-destructive">Could not load project access. <button type="button" onClick={() => queries.forEach((query) => query.refetch())} className="underline">Retry</button></div>

  const catalogue = groups.data ?? []
  const entries = members.data ?? []
  const defaults = DEFAULT_GROUPS.map((name) => ({ name, group: catalogue.find((group) => group.name === name) }))
  const optional = catalogue.filter((group) => !DEFAULT_GROUPS.includes(group.name))
  const visibleOptional = optional.filter((group) => additionalIds.includes(group.id) || entries.some((member) => member.policy_group_id === group.id))
  const remaining = optional.filter((group) => !visibleOptional.includes(group))
  const legacy = entries.filter((member) => !member.policy_group_id || !catalogue.some((group) => group.id === member.policy_group_id))

  return <section className="rounded-lg border border-border bg-card p-6 shadow-elegant">
    <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">Project members</h3>
    <p className="mt-1 mb-5 text-sm text-muted-foreground">Choose the people who receive each group of policies in this project. These groups are available in every project; people are assigned separately in each one.</p>
    <div className="grid gap-4 sm:grid-cols-2">
      {[...defaults, ...visibleOptional.map((group) => ({ name: group.name, group }))].map(({ name, group }) => group
        ? <ProjectGroupRoster key={`${projectId}-${group.id}`} projectId={projectId} group={group} members={entries} people={options.data?.users ?? []} policies={policies.data ?? []} canAssign={canAssign} canRemove={canRemove} />
        : <section key={name} aria-label={name} className="rounded-lg border border-border p-4"><h4 className="font-semibold">{name}</h4><p className="mt-2 text-sm text-destructive">This default group is missing. Configure it on Access before assigning people.</p></section>)}
    </div>
    {canAssign && remaining.length > 0 && <div className="mt-4 flex flex-wrap items-end gap-2">
      <label className="text-sm text-muted-foreground">Additional policy group
        <SelectField aria-label="Additional policy group" value={additionalId} onChange={(event) => setAdditionalId(event.target.value)} className="mt-1 block rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground">
          <option value="">Choose a group</option>
          {remaining.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
        </SelectField>
      </label>
      <button type="button" disabled={!additionalId} onClick={() => { setAdditionalIds((current) => [...current, Number(additionalId)]); setAdditionalId('') }} className="rounded-md border border-border px-3 py-2 text-sm disabled:opacity-50">Add group</button>
    </div>}
    {legacy.length > 0 && <div className="mt-6 rounded-lg border border-border p-4">
      <h4 className="text-sm font-semibold">Existing individual assignments</h4>
      <p className="mt-1 text-sm text-muted-foreground">These assignments remain active. Choose a person in a group above to replace their assignment for this project.</p>
      {legacy.map((member) => <LegacyMember key={member.id} projectId={projectId} member={member} canRemove={canRemove} />)}
    </div>}
  </section>
}

function ProjectGroupRoster({ projectId, group, members, people, policies, canAssign, canRemove }: {
  projectId: number; group: Group; members: ProjectMember[]; people: Person[]; policies: Policy[]; canAssign: boolean; canRemove: boolean
}) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [choosing, setChoosing] = useState(false)
  const [selected, setSelected] = useState<number[]>([])
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const assigned = members.filter((member) => member.policy_group_id === group.id)
  const assignedIds = assigned.map((member) => member.user_id)
  const candidates = new Map(people.map((person) => [person.id, person]))
  for (const member of assigned) {
    if (!candidates.has(member.user_id)) candidates.set(member.user_id, { ...member, id: member.user_id })
  }
  const eligible = [...candidates.values()]
    .filter((person) => assignedIds.includes(person.id) || isEligibleForGroup(person, group, policies))
    .sort((a, b) => a.full_name.localeCompare(b.full_name))
  const filtered = eligible.filter((person) => `${person.full_name} ${person.email}`.toLowerCase().includes(search.toLowerCase()))
  const addedIds = selected.filter((id) => !assignedIds.includes(id))
  const removed = assigned.filter((member) => !selected.includes(member.user_id))
  const changed = addedIds.length > 0 || removed.length > 0
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['project-members', projectId] })
    queryClient.invalidateQueries({ queryKey: ['project-access', projectId] })
    queryClient.invalidateQueries({ queryKey: ['project-permissions', projectId] })
    queryClient.invalidateQueries({ queryKey: ['project-capabilities', projectId] })
    queryClient.invalidateQueries({ queryKey: ['projects'] })
  }
  const assign = useMutation({
    mutationFn: async () => {
      if (addedIds.length > 0) await groupsApi.assign(group.id, projectId, addedIds)
      for (const member of removed) await projectMembersApi.remove(projectId, member.id)
    },
    onSuccess: () => { refresh(); setSelected([]); setChoosing(false); setSearch(''); setError(''); toast.saved(`${group.name} assignments`) },
    onError: (failure) => { refresh(); setError(extractApiErrorMessage(failure, 'Could not save selection')); toast.failed('Saving project assignments', failure) },
  })
  const remove = useMutation({
    mutationFn: (id: number) => projectMembersApi.remove(projectId, id),
    onSuccess: () => { refresh(); setError(''); toast.notify('Project assignment removed', 'success') },
    onError: (failure) => { setError(extractApiErrorMessage(failure, 'Could not remove project assignment')); toast.failed('Removing project assignment', failure) },
  })
  const busy = assign.isPending || remove.isPending
  return <section aria-label={group.name} className="min-w-0 rounded-lg border border-border bg-background/40 p-4">
    <div className="flex items-center justify-between gap-2"><h4 className="font-semibold text-foreground">{group.name}</h4>
      {canAssign && <button type="button" disabled={busy || group.policy_ids.length === 0} onClick={() => { setSelected(choosing ? [] : assignedIds); setSearch(''); setChoosing((value) => !value); setError('') }} className="rounded-md border border-border px-2.5 py-1.5 text-xs hover:bg-accent disabled:opacity-50">{choosing ? 'Cancel selection' : 'Select members'}</button>}
    </div>
    {!choosing && (assigned.length === 0 ? <p className="mt-3 text-sm text-muted-foreground">No people assigned.</p> : <ul className="mt-3 space-y-2">
      {assigned.map((member) => <li key={member.id} className="flex items-center gap-2"><div className="min-w-0"><p className="text-sm text-foreground"><ProjectMemberIdentity member={member} canRemove={canRemove} disabled={busy} onRemove={() => remove.mutate(member.id)} /></p><p className="truncate text-xs text-muted-foreground">{member.email}</p></div></li>)}
    </ul>)}
    {error && <p role="alert" className="mt-3 text-sm text-destructive">{error}</p>}
    {choosing && <fieldset disabled={busy} className="mt-4 min-w-0 space-y-3">
      <legend className="text-sm font-medium">Select members</legend>
      <input aria-label={`Search people for ${group.name}`} placeholder="Search people..." value={search} onChange={(event) => setSearch(event.target.value)} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
      <p className="text-xs text-muted-foreground">Assigning a person replaces their current policy group in this project. Their assignments in other projects stay separate.</p>
      <div className="max-h-56 space-y-2 overflow-y-auto">
        {filtered.map((person) => {
          const current = members.find((member) => member.user_id === person.id)
          return <label key={person.id} className="flex items-start gap-2 text-sm"><input type="checkbox" aria-label={`Select ${person.full_name}`} disabled={busy || (assignedIds.includes(person.id) && !canRemove)} checked={selected.includes(person.id)} onChange={() => setSelected((values) => values.includes(person.id) ? values.filter((id) => id !== person.id) : [...values, person.id].sort((a, b) => a - b))} className="mt-1" /><span className="min-w-0"><span className="block truncate"><UserIdentity user={person} /></span><span className="block truncate text-xs text-muted-foreground">{person.email}</span>{current && current.policy_group_id !== group.id && <span className="text-xs text-muted-foreground">Currently: {current.policy_group_name ?? (current.owner ? 'Owner' : current.inherit_policies ? 'Inherited policies' : 'Individual policies')}</span>}</span></label>
        })}
        {filtered.length === 0 && <p className="text-sm text-muted-foreground">{search ? 'No matching people.' : 'No people available.'}</p>}
      </div>
      <button type="button" disabled={busy || !changed} onClick={() => assign.mutate()} className="rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground disabled:opacity-50">{assign.isPending ? 'Saving...' : 'Save selection'}</button>
    </fieldset>}
  </section>
}

function LegacyMember({ projectId, member, canRemove }: { projectId: number; member: ProjectMember; canRemove: boolean }) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const remove = useMutation({
    mutationFn: () => projectMembersApi.remove(projectId, member.id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['project-members', projectId] }); queryClient.invalidateQueries({ queryKey: ['project-access', projectId] }); queryClient.invalidateQueries({ queryKey: ['project-permissions', projectId] }); queryClient.invalidateQueries({ queryKey: ['project-capabilities', projectId] }); queryClient.invalidateQueries({ queryKey: ['projects'] }); toast.notify('Project assignment removed', 'success') },
    onError: (failure) => toast.failed('Removing project assignment', failure),
  })
  return <div className="mt-3 flex items-center gap-2 text-sm"><div className="min-w-0"><p><ProjectMemberIdentity member={member} canRemove={canRemove} disabled={remove.isPending} onRemove={() => remove.mutate()} /></p><p className="truncate text-xs text-muted-foreground">{member.email}</p><p className="text-xs text-muted-foreground">{member.owner ? 'Owner' : member.inherit_policies ? 'Inherited group policies' : 'Individually selected policies'}</p></div></div>
}
