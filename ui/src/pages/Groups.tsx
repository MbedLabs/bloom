import SelectField from '../components/SelectField'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, Edit2, Eye, Plus, Trash2, X } from 'lucide-react'
import {
  Group,
  GroupInput,
  groupsApi,
  Policy,
  PolicyVisibility,
  PolicyInput,
  PolicyRule,
  PolicyScope,
  policiesApi,
  Tag,
  tagsApi,
} from '../api/client'
import { useToast } from '../components/useToast'
import { useAuth } from '../contexts/AuthContext'
import { applicationAllows } from '../lib/applicationAccess'
import { SortableHeader } from '../components/ListControls'
import AccessRequestsPanel from '../components/AccessRequestsPanel'
import {
  activeRule, approveIncludesReview, BUILTIN_ORIGINS, emptyRule, isCompleteAppPolicy, isDocType, PERMISSIONS,
  policyOrigins, policyPermissions, policyResourceSummary, policyScopeLabel,
  resourceLabel, resourcesFor, SCOPE_LABELS, supportedPermission, type Permission,
} from '../lib/policySummary'

/** The tab a key moves to in a tab list: first, last, next or previous with wrap-around; null for any other key. */
function tabForKey<T>(key: string, views: readonly T[], index: number): T | null {
  if (key === 'Home') return views[0]
  if (key === 'End') return views[views.length - 1]
  if (key === 'ArrowRight') return views[(index + 1) % views.length]
  if (key === 'ArrowLeft') return views[(index + views.length - 1) % views.length]
  return null
}

/** The read flag of a rule after one of its permissions is toggled. */
function toggledRead(permission: Permission, current: PolicyRule): boolean {
  if (permission === 'write' && !current.write) return true
  return permission === 'read' ? !current.read : current.read
}

/** The review flag of a rule after one of its permissions is toggled. */
function toggledReview(permission: Permission, current: PolicyRule, resource: string): boolean {
  if (permission === 'approve' && !current.approve && approveIncludesReview(resource)) return true
  return permission === 'review' ? !current.review : current.review ?? false
}

/** Whether the permission checkbox of a rule shows as checked. */
function permissionChecked(permission: Permission, current: PolicyRule, resource: string): boolean {
  if (permission === 'read') return current.read || current.write
  if (permission === 'review') return current.review || current.approve && approveIncludesReview(resource)
  return current[permission]
}

/** Title of the policy dialog. */
function policyModalTitle(readOnly: boolean, editing: boolean): string {
  if (readOnly) return 'View policy'
  return editing ? 'Edit policy' : 'New policy'
}

export default function GroupsPage() {
  const { user } = useAuth()
  if (!applicationAllows(user, 'view')) {
    return <div className="p-6 text-muted-foreground">Access Management permission is required.</div>
  }
  return <AccessContent />
}

function AccessContent() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const toast = useToast()

  const { data: policies } = useQuery({ queryKey: ['policies'], queryFn: policiesApi.list })
  const { data: groups } = useQuery({ queryKey: ['groups'], queryFn: groupsApi.list })
  const { data: tags } = useQuery({ queryKey: ['tags'], queryFn: () => tagsApi.list() })

  const [view, setView] = useState<'groups' | 'policies' | 'requests'>('policies')
  const views = user?.role === 'admin' ? ['policies', 'groups', 'requests'] as const : ['policies', 'groups'] as const
  const [viewingPolicy, setViewingPolicy] = useState<Policy | null>(null)
  const [editingPolicy, setEditingPolicy] = useState<Policy | 'new' | null>(null)
  const [editingGroup, setEditingGroup] = useState<Group | 'new' | null>(null)
  const [groupSort, setGroupSort] = useState<'name' | 'policies'>('name')
  const [groupDir, setGroupDir] = useState<'asc' | 'desc'>('asc')
  const [policySort, setPolicySort] = useState<'name' | 'scope' | 'permissions' | 'origins'>('name')
  const [policyDir, setPolicyDir] = useState<'asc' | 'desc'>('asc')
  const groupPolicyNames = (group: Group) => (group.policy_ids ?? [])
    .map((id) => policies?.find((policy) => policy.id === id)?.name ?? `Policy ${id}`).join(', ') || 'None'
  const sortedGroups = [...(groups ?? [])].sort((a, b) => {
    const value = (group: Group) => groupSort === 'name' ? group.name : groupPolicyNames(group)
    return value(a).localeCompare(value(b)) * (groupDir === 'asc' ? 1 : -1) || a.id - b.id
  })
  const sortedPolicies = [...(policies ?? [])].sort((a, b) => {
    const scope = (policy: Policy) => {
      const label = policyScopeLabel(policy)
      const resources = policyResourceSummary(policy)
      return policy.scope !== 'document' && !isCompleteAppPolicy(policy) && resources !== label ? `${label} ${resources}` : label
    }
    const value = (policy: Policy) => {
      if (policySort === 'name') return policy.name
      if (policySort === 'scope') return scope(policy)
      if (policySort === 'permissions') return policyPermissions(policy).join(', ')
      return policyOrigins(policy, tags ?? []).join(', ')
    }
    return value(a).localeCompare(value(b)) * (policyDir === 'asc' ? 1 : -1) || a.id - b.id
  })
  const toggleGroupSort = (field: typeof groupSort) => {
    setGroupDir(field === groupSort && groupDir === 'asc' ? 'desc' : 'asc')
    setGroupSort(field)
  }
  const togglePolicySort = (field: typeof policySort) => {
    setPolicyDir(field === policySort && policyDir === 'asc' ? 'desc' : 'asc')
    setPolicySort(field)
  }

  const invalidatePolicies = () => queryClient.invalidateQueries({ queryKey: ['policies'] })
  const invalidateGroups = () => queryClient.invalidateQueries({ queryKey: ['groups'] })

  const deletePolicy = useMutation({
    mutationFn: (id: number) => policiesApi.delete(id),
    onSuccess: () => {
      void invalidatePolicies()
      toast.deleted('Policy')
    },
    onError: (error) => toast.failed('Deleting the policy', error),
  })

  const duplicatePolicy = useMutation({
    mutationFn: (id: number) => policiesApi.duplicate(id),
    onSuccess: (copy) => {
      void invalidatePolicies()
      setEditingPolicy(copy)
    },
    onError: (error) => toast.failed('Duplicating the policy', error),
  })

  const deleteGroup = useMutation({
    mutationFn: (id: number) => groupsApi.delete(id),
    onSuccess: () => {
      void invalidateGroups()
      toast.deleted('Group')
    },
    onError: (error) => toast.failed('Deleting the group', error),
  })


  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Access Management</h1>
        <p className="mt-1 text-sm text-muted-foreground">Configure groups of policies and permissions by scope and origin.</p>
      </div>
      <div role="tablist" aria-label="Access views" className="flex gap-1 border-b border-border">
        {views.map((tab) => (
          <button
            key={tab}
            id={`access-${tab}-tab`}
            type="button"
            role="tab"
            aria-selected={view === tab}
            aria-controls={`access-${tab}-panel`}
            tabIndex={view === tab ? 0 : -1}
            onClick={() => setView(tab)}
            onKeyDown={(event) => {
              const index = views.findIndex((item) => item === tab)
              const next = tabForKey(event.key, views, index)
              if (next) {
                event.preventDefault()
                setView(next)
                document.getElementById(`access-${next}-tab`)?.focus()
              }
            }}
            className={`border-b-2 px-4 py-2 text-sm font-medium ${view === tab ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>
      {view === 'requests' && user?.role === 'admin' && <section role="tabpanel" id="access-requests-panel" aria-labelledby="access-requests-tab">
        <AccessRequestsPanel showEmpty />
      </section>}
      {view === 'groups' && <section role="tabpanel" id="access-groups-panel" aria-labelledby="access-groups-tab">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-foreground">Groups</h2>
          </div>
          <button
            onClick={() => setEditingGroup('new')}
            disabled={!applicationAllows(user, 'create')}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" /> New group
          </button>
        </div>
        <div className="border border-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                {(['name', 'policies'] as const).map((field) => (
                  <SortableHeader key={field} field={field} sortField={groupSort} sortDir={groupDir} onSort={toggleGroupSort}
                    className="text-left font-medium px-4 py-2 cursor-pointer select-none hover:text-foreground transition-colors">
                    {field === 'name' ? 'Name' : 'Policies'}
                  </SortableHeader>
                ))}
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {sortedGroups.map((group) => (
                <tr key={group.id} className="border-t border-border">
                  <td className="px-4 py-2 text-foreground font-medium">{group.name}</td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {groupPolicyNames(group)}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setEditingGroup(group)}
                        disabled={!applicationAllows(user, 'edit')}
                        title="Edit group"
                        className="p-1 rounded text-muted-foreground hover:text-foreground"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => deleteGroup.mutate(group.id)}
                        disabled={!applicationAllows(user, 'delete')}
                        title="Delete group"
                        className="p-1 rounded text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {groups?.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-muted-foreground">
                    No groups yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>}

      {view === 'policies' && <section role="tabpanel" id="access-policies-panel" aria-labelledby="access-policies-tab">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-foreground">Policies</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Named permission sets. The shipped defaults are protected.
            </p>
          </div>
          <button
            onClick={() => setEditingPolicy('new')}
            disabled={!applicationAllows(user, 'create')}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" /> New policy
          </button>
        </div>
        <div className="border border-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                {(['name', 'scope', 'permissions', 'origins'] as const).map((field) => (
                  <SortableHeader key={field} field={field} sortField={policySort} sortDir={policyDir} onSort={togglePolicySort}
                    className="text-left font-medium px-4 py-2 cursor-pointer select-none hover:text-foreground transition-colors">
                    {field.charAt(0).toUpperCase() + field.slice(1)}
                  </SortableHeader>
                ))}
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {sortedPolicies.map((policy) => (
                <tr key={policy.id} className="border-t border-border">
                  <td className="px-4 py-2 text-foreground font-medium">
                    {policy.name}
                    {policy.is_default && (
                      <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase bg-muted text-muted-foreground">
                        Default
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-muted-foreground">
                    <div>{policyScopeLabel(policy)}</div>
                    {policy.scope !== 'document' && !isCompleteAppPolicy(policy) && policyResourceSummary(policy) !== policyScopeLabel(policy) && (
                      <div className="mt-1 max-w-64 text-xs">{policyResourceSummary(policy)}</div>
                    )}
                  </td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {policyPermissions(policy).map((summary) => <div key={summary}>{summary}</div>)}
                  </td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {policyOrigins(policy, tags ?? []).map((summary) => <div key={summary}>{summary}</div>)}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => setViewingPolicy(policy)} title={`View ${policy.name}`} className="p-1 rounded text-muted-foreground hover:text-foreground">
                        <Eye className="h-3.5 w-3.5" />
                      </button>
                      {policy.is_default ? (
                        <button
                          onClick={() => duplicatePolicy.mutate(policy.id)}
                          disabled={!applicationAllows(user, 'create')}
                          title={`Duplicate ${policy.name}`}
                          className="p-1 rounded text-muted-foreground hover:text-foreground"
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={() => setEditingPolicy(policy)}
                            disabled={!applicationAllows(user, 'edit')}
                            title={`Edit ${policy.name}`}
                            className="p-1 rounded text-muted-foreground hover:text-foreground"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => deletePolicy.mutate(policy.id)}
                            disabled={!applicationAllows(user, 'delete')}
                            title={`Delete ${policy.name}`}
                            className="p-1 rounded text-muted-foreground hover:text-destructive"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>}


      {viewingPolicy && <PolicyModal policy={viewingPolicy} tags={tags ?? []} readOnly onClose={() => setViewingPolicy(null)} onSaved={() => setViewingPolicy(null)} />}
      {editingPolicy && (
        <PolicyModal
          policy={editingPolicy === 'new' ? null : editingPolicy}
          tags={tags ?? []}
          onClose={() => setEditingPolicy(null)}
          onSaved={() => {
            void invalidatePolicies()
            setEditingPolicy(null)
          }}
        />
      )}
      {editingGroup && (
        <GroupModal
          group={editingGroup === 'new' ? null : editingGroup}
          policies={policies ?? []}
          onClose={() => setEditingGroup(null)}
          onSaved={() => {
            void invalidateGroups()
            setEditingGroup(null)
          }}
        />
      )}
    </div>
  )
}

function ModalShell({ title, onClose, children }: Readonly<{
  title: string
  onClose: () => void
  children: React.ReactNode
}>) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <button type="button" aria-label="Close dialog backdrop" tabIndex={-1} className="absolute inset-0 h-full w-full cursor-default" onClick={onClose} />
      <dialog open aria-modal="true" aria-label={title}
        className="relative m-0 text-foreground bg-card border border-border rounded-xl shadow-elegant p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto" onKeyDown={(event) => { if (event.key === 'Escape') { event.stopPropagation(); onClose() } }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">{title}</h2>
          <button onClick={onClose} title="Close" className="p-1 rounded text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </dialog>
    </div>
  )
}

const inputClass =
  'w-full px-3 py-2 bg-background border border-input rounded-lg text-sm text-foreground'
const submitClass =
  'w-full py-2 bg-linear-to-r/srgb from-primary to-[#6b7280] text-white text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-50'

function PolicyModal({ policy, tags, readOnly = false, onClose, onSaved }: Readonly<{
  policy: Policy | null
  tags: Tag[]
  readOnly?: boolean
  onClose: () => void
  onSaved: () => void
}>) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const [name, setName] = useState(policy?.name ?? '')
  const [description, setDescription] = useState(policy?.description ?? '')
  const [scope, setScope] = useState<PolicyScope>(policy?.scope ?? 'document')
  const [rules, setRules] = useState<Record<string, PolicyRule>>(policy?.rules ?? {})
  const [newOrigin, setNewOrigin] = useState('')
  const resources = resourcesFor(scope)
  const rule = (resource: string) => rules[resource] ?? emptyRule()
  const change = (resource: string, update: (current: PolicyRule) => PolicyRule) =>
    setRules((prev) => ({ ...prev, [resource]: update(prev[resource] ?? emptyRule()) }))
  const togglePermission = (resource: string, permission: Permission) =>
    change(resource, (current) => ({
      ...current,
      [permission]: !current[permission],
      read: toggledRead(permission, current),
      review: toggledReview(permission, current, resource),
    }))
  const toggleAllOrigins = (resource: string) =>
    change(resource, (current) => ({
      ...current,
      all_origins: !current.all_origins,
      visibility: [],
      tags: [],
    }))
  const toggleBuiltinOrigin = (resource: string, key: PolicyVisibility) =>
    change(resource, (current) => ({
      ...current,
      all_origins: false,
      visibility: current.visibility.includes(key)
        ? current.visibility.filter((item) => item !== key)
        : [...current.visibility, key],
    }))
  const toggleCustomOrigin = (resource: string, id: number) =>
    change(resource, (current) => ({
      ...current,
      all_origins: false,
      tags: current.tags.includes(id) ? current.tags.filter((item) => item !== id) : [...current.tags, id],
    }))
  const unscoped = resources.filter((resource) => {
    const current = rule(resource)
    return isDocType(resource) && activeRule(current) && !current.all_origins
      && current.visibility.length === 0 && current.tags.length === 0
  })
  const save = useMutation({
    mutationFn: () => {
      const payload: PolicyInput = {
        name,
        description,
        scope,
        rules: Object.fromEntries(
          resources.filter((resource) => activeRule(rule(resource))).map((resource) => {
            const current = rule(resource)
            const allOrigins = isDocType(resource) && current.all_origins
            return [resource, {
              read: current.read || current.write,
              write: current.write,
              review: current.review ?? false,
              approve: current.approve,
              delete: current.delete,
              all_origins: allOrigins,
              visibility: isDocType(resource) && !allOrigins ? current.visibility : [],
              tags: isDocType(resource) && !allOrigins ? current.tags : [],
            }]
          }),
        ),
      }
      return policy ? policiesApi.update(policy.id, payload) : policiesApi.create(payload)
    },
    onSuccess: () => { toast.saved('Policy'); onSaved() },
    onError: (error) => toast.failed('Saving the policy', error),
  })
  const addOrigin = useMutation({
    mutationFn: () => tagsApi.create(newOrigin.trim()),
    onSuccess: () => {
      setNewOrigin('')
      void queryClient.invalidateQueries({ queryKey: ['tags'] })
      toast.saved('Origin')
    },
    onError: (error) => toast.failed('Adding the origin', error),
  })
  return (
    <ModalShell title={policyModalTitle(readOnly, !!policy)} onClose={onClose}>
      <form onSubmit={(event) => { event.preventDefault(); if (!readOnly) save.mutate() }} className="space-y-4">
        <label className="block text-sm font-medium text-foreground">Name
          <input value={name} onChange={(event) => setName(event.target.value)} readOnly={readOnly} required title="Policy name" className={inputClass} />
        </label>
        <label className="block text-sm font-medium text-foreground">Description
          <input value={description} onChange={(event) => setDescription(event.target.value)} readOnly={readOnly} title="Description" className={inputClass} />
        </label>
        <label className="block text-sm font-medium text-foreground">Assignment scope
          <SelectField disabled={readOnly} value={scope} title="Assignment scope" className={inputClass} onChange={(event) => {
            const nextScope = event.target.value as PolicyScope
            setScope(nextScope)
            setRules((current) => Object.fromEntries(Object.entries(current).filter(([resource]) => resourcesFor(nextScope).includes(resource))))
          }}>
            {Object.entries(SCOPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </SelectField>
        </label>
        <p className="text-xs text-muted-foreground">Write includes Read. Review, Approve and Delete are separate permissions.</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-muted-foreground">
                <th className="text-left font-medium pr-3">Resource</th>
                {PERMISSIONS.map((permission) => (
                  <th key={permission} className="font-medium px-2">
                    {permission.charAt(0).toUpperCase() + permission.slice(1)}
                  </th>
                ))}
                <th className="text-left font-medium px-2">Origins</th>
              </tr>
            </thead>
            <tbody>
              {resources.map((resource) => {
                const current = rule(resource)
                const active = activeRule(current)
                return (
                  <tr key={resource} className="border-t border-border">
                    <th className="text-left font-normal py-2 pr-3 whitespace-nowrap" title={current.actions?.length ? `Grants: ${current.actions.join(', ')}` : undefined}>
                      {resourceLabel(resource)}
                    </th>
                    {PERMISSIONS.map((permission) => (
                      <td key={permission} className="text-center px-2">
                        <input
                          type="checkbox"
                          aria-label={`${permission.charAt(0).toUpperCase() + permission.slice(1)} ${resource}`}
                          checked={permissionChecked(permission, current, resource)}
                          disabled={readOnly || !supportedPermission(resource, permission) || permission === 'read' && current.write || permission === 'review' && current.approve && approveIncludesReview(resource)}
                          onChange={() => togglePermission(resource, permission)}
                        />
                      </td>
                    ))}
                    <td className="px-2 py-2">
                      {isDocType(resource) && (
                        <fieldset aria-label={`Origins for ${resource}`} className="flex flex-wrap gap-x-3 gap-y-1 min-w-56">
                          <label className="inline-flex items-center gap-1.5">
                            <input type="checkbox" aria-label={`All origins on ${resource}`} disabled={readOnly || !active} checked={current.all_origins} onChange={() => toggleAllOrigins(resource)} />
                            All
                          </label>
                          {BUILTIN_ORIGINS.map((origin) => (
                            <label key={origin.key} className="inline-flex items-center gap-1.5">
                              <input type="checkbox" aria-label={`${origin.label} on ${resource}`} disabled={readOnly || !active} checked={current.visibility.includes(origin.key)} onChange={() => toggleBuiltinOrigin(resource, origin.key)} />
                              {origin.label}
                            </label>
                          ))}
                          {tags.map((origin) => (
                            <label key={origin.id} className="inline-flex items-center gap-1.5">
                              <input type="checkbox" aria-label={`${origin.name} on ${resource}`} disabled={readOnly || !active} checked={current.tags.includes(origin.id)} onChange={() => toggleCustomOrigin(resource, origin.id)} />
                              {origin.name}
                            </label>
                          ))}
                        </fieldset>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {!readOnly && <div className="flex gap-2">
          <input value={newOrigin} onChange={(event) => setNewOrigin(event.target.value)} placeholder="New origin" title="New origin" className={inputClass + ' max-w-xs'} />
          <button type="button" disabled={!newOrigin.trim() || addOrigin.isPending} onClick={() => addOrigin.mutate()} className="inline-flex items-center gap-1.5 px-3 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary/90 disabled:opacity-50">
            <Plus className="h-4 w-4" /> Add origin
          </button>
        </div>}
        {unscoped.length > 0 && <p className="text-xs text-destructive">Choose at least one origin for {unscoped.join(', ')}.</p>}
        {!readOnly && <button type="submit" disabled={save.isPending || unscoped.length > 0} className={submitClass}>{save.isPending ? 'Saving…' : 'Save policy'}</button>}
      </form>
    </ModalShell>
  )
}

function GroupModal({ group, policies, onClose, onSaved }: Readonly<{
  group: Group | null
  policies: Policy[]
  onClose: () => void
  onSaved: () => void
}>) {
  const toast = useToast()
  const [name, setName] = useState(group?.name ?? '')
  const [description, setDescription] = useState(group?.description ?? '')
  const [policyIds, setPolicyIds] = useState<number[]>(group?.policy_ids ?? [])

  const save = useMutation({
    mutationFn: () => {
      const payload: GroupInput = { name, description, policy_ids: policyIds }
      return group ? groupsApi.update(group.id, payload) : groupsApi.create(payload)
    },
    onSuccess: () => {
      toast.saved('Group')
      onSaved()
    },
    onError: (error) => toast.failed('Saving the group', error),
  })

  return (
    <ModalShell title={group ? 'Edit group' : 'New group'} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
        className="space-y-3"
      >
        <label className="block">
          <span className="block text-sm font-medium text-foreground mb-1">Name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required title="Group name" className={inputClass} />
        </label>
        <label className="block">
          <span className="block text-sm font-medium text-foreground mb-1">Description</span>
          <input value={description} onChange={(e) => setDescription(e.target.value)} title="Description" className={inputClass} />
        </label>
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-foreground mb-2">Policies owned by this group</legend>
          {policies.map((policy) => (
            <label key={policy.id} className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                aria-label={`Group policy ${policy.name}`}
                checked={policyIds.includes(policy.id)}
                onChange={() => setPolicyIds((current) => current.includes(policy.id)
                  ? current.filter((id) => id !== policy.id)
                  : [...current, policy.id].sort((a, b) => a - b))}
              />
              {policy.name}
              <span className="text-muted-foreground">{SCOPE_LABELS[policy.scope]}</span>
            </label>
          ))}
          {policies.length === 0 && <p className="text-sm text-muted-foreground">No policies available.</p>}
        </fieldset>
        <button type="submit" disabled={save.isPending} className={submitClass}>
          {save.isPending ? 'Saving…' : 'Save group'}
        </button>
      </form>
    </ModalShell>
  )
}
